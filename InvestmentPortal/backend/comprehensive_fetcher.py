"""
comprehensive_fetcher.py
========================
기관급 US 기업 재무 데이터 통합 수집기

데이터 소스 우선순위:
1. FMP API  — 밸류에이션(P/E, EV/EBITDA, DCF), 프로파일, 연간/분기 풀 재무제표
2. SEC EDGAR — FMP 실패 시 손익 백업 (무료, 신뢰성 높음)
3. yahooquery — 최후 폴백
"""

import os
import requests
import datetime
from yahooquery import Ticker

FMP_API_KEY = os.environ.get("FMP_API_KEY", "qVib4aX1LQ1SimFf07f7m1PPHQzhESIh")
FMP_BASE = "https://financialmodelingprep.com/api/v3"
HEADERS = {"User-Agent": "InvestmentPortal research@example.com"}


# ─────────────────────────────────────────────
# 유틸 함수
# ─────────────────────────────────────────────

def safe(d: dict, key, default=None):
    """딕셔너리에서 None/NaN 안전 추출"""
    if d is None:
        return default
    v = d.get(key)
    if v is None or v != v:  # NaN check
        return default
    return v


def pct(numerator, denominator) -> float | None:
    """비율 계산 (퍼센트)"""
    try:
        if denominator and denominator != 0:
            return round(numerator / denominator * 100, 2)
    except Exception:
        pass
    return None


def yoy_growth(current, previous) -> float | None:
    """YoY 성장률 계산 (퍼센트)"""
    try:
        if previous and previous != 0:
            return round((current - previous) / abs(previous) * 100, 2)
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────
# 1. FMP — 회사 프로파일 + 밸류에이션
# ─────────────────────────────────────────────

def fetch_profile_from_yahoo(ticker: str) -> dict | None:
    """
    Yahoo Finance (yahooquery)에서 밸류에이션·프로파일 데이터를 수집합니다.
    FMP 무료 플랜 한도 우회용 대체 수집기.
    """
    try:
        t = Ticker(ticker)
        fd = t.financial_data.get(ticker, {})
        ks = t.key_stats.get(ticker, {})
        sd = t.summary_detail.get(ticker, {})
        asset_profile = t.asset_profile.get(ticker, {})
        price_data = t.price.get(ticker, {})

        if not fd or isinstance(fd, str):
            return None

        market_cap = price_data.get("marketCap") or ks.get("marketCap")
        enterprise_value = ks.get("enterpriseValue")
        ebitda = fd.get("ebitda")
        ev_ebitda = round(enterprise_value / ebitda, 2) if (enterprise_value and ebitda and ebitda != 0) else None

        total_revenue = fd.get("totalRevenue")
        ev_sales = round(enterprise_value / total_revenue, 2) if (enterprise_value and total_revenue and total_revenue != 0) else None

        book_value_per_share = ks.get("bookValue")
        price = fd.get("currentPrice") or sd.get("previousClose")
        pb_ratio = round(price / book_value_per_share, 2) if (price and book_value_per_share and book_value_per_share != 0) else None

        return {
            "sector": asset_profile.get("sector"),
            "industry_classification": asset_profile.get("industry"),
            "description": asset_profile.get("longBusinessSummary"),
            "ceo": next((o.get("name") for o in asset_profile.get("companyOfficers", []) if "CEO" in o.get("title", "")), None),
            "employees": asset_profile.get("fullTimeEmployees"),
            "website": asset_profile.get("website"),
            # 시장 데이터
            "market_cap": market_cap,
            "current_price": price,
            "beta": sd.get("beta") or ks.get("beta"),
            # 밸류에이션
            "pe_ratio": sd.get("trailingPE"),
            "pb_ratio": pb_ratio,
            "ps_ratio": None,  # yahooquery doesn't directly provide this
            "ev_ebitda": ev_ebitda,
            "ev_sales": ev_sales,
            "dcf_value": None,  # Requires FMP paid plan
            "analyst_target": fd.get("targetMeanPrice"),
            # 수익성 (비율값이므로 *100 변환)
            "roe": fd.get("returnOnEquity"),
            "roa": fd.get("returnOnAssets"),
            "roic": None,
            "gross_margin_ttm": fd.get("grossMargins"),
            "op_margin_ttm": fd.get("operatingMargins"),
            "net_margin_ttm": fd.get("profitMargins"),
            "ebitda_margin_ttm": fd.get("ebitdaMargins"),
            # 성장성
            "revenue_growth": fd.get("revenueGrowth"),
            "eps_growth": ks.get("trailingEps"),
            "fcf_growth": None,
            "op_income_growth": None,
            # 재무건전성
            "current_ratio": fd.get("currentRatio"),
            "debt_to_equity": fd.get("debtToEquity"),
            "net_debt_to_ebitda": None,
            "interest_coverage": None,
            # 주주환원
            "dividend_yield": sd.get("dividendYield"),
            "payout_ratio": sd.get("payoutRatio"),
            # 효율성
            "asset_turnover": None,
            "receivables_turnover": None,
            "inventory_turnover": None,
            "last_updated": datetime.date.today().isoformat(),
        }
    except Exception as e:
        print(f"  [Yahoo Profile Error] {ticker}: {e}")
        return None



# ─────────────────────────────────────────────
# 2. FMP — 연간/분기 풀 재무제표
# ─────────────────────────────────────────────

def fetch_fmp_financials(ticker: str) -> list[dict]:
    """
    FMP에서 연간 5년 + 분기 8분기 재무제표를 가져옵니다.
    손익 + 재무상태표 + 현금흐름을 날짜 기준으로 병합합니다.
    """
    t = ticker.upper()
    results = []

    for period, limit in [("annual", 5), ("quarter", 8)]:
        try:
            # 손익계산서
            r_inc = requests.get(
                f"{FMP_BASE}/income-statement/{t}?period={period}&limit={limit}&apikey={FMP_API_KEY}",
                timeout=15
            )
            # 재무상태표
            r_bs = requests.get(
                f"{FMP_BASE}/balance-sheet-statement/{t}?period={period}&limit={limit}&apikey={FMP_API_KEY}",
                timeout=15
            )
            # 현금흐름표
            r_cf = requests.get(
                f"{FMP_BASE}/cash-flow-statement/{t}?period={period}&limit={limit}&apikey={FMP_API_KEY}",
                timeout=15
            )

            inc_list = r_inc.json() if r_inc.ok else []
            bs_list = r_bs.json() if r_bs.ok else []
            cf_list = r_cf.json() if r_cf.ok else []

            # date 기준으로 딕셔너리화
            bs_map = {row.get("date"): row for row in bs_list}
            cf_map = {row.get("date"): row for row in cf_list}

            prev_revenue = None
            prev_op_income = None
            prev_eps = None

            for inc in inc_list:
                date = inc.get("date")
                if not date:
                    continue

                bs = bs_map.get(date, {})
                cf = cf_map.get(date, {})

                revenue = safe(inc, "revenue")
                cost_of_revenue = safe(inc, "costOfRevenue")
                gross_profit = safe(inc, "grossProfit")
                op_income = safe(inc, "operatingIncome")
                ebitda = safe(inc, "ebitda")
                net_income = safe(inc, "netIncome")
                eps = safe(inc, "eps")
                shares = safe(inc, "weightedAverageShsOut")

                total_assets = safe(bs, "totalAssets")
                total_current_assets = safe(bs, "totalCurrentAssets")
                cash = safe(bs, "cashAndCashEquivalents")
                total_debt = safe(bs, "totalDebt")
                total_liabilities = safe(bs, "totalLiabilities")
                total_current_liabilities = safe(bs, "totalCurrentLiabilities")
                equity = safe(bs, "totalStockholdersEquity")

                ocf = safe(cf, "operatingCashFlow")
                capex = safe(cf, "capitalExpenditure")
                fcf = safe(cf, "freeCashFlow")
                dividends = safe(cf, "dividendsPaid")
                buyback = safe(cf, "commonStockRepurchased")

                # 계산값
                net_debt = (total_debt or 0) - (cash or 0) if total_debt is not None else None

                row = {
                    "period_type": "annual" if period == "annual" else "quarterly",
                    "date": date,
                    "fiscal_year": inc.get("calendarYear", ""),
                    # 손익
                    "revenue": revenue,
                    "cost_of_revenue": cost_of_revenue,
                    "gross_profit": gross_profit,
                    "operating_income": op_income,
                    "ebitda": ebitda,
                    "net_income": net_income,
                    "eps": eps,
                    "shares_outstanding": shares,
                    # 마진율
                    "gross_margin": pct(gross_profit, revenue),
                    "op_margin": pct(op_income, revenue),
                    "net_margin": pct(net_income, revenue),
                    "ebitda_margin": pct(ebitda, revenue),
                    # 성장률
                    "revenue_growth_yoy": yoy_growth(revenue, prev_revenue),
                    "op_income_growth_yoy": yoy_growth(op_income, prev_op_income),
                    "eps_growth_yoy": yoy_growth(eps, prev_eps),
                    # 재무상태표
                    "total_assets": total_assets,
                    "total_current_assets": total_current_assets,
                    "cash_and_equivalents": cash,
                    "total_debt": total_debt,
                    "total_liabilities": total_liabilities,
                    "total_current_liabilities": total_current_liabilities,
                    "shareholders_equity": equity,
                    "net_debt": net_debt,
                    # 재무건전성
                    "current_ratio": round(total_current_assets / total_current_liabilities, 2) if (total_current_assets and total_current_liabilities) else None,
                    "debt_to_equity_ratio": pct(total_debt, equity),
                    # 현금흐름
                    "operating_cash_flow": ocf,
                    "capital_expenditure": capex,
                    "free_cash_flow": fcf,
                    "dividends_paid": dividends,
                    "stock_buyback": buyback,
                    # 수익성
                    "roe": pct(net_income, equity),
                    "roa": pct(net_income, total_assets),
                    "fcf_margin": pct(fcf, revenue),
                }

                results.append(row)

                prev_revenue = revenue
                prev_op_income = op_income
                prev_eps = eps

        except Exception as e:
            print(f"  [FMP Financials Error] {ticker} ({period}): {e}")

    results.sort(key=lambda x: x["date"])
    return results


# ─────────────────────────────────────────────
# 3. SEC EDGAR 폴백 (FMP 실패 시)
# ─────────────────────────────────────────────

def fetch_sec_basic(ticker: str) -> list[dict]:
    """SEC EDGAR에서 기본 손익만 가져오는 폴백"""
    from finance_fetcher import fetch_sec_financials
    try:
        raw = fetch_sec_financials(ticker)
        # 기존 finance_fetcher 포맷을 새 포맷으로 변환
        converted = []
        for r in raw:
            rev = r.get("revenue")
            op = r.get("operating_income")
            net = r.get("net_income")
            converted.append({
                "period_type": r.get("period_type"),
                "date": r.get("date"),
                "fiscal_year": r.get("date", "")[:4],
                "revenue": rev,
                "cost_of_revenue": None,
                "gross_profit": None,
                "operating_income": op,
                "ebitda": None,
                "net_income": net,
                "eps": None,
                "shares_outstanding": None,
                "gross_margin": r.get("gross_margin"),
                "op_margin": pct(op, rev),
                "net_margin": pct(net, rev),
                "ebitda_margin": None,
                "revenue_growth_yoy": None,
                "op_income_growth_yoy": None,
                "eps_growth_yoy": None,
                "total_assets": None, "total_current_assets": None,
                "cash_and_equivalents": None, "total_debt": None,
                "total_liabilities": None, "total_current_liabilities": None,
                "shareholders_equity": None, "net_debt": None,
                "current_ratio": None, "debt_to_equity_ratio": None,
                "operating_cash_flow": None, "capital_expenditure": None,
                "free_cash_flow": None, "dividends_paid": None, "stock_buyback": None,
                "roe": None, "roa": None, "fcf_margin": None,
            })
        return converted
    except Exception as e:
        print(f"  [SEC EDGAR Fallback Error] {ticker}: {e}")
        return []


# ─────────────────────────────────────────────
# 4. 메인 함수
# ─────────────────────────────────────────────

def fetch_full_company_data(ticker: str) -> dict:
    """
    종합 데이터 수집 함수
    반환: {
        "profile": dict | None,       → CompanyProfile 테이블에 적재
        "financials": list[dict],     → FinancialData 테이블에 적재
        "source": str
    }
    """
    print(f"\n{'='*50}")
    print(f"  [{ticker}] Fetching institutional-grade data...")
    print(f"{'='*50}")

    # --- Profile (Yahoo Finance) ---
    print(f"  [1/3] Yahoo Finance profile fetch...")
    profile = fetch_profile_from_yahoo(ticker)
    if profile:
        mktcap = profile.get('market_cap') or 0
        print(f"  OK Profile fetched (MktCap: ${mktcap/1e9:.1f}B, P/E: {profile.get('pe_ratio')}, EV/EBITDA: {profile.get('ev_ebitda')})")
    else:
        print(f"  WARN Profile fetch failed")

    # --- Financials: FMP first, SEC fallback ---
    print(f"  [2/3] FMP Financials (IS+BS+CF)...")
    financials = fetch_fmp_financials(ticker)

    if not financials:
        print(f"  WARN FMP financials failed -> SEC EDGAR fallback...")
        financials = fetch_sec_basic(ticker)
        source = "SEC_EDGAR"

        # Supplement balance sheet & cash flow from yahooquery
        print(f"  [3/3] Supplementing BS+CF from yahooquery...")
        try:
            yq = Ticker(ticker)
            bs_annual = yq.balance_sheet(frequency='a')
            cf_annual = yq.cash_flow(frequency='a')
            inc_annual = yq.income_statement(frequency='a')

            # Build a map by date from yahooquery for supplementing
            def yq_to_map(df):
                if not isinstance(df, __import__('pandas').DataFrame) or df.empty:
                    return {}
                if 'symbol' in df.index.names:
                    df = df.reset_index()
                result = {}
                for _, row in df.iterrows():
                    date_str = str(row.get('asOfDate', ''))[:10]
                    result[date_str] = row.to_dict()
                return result

            bs_map = yq_to_map(bs_annual)
            cf_map = yq_to_map(cf_annual)
            inc_map = yq_to_map(inc_annual)

            def sv(row, *keys):
                for k in keys:
                    v = row.get(k)
                    if v is not None and v == v:
                        return float(v)
                return None

            # Update existing entries with supplemental data
            for f in financials:
                date = f["date"]
                # Find closest date match
                bs = bs_map.get(date, {})
                cf = cf_map.get(date, {})
                inc = inc_map.get(date, {})

                if bs:
                    ta = sv(bs, 'TotalAssets')
                    tca = sv(bs, 'CurrentAssets')
                    cash = sv(bs, 'CashAndCashEquivalents', 'CashCashEquivalentsAndShortTermInvestments')
                    td = sv(bs, 'TotalDebt', 'LongTermDebt')
                    tl = sv(bs, 'TotalLiabilitiesNetMinorityInterest')
                    tcl = sv(bs, 'CurrentLiabilities')
                    eq = sv(bs, 'StockholdersEquity', 'CommonStockEquity')
                    f['total_assets'] = ta
                    f['total_current_assets'] = tca
                    f['cash_and_equivalents'] = cash
                    f['total_debt'] = td
                    f['total_liabilities'] = tl
                    f['total_current_liabilities'] = tcl
                    f['shareholders_equity'] = eq
                    f['net_debt'] = (td or 0) - (cash or 0) if td is not None else None
                    f['current_ratio'] = round(tca / tcl, 2) if (tca and tcl and tcl != 0) else None
                    f['debt_to_equity_ratio'] = pct(td, eq)
                    f['roe'] = pct(f.get('net_income'), eq)
                    f['roa'] = pct(f.get('net_income'), ta)

                if cf:
                    ocf = sv(cf, 'OperatingCashFlow', 'CashFlowFromContinuingOperatingActivities')
                    capex = sv(cf, 'CapitalExpenditure')
                    fcf_val = (ocf or 0) + (capex or 0) if ocf is not None else None
                    dividends = sv(cf, 'CommonStockDividendPaid', 'PaymentOfDividends')
                    buyback = sv(cf, 'RepurchaseOfCapitalStock', 'CommonStockRepurchased')
                    f['operating_cash_flow'] = ocf
                    f['capital_expenditure'] = capex
                    f['free_cash_flow'] = fcf_val
                    f['dividends_paid'] = dividends
                    f['stock_buyback'] = buyback
                    f['fcf_margin'] = pct(fcf_val, f.get('revenue'))

                if inc:
                    gp = sv(inc, 'GrossProfit')
                    ebitda_v = sv(inc, 'EBITDA')
                    cogs = sv(inc, 'CostOfRevenue', 'CostOfGoodsAndServicesSold')
                    eps_v = sv(inc, 'DilutedEPS', 'BasicEPS')
                    f['gross_profit'] = gp
                    f['cost_of_revenue'] = cogs
                    f['ebitda'] = ebitda_v
                    f['eps'] = eps_v
                    rev = f.get('revenue')
                    f['gross_margin'] = pct(gp, rev)
                    f['ebitda_margin'] = pct(ebitda_v, rev)
        except Exception as e:
            print(f"  WARN yahooquery supplement failed: {e}")
    else:
        source = "FMP"
        ann_count = sum(1 for f in financials if f["period_type"] == "annual")
        q_count = sum(1 for f in financials if f["period_type"] == "quarterly")
        print(f"  OK Financials fetched (Annual: {ann_count}, Quarterly: {q_count})")

    # --- Recency check ---
    has_recent = any(
        "2023" in f["date"] or "2024" in f["date"] or "2025" in f["date"]
        for f in financials
    ) if financials else False

    if not has_recent and financials:
        print(f"  WARN Data too old (no 2023+) -> yahooquery full refetch...")
        from finance_fetcher import fetch_financial_data
        yahoo_data = fetch_financial_data(ticker)
        if yahoo_data:
            for r in yahoo_data:
                rev = r.get("revenue")
                op = r.get("operating_income")
                net = r.get("net_income")
                financials.append({
                    "period_type": r.get("period_type"),
                    "date": r.get("date"),
                    "fiscal_year": r.get("date", "")[:4],
                    "revenue": rev, "cost_of_revenue": None,
                    "gross_profit": None, "operating_income": op,
                    "ebitda": None, "net_income": net,
                    "eps": None, "shares_outstanding": None,
                    "gross_margin": r.get("gross_margin"),
                    "op_margin": pct(op, rev), "net_margin": pct(net, rev),
                    "ebitda_margin": None, "revenue_growth_yoy": None,
                    "op_income_growth_yoy": None, "eps_growth_yoy": None,
                    "total_assets": None, "total_current_assets": None,
                    "cash_and_equivalents": None, "total_debt": None,
                    "total_liabilities": None, "total_current_liabilities": None,
                    "shareholders_equity": None, "net_debt": None,
                    "current_ratio": None, "debt_to_equity_ratio": None,
                    "operating_cash_flow": None, "capital_expenditure": None,
                    "free_cash_flow": None, "dividends_paid": None, "stock_buyback": None,
                    "roe": None, "roa": None, "fcf_margin": None,
                })
            source = "YAHOOQUERY"
            financials.sort(key=lambda x: x["date"])

    print(f"  DONE [{ticker}] Source: {source}, Total records: {len(financials)}")
    return {"profile": profile, "financials": financials, "source": source}



# ─────────────────────────────────────────────
# CLI 테스트용
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
    data = fetch_full_company_data(ticker)
    
    print("\n--- PROFILE ---")
    if data["profile"]:
        p = data["profile"]
        print(f"  Sector: {p.get('sector')} | Industry: {p.get('industry_classification')}")
        print(f"  MktCap: ${p.get('market_cap', 0)/1e9:.1f}B | Price: ${p.get('current_price')}")
        print(f"  P/E: {p.get('pe_ratio')} | P/B: {p.get('pb_ratio')} | EV/EBITDA: {p.get('ev_ebitda')}")
        print(f"  ROE: {p.get('roe')} | ROA: {p.get('roa')} | ROIC: {p.get('roic')}")
        print(f"  Gross Margin: {p.get('gross_margin_ttm')} | Op Margin: {p.get('op_margin_ttm')}")
        print(f"  DCF Value: ${p.get('dcf_value')} | Dividend Yield: {p.get('dividend_yield')}")
    
    print(f"\n--- FINANCIALS ({len(data['financials'])} records) ---")
    for f in data["financials"][-5:]:
        print(f"  {f['date']} [{f['period_type']}]  Rev: ${(f.get('revenue') or 0)/1e9:.2f}B  "
              f"OpInc: ${(f.get('operating_income') or 0)/1e9:.2f}B  "
              f"FCF: ${(f.get('free_cash_flow') or 0)/1e9:.2f}B  "
              f"OPM: {f.get('op_margin')}%")
