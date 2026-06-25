"""
기업 투자 순위 자동 산정 스크립트
- 산업별 기업 투자 점수 계산 (Quant + Moat + Growth)
- display_order 업데이트
- GitHub Actions 월간 자동 실행용
"""
import sqlite3, sys, math, json
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = 'investment_portal.db'

def safe(v):
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except:
        return None

def calc_investment_score(c, fin):
    """투자 매력도 종합 점수 (0~100점)"""
    score = 50
    details = []

    # ── 1. 수익성 / 해자 (30점) ────────────────────────────
    gm = safe(c.get('gm_ttm'))
    if gm is not None:
        gm_val = gm if gm > 1 else gm * 100  # 0~1 또는 0~100 대응
        if gm_val > 60:   score += 18; details.append(f"초고마진GPM{gm_val:.0f}%")
        elif gm_val > 40: score += 12; details.append(f"고마진GPM{gm_val:.0f}%")
        elif gm_val > 20: score += 6;  details.append(f"중간마진GPM{gm_val:.0f}%")
        elif gm_val > 0:  score += 2
        else:             score -= 8;  details.append("저마진")

    roe = safe(c.get('roe'))
    if roe is not None:
        roe_val = roe if roe > 1 else roe * 100
        if roe_val > 25:  score += 12; details.append(f"고ROE{roe_val:.0f}%")
        elif roe_val > 15: score += 7;  details.append(f"적정ROE{roe_val:.0f}%")
        elif roe_val < 0: score -= 10; details.append("마이너스ROE")

    # ── 2. 성장성 (25점) ──────────────────────────────────
    rg = safe(c.get('rev_growth'))
    if rg is not None:
        rg_val = rg if abs(rg) <= 1 else rg / 100
        if rg_val > 0.5:   score += 22; details.append(f"초고성장{rg_val*100:.0f}%")
        elif rg_val > 0.25: score += 16; details.append(f"고성장{rg_val*100:.0f}%")
        elif rg_val > 0.10: score += 10; details.append(f"성장{rg_val*100:.0f}%")
        elif rg_val > 0:    score += 4
        else:               score -= 12; details.append(f"역성장{rg_val*100:.0f}%")

    # ── 3. 밸류에이션 (25점) ──────────────────────────────
    pe = safe(c.get('pe'))
    ev_sales = safe(c.get('ev_sales'))
    nm = safe(c.get('nm_ttm'))

    if pe is not None and pe > 0:
        if pe < 15:   score += 20; details.append(f"저평가PER{pe:.0f}x")
        elif pe < 25: score += 13; details.append(f"적정PER{pe:.0f}x")
        elif pe < 40: score += 6
        elif pe < 80: score -= 3
        else:         score -= 8;  details.append(f"고평가PER{pe:.0f}x")
    elif ev_sales and ev_sales > 0:
        if ev_sales < 3:   score += 15; details.append(f"저EV/S{ev_sales:.1f}x")
        elif ev_sales < 8: score += 7
        elif ev_sales > 30: score -= 5

    # 적자면 페널티
    if nm is not None:
        nm_val = nm if abs(nm) <= 1 else nm / 100
        if nm_val < -0.2: score -= 15; details.append("심각한적자")
        elif nm_val < 0:  score -= 8;  details.append("적자")
        elif nm_val > 0.2: score += 8;  details.append(f"고순이익률{nm_val*100:.0f}%")

    # ── 4. 재무건전성 (10점) ──────────────────────────────
    de = safe(c.get('d_e'))
    if de is not None:
        if de < 30:    score += 10; details.append("무부채")
        elif de < 100: score += 5;  details.append("건전부채")
        elif de > 300: score -= 8;  details.append("과다부채")

    # ── 5. FCF (10점) ─────────────────────────────────────
    fcf = safe(fin.get('fcf'))
    rev = safe(fin.get('revenue'))
    if fcf and rev and rev > 0:
        fcfm = fcf / rev
        if fcfm > 0.2:  score += 10; details.append(f"고FCF마진{fcfm*100:.0f}%")
        elif fcfm > 0.1: score += 6
        elif fcfm > 0:   score += 2
        else:            score -= 5;  details.append("마이너스FCF")

    return max(0, min(100, score)), details

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# ── 전체 기업 + 프로파일 로드 ────────────────────────────────
cur.execute('''
    SELECT c.id, c.name, c.ticker, ir.tag as industry, ir.id as industry_id,
        cp.current_price, cp.market_cap, cp.pe_ratio, cp.ev_sales,
        cp.revenue_growth, cp.gross_margin_ttm, cp.net_margin_ttm, cp.op_margin_ttm,
        cp.roe, cp.debt_to_equity, cp.current_ratio
    FROM companies c
    LEFT JOIN industry_reports ir ON c.industry_id = ir.id
    LEFT JOIN company_profiles cp ON c.id = cp.company_id
    ORDER BY ir.tag, c.ticker
''')
companies = cur.fetchall()
cols = ['id','name','ticker','industry','industry_id','price','mc','pe','ev_sales',
        'rev_growth','gm_ttm','nm_ttm','om_ttm','roe','d_e','curr_ratio']
companies = [dict(zip(cols, r)) for r in companies]

# ── 최신 연간 재무 로드 ──────────────────────────────────────
def get_latest_fin(cid):
    cur.execute('''
        SELECT revenue, gross_profit, operating_income, net_income, free_cash_flow,
               total_assets, shareholders_equity, total_debt
        FROM financial_data
        WHERE company_id=? AND period_type='annual'
        ORDER BY date DESC LIMIT 1
    ''', (cid,))
    r = cur.fetchone()
    if not r: return {}
    return dict(zip(['revenue','gp','op_income','net_income','fcf','ta','equity','debt'], r))

# ── 점수 계산 ─────────────────────────────────────────────────
print("=== 투자 점수 계산 시작 ===")
scored = []
for c in companies:
    fin = get_latest_fin(c['id'])
    score, details = calc_investment_score(c, fin)
    scored.append({**c, 'score': score, 'details': details})

# ── 산업별 순위 산정 ──────────────────────────────────────────
from collections import defaultdict
by_industry = defaultdict(list)
for c in scored:
    by_industry[c['industry']].append(c)

rank_date = datetime.now().strftime('%Y-%m-%d')
print(f"\n=== 산업별 투자 순위 ({rank_date}) ===")

for industry, comps in sorted(by_industry.items()):
    comps.sort(key=lambda x: x['score'], reverse=True)
    print(f"\n[{industry}] ({len(comps)}개)")
    for rank, c in enumerate(comps, 1):
        # DB 업데이트
        cur.execute(
            'UPDATE companies SET display_order=? WHERE id=?',
            (rank, c['id'])
        )
        detail_str = ', '.join(c['details'][:3])
        print(f"  {rank:2}위 {c['ticker']:6} {c['name'][:22]:22} {c['score']}점  [{detail_str}]")

conn.commit()
print(f"\n=== 순위 업데이트 완료 ({rank_date}) ===")

# ── 전체 TOP 10 ───────────────────────────────────────────────
all_sorted = sorted(scored, key=lambda x: x['score'], reverse=True)
print("\n=== 전체 산업 통합 TOP 10 ===")
for i, c in enumerate(all_sorted[:10], 1):
    print(f"  {i:2}위 [{c['industry']:5}] {c['ticker']:6} {c['name'][:22]} {c['score']}점")

# 순위 로그를 JSON으로도 저장
rank_log = {
    'date': rank_date,
    'rankings': {}
}
for industry, comps in by_industry.items():
    rank_log['rankings'][industry] = [
        {'rank': i+1, 'ticker': c['ticker'], 'name': c['name'], 'score': c['score']}
        for i, c in enumerate(comps)
    ]

with open('ranking_log.json', 'w', encoding='utf-8') as f:
    json.dump(rank_log, f, ensure_ascii=False, indent=2)
print("\n순위 로그 저장: ranking_log.json")

conn.close()
