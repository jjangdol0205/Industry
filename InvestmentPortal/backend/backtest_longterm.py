"""
2000년부터 전체 재무 이력 수집 + 주도주 백테스트
=================================================
- yfinance로 미국 상장 기업 연간 재무제표 전수 수집
- 한국 주식(.KS/.KQ)은 데이터 한계로 가능 범위만 수집
- 2000~2025년 연도별 채점 → 익년도 매출 성장률로 검증
"""

import sqlite3, sys, math, json, time
from datetime import datetime
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

try:
    import yfinance as yf
    import pandas as pd
except ImportError:
    print("yfinance/pandas 없음. 설치 필요")
    sys.exit(1)

DB_PATH = 'InvestmentPortal/backend/investment_portal.db'
HIST_TABLE = 'financial_data_history'  # 확장 이력 테이블

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# ── 이력 테이블 생성 (없으면) ─────────────────────────────────
cur.execute(f'''
    CREATE TABLE IF NOT EXISTS {HIST_TABLE} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        ticker TEXT,
        fiscal_year INTEGER NOT NULL,
        revenue REAL,
        gross_profit REAL,
        operating_income REAL,
        net_income REAL,
        free_cash_flow REAL,
        total_assets REAL,
        total_debt REAL,
        shareholders_equity REAL,
        gross_margin REAL,
        op_margin REAL,
        net_margin REAL,
        fcf_margin REAL,
        roe REAL,
        source TEXT DEFAULT 'yfinance',
        fetched_at TEXT,
        UNIQUE(company_id, fiscal_year)
    )
''')
conn.commit()

# ── 전체 기업 목록 ────────────────────────────────────────────
cur.execute('''
    SELECT c.id, c.name, c.ticker, ir.tag as industry, c.display_order
    FROM companies c
    LEFT JOIN industry_reports ir ON c.industry_id = ir.id
    ORDER BY c.ticker
''')
companies = [dict(zip(['id','name','ticker','industry','display_order'], r)) for r in cur.fetchall()]

def safe(v):
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except:
        return None

# ── yfinance 수집 ─────────────────────────────────────────────
print(f"총 {len(companies)}개 기업 이력 수집 시작 (2000~2025)")
print("한국 주식(.KS/.KQ)은 yfinance 데이터 한계로 일부만 수집됩니다.\n")

fetched_count = 0
failed = []

for idx, c in enumerate(companies):
    ticker = c['ticker']
    cid = c['id']
    
    # 이미 수집된 기업은 스킵 (25년치 이상)
    cur.execute(f'SELECT COUNT(*) FROM {HIST_TABLE} WHERE company_id=?', (cid,))
    existing = cur.fetchone()[0]
    if existing >= 10:
        print(f"  [{idx+1:3}/{len(companies)}] {ticker:12} 스킵 (기존 {existing}년치)")
        continue
    
    print(f"  [{idx+1:3}/{len(companies)}] {ticker:12} 수집 중...", end='', flush=True)
    
    try:
        stock = yf.Ticker(ticker)
        
        # 연간 재무제표 수집
        income = stock.financials        # 손익계산서
        balance = stock.balance_sheet    # 재무상태표
        cashflow = stock.cashflow        # 현금흐름표
        
        if income is None or income.empty:
            print(f" ❌ 데이터없음")
            failed.append(ticker)
            continue
        
        years_added = 0
        for col in income.columns:
            try:
                yr = col.year if hasattr(col, 'year') else int(str(col)[:4])
                if yr < 2000: continue
                
                # 손익
                rev  = safe(income.loc['Total Revenue', col]) if 'Total Revenue' in income.index else None
                gp   = safe(income.loc['Gross Profit', col]) if 'Gross Profit' in income.index else None
                op   = safe(income.loc['Operating Income', col]) if 'Operating Income' in income.index else None
                net  = safe(income.loc['Net Income', col]) if 'Net Income' in income.index else None
                
                if not rev: continue  # 매출 없으면 의미없음
                
                # 재무상태표
                ta = she = td = None
                if balance is not None and not balance.empty and col in balance.columns:
                    ta  = safe(balance.loc['Total Assets', col]) if 'Total Assets' in balance.index else None
                    she = safe(balance.loc['Stockholders Equity', col]) if 'Stockholders Equity' in balance.index else (
                          safe(balance.loc['Total Equity Gross Minority Interest', col]) if 'Total Equity Gross Minority Interest' in balance.index else None)
                    td  = safe(balance.loc['Total Debt', col]) if 'Total Debt' in balance.index else None
                
                # 현금흐름
                fcf = None
                if cashflow is not None and not cashflow.empty and col in cashflow.columns:
                    ocf  = safe(cashflow.loc['Operating Cash Flow', col]) if 'Operating Cash Flow' in cashflow.index else None
                    capx = safe(cashflow.loc['Capital Expenditure', col]) if 'Capital Expenditure' in cashflow.index else None
                    if ocf and capx:
                        fcf = ocf + capx  # capex는 보통 음수
                
                # 마진 계산
                gm  = gp / rev if (gp and rev) else None
                om  = op / rev if (op and rev) else None
                nm  = net / rev if (net and rev) else None
                fcfm = fcf / rev if (fcf and rev) else None
                roe = net / she if (net and she and she > 0) else None
                
                cur.execute(f'''
                    INSERT OR REPLACE INTO {HIST_TABLE}
                    (company_id, ticker, fiscal_year, revenue, gross_profit, operating_income,
                     net_income, free_cash_flow, total_assets, total_debt, shareholders_equity,
                     gross_margin, op_margin, net_margin, fcf_margin, roe, fetched_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ''', (cid, ticker, yr, rev, gp, op, net, fcf, ta, td, she,
                      gm, om, nm, fcfm, roe, datetime.now().isoformat()))
                years_added += 1
                
            except Exception as e2:
                continue
        
        conn.commit()
        fetched_count += 1
        print(f" ✅ {years_added}년치")
        time.sleep(0.3)  # API 제한 방지
        
    except Exception as e:
        print(f" ❌ {str(e)[:40]}")
        failed.append(ticker)
        time.sleep(0.5)

print(f"\n수집 완료: {fetched_count}개 기업 성공, {len(failed)}개 실패")
print(f"실패: {failed[:10]}")

# ── 백테스트 함수 ─────────────────────────────────────────────
def safe_db(v):
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except:
        return None

def calc_leading_score(d):
    score = 0
    
    rev    = safe_db(d.get('revenue'))
    gm     = safe_db(d.get('gross_margin'))
    om     = safe_db(d.get('op_margin'))
    nm     = safe_db(d.get('net_margin'))
    fcfm   = safe_db(d.get('fcf_margin'))
    roe    = safe_db(d.get('roe'))
    rev_g  = safe_db(d.get('rev_growth'))

    # A. 성장 모멘텀 (40점)
    if rev_g is not None:
        if rev_g >= 0.50:    score += 40
        elif rev_g >= 0.25:  score += 32
        elif rev_g >= 0.15:  score += 24
        elif rev_g >= 0.05:  score += 14
        elif rev_g >= 0:     score += 6
        else:                score += 0
    else:
        score += 10  # 성장률 모름 → 중립

    # B. 마진/해자 (30점)
    gm_pct = (gm * 100) if gm and abs(gm) <= 1 else gm
    if gm_pct:
        if gm_pct >= 70:    score += 15
        elif gm_pct >= 55:  score += 12
        elif gm_pct >= 40:  score += 9
        elif gm_pct >= 25:  score += 5
        elif gm_pct >= 10:  score += 2

    fcfm_pct = (fcfm * 100) if fcfm and abs(fcfm) <= 1 else fcfm
    if fcfm_pct:
        if fcfm_pct >= 25:    score += 10
        elif fcfm_pct >= 15:  score += 8
        elif fcfm_pct >= 5:   score += 5
        elif fcfm_pct >= 0:   score += 2

    roe_pct = (roe * 100) if roe and abs(roe) <= 1 else roe
    if roe_pct and roe_pct > 0:
        if roe_pct >= 30:    score += 5
        elif roe_pct >= 20:  score += 4
        elif roe_pct >= 10:  score += 2

    # C. 수익성 지속 (20점)
    nm_pct = (nm * 100) if nm and abs(nm) <= 1 else nm
    if nm_pct:
        if nm_pct >= 20:    score += 10
        elif nm_pct >= 10:  score += 8
        elif nm_pct >= 0:   score += 4
        elif nm_pct >= -20: score += 0
        else:               score -= 5

    # 규모 보너스 (10점)
    if rev:
        if rev >= 100e9:   score += 10
        elif rev >= 10e9:  score += 7
        elif rev >= 1e9:   score += 4
        elif rev >= 0.1e9: score += 2

    return max(0, min(100, score))

# ── 백테스트 실행 ─────────────────────────────────────────────
print("\n" + "=" * 70)
print("📊 백테스트: 2000~2024년 주도주 스코어 → 익년도 성과")
print("=" * 70)

# NVDA, GOOGL 등 장기 데이터 있는 기업만 추려서 통계 의미 있게
backtest_summary = {}

for test_yr in range(2000, 2025):
    result_yr = test_yr + 1
    
    # 해당 연도 데이터 있는 기업들 수집
    cur.execute(f'''
        SELECT h.company_id, h.ticker, h.revenue, h.gross_margin, h.op_margin,
               h.net_margin, h.fcf_margin, h.roe,
               h2.revenue as next_rev
        FROM {HIST_TABLE} h
        LEFT JOIN {HIST_TABLE} h2 ON h.company_id=h2.company_id AND h2.fiscal_year=?
        WHERE h.fiscal_year=? AND h.revenue IS NOT NULL
    ''', (result_yr, test_yr))
    rows = cur.fetchall()
    
    if len(rows) < 3:
        continue
    
    grade_groups = defaultdict(list)
    for r in rows:
        base_rev = safe_db(r[2])
        next_rev = safe_db(r[8])
        if not base_rev or not next_rev: continue
        
        # 전년도 데이터 (성장률 계산용)
        cur.execute(f'SELECT revenue FROM {HIST_TABLE} WHERE company_id=? AND fiscal_year=?', (r[0], test_yr-1))
        prev = cur.fetchone()
        prev_rev = safe_db(prev[0]) if prev else None
        
        rev_growth = (base_rev - prev_rev) / abs(prev_rev) if (prev_rev and prev_rev != 0) else None
        
        d = {
            'revenue': base_rev,
            'gross_margin': r[3],
            'op_margin': r[4],
            'net_margin': r[5],
            'fcf_margin': r[6],
            'roe': r[7],
            'rev_growth': rev_growth,
        }
        score = calc_leading_score(d)
        actual_growth = (next_rev - base_rev) / abs(base_rev) * 100
        
        if score >= 85:   grade = 'S(85+)'
        elif score >= 70: grade = 'A(70-84)'
        elif score >= 55: grade = 'B(55-69)'
        elif score >= 40: grade = 'C(40-54)'
        else:             grade = 'D(<40)'
        
        grade_groups[grade].append(actual_growth)
    
    if not grade_groups:
        continue
    
    year_result = {}
    for grade, growths in grade_groups.items():
        year_result[grade] = {
            'avg': sum(growths)/len(growths),
            'n': len(growths),
            'beat_10pct': sum(1 for g in growths if g > 10) / len(growths) * 100
        }
    backtest_summary[test_yr] = year_result

# 연도별 결과 출력
print(f"\n{'연도':6} {'S등급 평균':>12} {'A등급 평균':>12} {'D등급 평균':>12} {'기업수':>6}")
print("-" * 55)
for yr in sorted(backtest_summary.keys()):
    res = backtest_summary[yr]
    s_avg = f"{res['S(85+)']['avg']:+.1f}% ({res['S(85+)']['n']})" if 'S(85+)' in res else '-'
    a_avg = f"{res['A(70-84)']['avg']:+.1f}% ({res['A(70-84)']['n']})" if 'A(70-84)' in res else '-'
    d_avg = f"{res['D(<40)']['avg']:+.1f}% ({res['D(<40)']['n']})" if 'D(<40)' in res else '-'
    total = sum(v['n'] for v in res.values())
    print(f"{yr}년  {s_avg:>20} {a_avg:>20} {d_avg:>20} {total:>6}")

# 등급별 전체 기간 평균 계산
print("\n" + "=" * 70)
print("📈 전체 기간 (2000~2024) 등급별 평균 성과")
print("=" * 70)
all_grades = defaultdict(list)
for yr_data in backtest_summary.values():
    for grade, stats in yr_data.items():
        all_grades[grade].append(stats['avg'])

grade_order = ['S(85+)', 'A(70-84)', 'B(55-69)', 'C(40-54)', 'D(<40)']
print(f"\n{'등급':12} {'평균 익년도 매출성장':>20} {'관측 연-기업':>12}")
print("-" * 48)
for g in grade_order:
    if g in all_grades:
        avgs = all_grades[g]
        total_avg = sum(avgs) / len(avgs)
        print(f"{g:12}  {total_avg:>+18.1f}%  {len(avgs):>12}회")

print("\n※ 매출 성장률로 검증 (주가 데이터 없어 펀더멘탈 기반 검증)")
print("   S/A 등급이 D등급보다 성장률 높으면 스코어링 유효")

# JSON 저장
with open('InvestmentPortal/backend/backtest_2000_2025.json', 'w', encoding='utf-8') as f:
    json.dump({
        'period': '2000-2025',
        'description': '주도주 스코어 → 익년도 매출성장률 검증',
        'by_year': backtest_summary,
        'overall': {g: {'avg': sum(v)/len(v), 'n': len(v)} for g, v in all_grades.items()}
    }, f, ensure_ascii=False, indent=2)

print(f"\n✅ 저장: backtest_2000_2025.json")
conn.close()
