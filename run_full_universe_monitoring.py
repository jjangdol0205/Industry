# -*- coding: utf-8 -*-
import sqlite3
import os
import sys
import json

sys.stdout.reconfigure(encoding='utf-8')

db_path = os.path.join(os.path.dirname(__file__), "InvestmentPortal", "backend", "investment_portal.db")
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Get all unique companies with profile and industry info
query = """
SELECT c.id, c.name, c.ticker, c.industry_id,
       COALESCE(ir.title, '기타') AS industry_title,
       c.role_description, c.future_growth,
       COALESCE(c.portfolio_tier, 'Standard') AS portfolio_tier,
       c.principle_reason,
       cp.current_price, cp.high_52w, cp.mdd_pct,
       cp.buy_signal, cp.roe, cp.op_margin_ttm, cp.gross_margin_ttm, cp.market_cap,
       cp.sector, cp.industry_classification
FROM companies c
LEFT JOIN industry_reports ir ON c.industry_id = ir.id
LEFT JOIN company_profiles cp ON c.id = cp.company_id
ORDER BY 
    CASE COALESCE(c.portfolio_tier, 'Standard')
        WHEN 'Core' THEN 1
        WHEN 'Satellite' THEN 2
        WHEN 'Watchlist' THEN 3
        ELSE 4
    END, c.id
"""

cur.execute(query)
rows = cur.fetchall()

seen_tickers = set()
universe = []

for r in rows:
    tk = r['ticker']
    if tk:
        tk_clean = tk.strip().upper()
        if tk_clean in seen_tickers:
            continue
        seen_tickers.add(tk_clean)
    universe.append(dict(r))

print(f"Loaded {len(universe)} unique stocks into Universe Monitoring.")

# Function to evaluate 4-step principles
def evaluate_stock(s):
    name = s['name']
    ticker = s['ticker'] or ''
    tier = s['portfolio_tier']
    reason = s['principle_reason'] or ''
    role = s['role_description'] or ''
    growth = s['future_growth'] or ''
    mdd = s['mdd_pct']
    opm = s['op_margin_ttm']
    roe = s['roe']
    gpm = s['gross_margin_ttm']
    
    # 1. Check Buyability (Business Model & Bottleneck Moat)
    # Price independent
    is_buyable = False
    buyable_reason = ""
    
    # Criteria for Buyability:
    # Tier is Core/Satellite/Watchlist OR has bottleneck keywords in role/growth/reason OR high profitability (OPM >= 20% or ROE >= 20%)
    has_moat_keywords = any(kw in (reason + role + growth).lower() for kw in [
        '독점', '1위', '병목', '소모품', '락인', 'moat', 'euv', 'cuda', '수술로봇', '액체냉각', 'ups', '원자력', '오픈쇼핑', '수주잔고', '리들샷', '특허', '과점'
    ])
    
    if tier in ['Core', 'Satellite', 'Watchlist'] or has_moat_keywords or (opm and opm >= 0.20) or (roe and roe >= 0.20):
        is_buyable = True
        if reason:
            buyable_reason = reason
        elif has_moat_keywords:
            buyable_reason = f"산업 내 강력한 기술/영업 독점력 및 병목 지위 보유 ({growth[:50]})"
        else:
            buyable_reason = f"고수익성 고해자 기업 (OPM {(opm*100):.1f}% / ROE {(roe*100):.1f}%)" if opm and roe else "병목 경쟁력 보유"
    else:
        is_buyable = False
        buyable_reason = "산업 내 독점적 병목 진입장벽 미흡 또는 범용 경쟁 구조 (관망 종목)"
        
    # 2. Tier classification (Core vs Satellite vs Watchlist vs Standard)
    suggested_tier = tier
    if is_buyable:
        if tier in ['Core', 'Satellite', 'Watchlist']:
            suggested_tier = tier
        else:
            # Classify standard stock if it has strong metrics
            if (opm and opm >= 0.25) or (roe and roe >= 0.25) or '1위' in (role+growth) or '독점' in (role+growth):
                suggested_tier = 'Core'
            else:
                suggested_tier = 'Satellite'
                
    return {
        "id": s['id'],
        "name": name,
        "ticker": ticker,
        "industry": s['industry_title'],
        "current_price": s['current_price'],
        "high_52w": s['high_52w'],
        "mdd_pct": s['mdd_pct'],
        "buy_signal": s['buy_signal'],
        "is_buyable": is_buyable,
        "buyable_reason": buyable_reason,
        "current_tier": tier,
        "suggested_tier": suggested_tier,
        "principle_reason": s['principle_reason']
    }

evaluated = [evaluate_stock(s) for s in universe]

# Save evaluated universe to JSON for quick reference
with open('universe_evaluated.json', 'w', encoding='utf-8') as f:
    json.dump(evaluated, f, ensure_ascii=False, indent=2)

print("Saved evaluated universe to universe_evaluated.json")
