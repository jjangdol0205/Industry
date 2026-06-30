"""
주도주 스코어링 v2 - 백테스트 결함 수정 후 DB 반영
====================================================
수정 사항:
1. FCF 마이너스 기업 성장 점수 50% 감점 (진짜 주도주 = 성장 + 현금창출)
2. 적자 심각도별 차등 페널티 강화
3. 최종 display_order 업데이트
"""

import sqlite3, sys, math, json
from collections import defaultdict
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')
DB_PATH = 'InvestmentPortal/backend/investment_portal.db'

def safe(v):
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except:
        return None

def pct(v):
    if v is None: return None
    f = float(v)
    return f * 100 if abs(f) <= 1 else f

def calc_leading_score_v2(d):
    """
    주도주 스코어 v2 (100점)
    
    핵심 철학:
    - 진짜 주도주 = 고성장 + 현금창출 능력 (FCF+) 동시 보유
    - FCF 마이너스 기업은 '투기 성장주'로 구분 → 성장 점수 절반
    - 적자 기업은 주도주 자격 없음 (강한 패널티)
    """
    score = 0
    details = {}

    rev     = safe(d.get('revenue'))
    gm      = pct(d.get('gross_margin'))
    om      = pct(d.get('op_margin'))
    nm      = pct(d.get('net_margin'))
    fcfm    = pct(d.get('fcf_margin'))
    roe     = pct(d.get('roe'))
    rev_g   = safe(d.get('rev_growth'))  # 소수점 형태 (0.5 = 50%)
    op_g    = safe(d.get('op_growth'))

    # ── 품질 게이트 판단 ─────────────────────────────────────
    is_fcf_positive  = fcfm is not None and fcfm > 0
    is_profitable    = nm is not None and nm > 0
    is_high_quality  = is_fcf_positive and is_profitable
    quality_modifier = 1.0 if is_high_quality else (0.5 if is_fcf_positive else 0.4)

    # ── A. 성장 모멘텀 (40점, 품질 배수 적용) ─────────────────
    a_raw = 0
    if rev_g is not None:
        if rev_g >= 0.50:    a_raw = 40
        elif rev_g >= 0.25:  a_raw = 32
        elif rev_g >= 0.15:  a_raw = 24
        elif rev_g >= 0.05:  a_raw = 14
        elif rev_g >= 0:     a_raw = 6
        else:                a_raw = 0
        details['매출성장'] = f"{rev_g*100:.1f}%"
    else:
        a_raw = 10  # 데이터 없으면 중립
        details['매출성장'] = 'N/A'

    # FCF 마이너스면 성장 점수 40% 감점 (투기 성장 구분)
    a_score = int(a_raw * quality_modifier)
    score += a_score
    details['A_성장(품질조정)'] = a_score

    # ── B. 마진 / 해자 (30점) ─────────────────────────────────
    b_score = 0

    # B1. GPM (15점)
    if gm is not None:
        if gm >= 70:    b_score += 15; details['GPM'] = f"{gm:.1f}%"
        elif gm >= 55:  b_score += 12; details['GPM'] = f"{gm:.1f}%"
        elif gm >= 40:  b_score += 9;  details['GPM'] = f"{gm:.1f}%"
        elif gm >= 25:  b_score += 5;  details['GPM'] = f"{gm:.1f}%"
        elif gm >= 10:  b_score += 2;  details['GPM'] = f"{gm:.1f}%"
        elif gm < 0:    b_score -= 5;  details['GPM'] = f"❌{gm:.1f}%"

    # B2. FCF 마진 (10점) — 핵심 차별화 지표
    if fcfm is not None:
        if fcfm >= 25:    b_score += 10; details['FCF마진'] = f"{fcfm:.1f}%"
        elif fcfm >= 15:  b_score += 8;  details['FCF마진'] = f"{fcfm:.1f}%"
        elif fcfm >= 5:   b_score += 5;  details['FCF마진'] = f"{fcfm:.1f}%"
        elif fcfm >= 0:   b_score += 2;  details['FCF마진'] = f"{fcfm:.1f}%"
        elif fcfm >= -20: b_score -= 3;  details['FCF마진'] = f"❌{fcfm:.1f}%"
        elif fcfm >= -100: b_score -= 7; details['FCF마진'] = f"❌❌{fcfm:.1f}%"
        else:              b_score -= 10; details['FCF마진'] = f"❌❌❌{fcfm:.1f}%"

    # B3. ROE (5점)
    if roe and roe > 0:
        if roe >= 30:    b_score += 5
        elif roe >= 20:  b_score += 4
        elif roe >= 10:  b_score += 2
        details['ROE'] = f"{roe:.1f}%"

    score += max(-10, min(30, b_score))
    details['B_마진해자'] = max(-10, min(30, b_score))

    # ── C. 수익성 지속성 (20점) ──────────────────────────────
    c_score = 0

    # C1. 순이익률 (10점) — 적자 = 주도주 자격 박탈
    if nm is not None:
        if nm >= 20:     c_score += 10; details['순이익률'] = f"{nm:.1f}%"
        elif nm >= 10:   c_score += 8;  details['순이익률'] = f"{nm:.1f}%"
        elif nm >= 5:    c_score += 6;  details['순이익률'] = f"{nm:.1f}%"
        elif nm >= 0:    c_score += 3;  details['순이익률'] = f"{nm:.1f}%"
        elif nm >= -10:  c_score -= 5;  details['순이익률'] = f"❌{nm:.1f}%"
        elif nm >= -30:  c_score -= 10; details['순이익률'] = f"❌❌{nm:.1f}%"
        else:            c_score -= 15; details['순이익률'] = f"❌❌❌{nm:.1f}%"

    # C2. 부채비율 (10점)
    de = pct(d.get('debt_to_equity'))
    if de is not None:
        if de <= 0:      c_score += 10
        elif de <= 50:   c_score += 8
        elif de <= 100:  c_score += 6
        elif de <= 200:  c_score += 3
        else:            c_score += 0
        details['부채비율'] = f"{de:.1f}%"

    score += max(-15, min(20, c_score))
    details['C_재무안전성'] = max(-15, min(20, c_score))

    # ── D. 규모 + 리더십 (10점) ──────────────────────────────
    d_score = 0
    if rev:
        if rev >= 100e9:   d_score += 5
        elif rev >= 10e9:  d_score += 4
        elif rev >= 1e9:   d_score += 3
        elif rev >= 0.1e9: d_score += 1

    leader = safe(d.get('leader_bonus', 3))
    d_score += min(5, leader)

    score += min(10, d_score)
    details['D_규모리더십'] = min(10, d_score)

    final = max(0, min(100, score))

    if final >= 85:   grade = 'S'
    elif final >= 70: grade = 'A'
    elif final >= 55: grade = 'B'
    elif final >= 40: grade = 'C'
    else:             grade = 'D'

    return final, grade, details


# ── DB 연결 + 전체 기업 채점 ─────────────────────────────────
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute('''
    SELECT c.id, c.name, c.ticker, ir.tag as industry, c.display_order
    FROM companies c
    LEFT JOIN industry_reports ir ON c.industry_id = ir.id
''')
companies = [dict(zip(['id','name','ticker','industry','display_order'], r)) for r in cur.fetchall()]

def get_fin(cid, year=None):
    if year:
        cur.execute('''
            SELECT fiscal_year, revenue, gross_profit, operating_income, net_income,
                   free_cash_flow, gross_margin, op_margin, net_margin, fcf_margin, roe,
                   total_assets, total_debt, shareholders_equity
            FROM financial_data_history WHERE company_id=? AND fiscal_year=?
        ''', (cid, year))
    else:
        cur.execute('''
            SELECT fiscal_year, revenue, gross_profit, operating_income, net_income,
                   free_cash_flow, gross_margin, op_margin, net_margin, fcf_margin, roe,
                   total_assets, total_debt, shareholders_equity
            FROM financial_data_history WHERE company_id=? ORDER BY fiscal_year DESC LIMIT 1
        ''', (cid,))
    r = cur.fetchone()
    if not r: return None
    cols = ['fiscal_year','revenue','gross_profit','operating_income','net_income',
            'free_cash_flow','gross_margin','op_margin','net_margin','fcf_margin','roe',
            'total_assets','total_debt','shareholders_equity']
    return dict(zip(cols, r))

# ── 4년 백테스트 (수정 로직 검증) ──────────────────────────
print("=" * 70)
print("📊 수정 로직 백테스트 (2022→2025, v2)")
print("=" * 70)

for test_yr, result_yr in [(2022, 2023), (2023, 2024), (2024, 2025)]:
    grade_groups = defaultdict(list)

    for c in companies:
        fin_base = get_fin(c['id'], test_yr)
        fin_prev = get_fin(c['id'], test_yr - 1)
        fin_next = get_fin(c['id'], result_yr)
        if not fin_base or not fin_next: continue

        d = dict(fin_base)
        if fin_prev and fin_prev.get('revenue') and fin_base.get('revenue'):
            prev_r = safe(fin_prev['revenue'])
            base_r = safe(fin_base['revenue'])
            d['rev_growth'] = (base_r - prev_r) / abs(prev_r) if prev_r else None

        order = c.get('display_order') or 99
        d['leader_bonus'] = max(0, 5 - order) if order <= 5 else 0

        score, grade, _ = calc_leading_score_v2(d)

        base_r = safe(fin_base.get('revenue'))
        next_r = safe(fin_next.get('revenue'))
        if base_r and next_r and base_r > 0:
            actual_g = (next_r - base_r) / base_r * 100
            grade_groups[f'{grade}({score})_grade'].append((grade, actual_g, score))

    # 집계
    by_grade = defaultdict(list)
    for items in grade_groups.values():
        for grade, g, score in items:
            by_grade[grade].append(g)

    print(f"\n[{test_yr}→{result_yr}년] 등급별 평균 매출성장:")
    for g in ['S', 'A', 'B', 'C', 'D']:
        if g in by_grade:
            gs = by_grade[g]
            avg = sum(gs) / len(gs)
            pos = sum(1 for x in gs if x > 10) / len(gs) * 100
            print(f"  {g}등급: {avg:>+7.1f}%  (N={len(gs):3}, 10%초과비율={pos:.0f}%)")

# ── 최종 2025년 기준 전체 순위 산정 + DB 업데이트 ────────────
print("\n" + "=" * 70)
print("🏆 v2 최종 순위 (2025년 데이터 기준) + DB 업데이트")
print("=" * 70)

final_scored = []
for c in companies:
    fin = get_fin(c['id'])
    fin_prev = get_fin(c['id'], (fin['fiscal_year'] - 1) if fin else None)

    if not fin: continue

    d = dict(fin)
    if fin_prev and fin_prev.get('revenue') and fin.get('revenue'):
        prev_r = safe(fin_prev['revenue'])
        cur_r  = safe(fin['revenue'])
        d['rev_growth'] = (cur_r - prev_r) / abs(prev_r) if prev_r else None

    order = c.get('display_order') or 99
    d['leader_bonus'] = max(0, 5 - order) if order <= 5 else 0

    score, grade, breakdown = calc_leading_score_v2(d)
    final_scored.append({**c, 'score': score, 'grade': grade, 'breakdown': breakdown})

# 산업별 순위 + display_order 업데이트
by_industry = defaultdict(list)
for c in final_scored:
    by_industry[c['industry']].append(c)

print(f"\n{'순위':4} {'등급':4} {'점수':>5} {'산업':8} {'티커':10} {'기업명':24} {'성장':>8} {'GPM':>7} {'FCF':>8}")
print("-" * 80)

all_sorted = sorted(final_scored, key=lambda x: x['score'], reverse=True)

for industry, comps in sorted(by_industry.items()):
    comps_sorted = sorted(comps, key=lambda x: x['score'], reverse=True)
    for rank, c in enumerate(comps_sorted, 1):
        cur.execute('UPDATE companies SET display_order=? WHERE id=?', (rank, c['id']))

conn.commit()

# 전체 TOP 30 출력
print("\n전체 통합 TOP 30:")
for i, c in enumerate(all_sorted[:30], 1):
    bd = c['breakdown']
    growth = bd.get('매출성장', '-')
    gpm    = bd.get('GPM', '-').replace('❌','')
    fcf    = bd.get('FCF마진', '-').replace('❌','')
    print(f"{i:4}위 [{c['grade']}] {c['score']:>3}점  {c['industry']:8} {c['ticker']:10} {c['name'][:22]:22} {growth:>8} {gpm:>7} {fcf:>8}")

# JSON 저장
rankings_json = {
    'version': 'v2',
    'generated_at': datetime.now().isoformat(),
    'scoring_logic': {
        'A_성장모멘텀(40점)': 'FCF- 기업은 성장점수 40% 감점',
        'B_마진해자(30점)': 'GPM+FCF마진+ROE',
        'C_재무안전성(20점)': '순이익률+부채비율',
        'D_규모리더십(10점)': '매출규모+섹터순위'
    },
    'grades': {'S': '85+', 'A': '70-84', 'B': '55-69', 'C': '40-54', 'D': '<40'},
    'rankings': [
        {'rank': i+1, 'ticker': c['ticker'], 'name': c['name'],
         'industry': c['industry'], 'score': c['score'], 'grade': c['grade'],
         'breakdown': c['breakdown']}
        for i, c in enumerate(all_sorted)
    ]
}

with open('InvestmentPortal/backend/leading_stock_rankings.json', 'w', encoding='utf-8') as f:
    json.dump(rankings_json, f, ensure_ascii=False, indent=2)

print(f"\n✅ DB display_order 업데이트 완료")
print(f"✅ leading_stock_rankings.json 저장 완료")
conn.close()
