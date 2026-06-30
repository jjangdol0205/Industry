"""
주도주 투자법 기반 신규 순위 산정 + 백테스트
==============================================
CAN SLIM + 추세추종 원칙 적용

[백테스트 로직]
- 2022년 데이터로 점수 산정 → 2022→2023 매출/이익 성과 추적
- 2023년 데이터로 점수 산정 → 2023→2024 매출/이익 성과 추적
- 고점수 그룹 vs 저점수 그룹의 실제 성과 비교
"""

import sqlite3, sys, math, json
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = 'InvestmentPortal/backend/investment_portal.db'

def safe(v, default=None):
    try:
        f = float(v)
        return default if (math.isnan(f) or math.isinf(f)) else f
    except:
        return default

# ─────────────────────────────────────────────────────
# 신규 주도주 스코어링 함수 (100점 만점)
# ─────────────────────────────────────────────────────
def calc_leading_score(fin_data, profile=None):
    """
    주도주 투자법 점수 산정
    
    [점수 구조]
    A. 성장 모멘텀  (40점) ← 주도주의 핵심
    B. 마진/해자    (30점) ← 경제적 해자
    C. 재무 안전성  (20점) ← 지속 가능성
    D. 산업 리더십  (10점) ← 섹터 내 1등
    
    총점 → 등급: S(85+), A(70~84), B(55~69), C(40~54), D(40미만)
    """
    score = 0
    breakdown = {}

    rev    = safe(fin_data.get('revenue'))
    gp     = safe(fin_data.get('gross_profit'))
    op_inc = safe(fin_data.get('operating_income'))
    net    = safe(fin_data.get('net_income'))
    fcf    = safe(fin_data.get('free_cash_flow'))
    gm     = safe(fin_data.get('gross_margin'))
    om     = safe(fin_data.get('op_margin'))
    nm     = safe(fin_data.get('net_margin'))
    fcfm   = safe(fin_data.get('fcf_margin'))
    roe    = safe(fin_data.get('roe'))
    roa    = safe(fin_data.get('roa'))
    de     = safe(fin_data.get('debt_to_equity_ratio'))
    cr     = safe(fin_data.get('current_ratio'))
    
    # 전년도 대비 성장률 계산용
    rev_prev = safe(fin_data.get('revenue_prev'))
    op_prev  = safe(fin_data.get('op_income_prev'))
    
    # ── A. 성장 모멘텀 (40점) ─────────────────────────────
    a_score = 0
    
    # A1. 매출 성장률 (20점) - 주도주의 핵심
    if rev and rev_prev and rev_prev > 0:
        rev_growth = (rev - rev_prev) / abs(rev_prev)
        if rev_growth >= 0.50:    a_score += 20  # 50%+ 초고성장 (주도주)
        elif rev_growth >= 0.25:  a_score += 16  # 25%+ 고성장
        elif rev_growth >= 0.15:  a_score += 12  # 15%+ 양호
        elif rev_growth >= 0.05:  a_score += 7   # 5%+ 완만성장
        elif rev_growth >= 0:     a_score += 3   # 보합
        else:                     a_score += 0   # 역성장 = 주도주 자격없음
        breakdown['매출성장'] = f"{rev_growth*100:.1f}%"
    else:
        a_score += 5  # 성장률 데이터 없을 때 중립
        breakdown['매출성장'] = 'N/A'
    
    # A2. 영업이익 성장률 (12점)
    if op_inc and op_prev and op_prev > 0 and op_inc > 0:
        op_growth = (op_inc - op_prev) / abs(op_prev)
        if op_growth >= 0.50:    a_score += 12
        elif op_growth >= 0.25:  a_score += 9
        elif op_growth >= 0.10:  a_score += 6
        elif op_growth >= 0:     a_score += 3
        breakdown['영업이익성장'] = f"{op_growth*100:.1f}%"
    elif op_inc and rev and rev > 0:
        # 성장률 없으면 영업이익률로 대체 판단
        if op_inc / rev >= 0.20:  a_score += 8
        elif op_inc / rev >= 0.10: a_score += 5
        elif op_inc > 0:           a_score += 2
    
    # A3. 규모 (성장을 뒷받침하는 매출 규모) (8점)
    if rev:
        if rev >= 100e9:   a_score += 8   # 100B+ 메가캡
        elif rev >= 10e9:  a_score += 6   # 10B+
        elif rev >= 1e9:   a_score += 4   # 1B+
        elif rev >= 0.1e9: a_score += 2   # 100M+
        else:              a_score += 0   # 초소형
        breakdown['매출규모'] = f"${rev/1e9:.1f}B"
    
    score += min(40, a_score)
    breakdown['A_성장모멘텀'] = min(40, a_score)

    # ── B. 마진/해자 (30점) ──────────────────────────────
    b_score = 0
    
    # B1. 매출총이익률 GPM (15점) - 경제적 해자의 핵심 지표
    gm_pct = gm * 100 if gm and gm <= 1 else gm
    if gm_pct:
        if gm_pct >= 70:    b_score += 15  # 소프트웨어/반도체 수준 (NVDA 71%)
        elif gm_pct >= 55:  b_score += 12  # 구조적 우위 (GOOGL 60%)
        elif gm_pct >= 40:  b_score += 9   # 양호
        elif gm_pct >= 25:  b_score += 5   # 제조업 수준
        elif gm_pct >= 10:  b_score += 2   # 저마진
        else:               b_score += 0   # 수익성 없음
        breakdown['GPM'] = f"{gm_pct:.1f}%"
    
    # B2. FCF 마진 (10점) - 진짜 현금창출력
    fcfm_pct = fcfm * 100 if fcfm and abs(fcfm) <= 1 else fcfm
    if fcfm_pct:
        if fcfm_pct >= 25:    b_score += 10
        elif fcfm_pct >= 15:  b_score += 8
        elif fcfm_pct >= 5:   b_score += 5
        elif fcfm_pct >= 0:   b_score += 2
        else:                 b_score += 0  # 마이너스 FCF = 해자 없음
        breakdown['FCF마진'] = f"{fcfm_pct:.1f}%"
    elif fcf and rev and rev > 0:
        calc_fcfm = fcf / rev * 100
        if calc_fcfm >= 20:   b_score += 9
        elif calc_fcfm >= 10: b_score += 6
        elif calc_fcfm >= 0:  b_score += 3
        breakdown['FCF마진(역산)'] = f"{calc_fcfm:.1f}%"
    
    # B3. ROE (5점) - 자본 효율성
    roe_pct = roe * 100 if roe and abs(roe) <= 1 else roe
    if roe_pct:
        if roe_pct >= 30:    b_score += 5
        elif roe_pct >= 20:  b_score += 4
        elif roe_pct >= 10:  b_score += 2
        elif roe_pct < 0:    b_score += 0
        breakdown['ROE'] = f"{roe_pct:.1f}%"
    
    score += min(30, b_score)
    breakdown['B_마진해자'] = min(30, b_score)

    # ── C. 재무 안전성 (20점) ─────────────────────────────
    c_score = 0
    
    # C1. 수익성 지속 가능성 (10점) - 적자 여부
    nm_pct = nm * 100 if nm and abs(nm) <= 1 else nm
    if nm_pct:
        if nm_pct >= 20:    c_score += 10  # 고수익
        elif nm_pct >= 10:  c_score += 8
        elif nm_pct >= 5:   c_score += 6
        elif nm_pct >= 0:   c_score += 3
        else:
            # 적자 기업: 주도주 투자법에서 적자는 큰 감점
            if nm_pct >= -10:  c_score += 0
            elif nm_pct >= -30: c_score -= 5
            else:               c_score -= 10
        breakdown['순이익률'] = f"{nm_pct:.1f}%"
    
    # C2. 부채 안전성 (10점)
    de_pct = de * 100 if de and abs(de) <= 1 else de
    if de_pct is not None:
        if de_pct <= 0:      c_score += 10  # 무부채
        elif de_pct <= 50:   c_score += 8   # 매우 건전
        elif de_pct <= 100:  c_score += 6
        elif de_pct <= 200:  c_score += 3
        else:                c_score += 0   # 과다부채
        breakdown['부채비율'] = f"{de_pct:.1f}%"
    
    score += max(0, min(20, c_score))
    breakdown['C_재무안전성'] = max(0, min(20, c_score))

    # ── D. 산업 리더십 (10점) ─────────────────────────────
    # 섹터 내 순위는 외부에서 주입 (display_order 기반)
    leader_score = safe(fin_data.get('leader_bonus'), 5)
    score += leader_score
    breakdown['D_산업리더십'] = leader_score

    final = max(0, min(100, score))
    
    # 등급 산정
    if final >= 85:   grade = 'S'
    elif final >= 70: grade = 'A'
    elif final >= 55: grade = 'B'
    elif final >= 40: grade = 'C'
    else:             grade = 'D'
    
    return final, grade, breakdown


# ─────────────────────────────────────────────────────
# 백테스트: 2022년 점수 → 2023년 성과, 2023년 점수 → 2024년 성과
# ─────────────────────────────────────────────────────
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# 전체 기업 목록
cur.execute('''
    SELECT c.id, c.name, c.ticker, ir.tag as industry, c.display_order
    FROM companies c
    LEFT JOIN industry_reports ir ON c.industry_id = ir.id
''')
companies = [dict(zip(['id','name','ticker','industry','display_order'], r)) for r in cur.fetchall()]

def get_fin_year(company_id, year):
    """특정 연도 데이터 가져오기"""
    cur.execute('''
        SELECT revenue, gross_profit, operating_income, net_income,
               free_cash_flow, gross_margin, op_margin, net_margin,
               fcf_margin, roe, roa, debt_to_equity_ratio, current_ratio,
               total_assets, shareholders_equity
        FROM financial_data
        WHERE company_id=? AND period_type='annual'
          AND substr(date,1,4) = ?
        ORDER BY date DESC LIMIT 1
    ''', (company_id, str(year)))
    r = cur.fetchone()
    if not r: return None
    cols = ['revenue','gross_profit','operating_income','net_income',
            'free_cash_flow','gross_margin','op_margin','net_margin',
            'fcf_margin','roe','roa','debt_to_equity_ratio','current_ratio',
            'total_assets','shareholders_equity']
    return dict(zip(cols, r))

# ─────────────────────────────────────────────────────
# 백테스트 실행
# ─────────────────────────────────────────────────────
print("=" * 70)
print("📊 백테스트: 주도주 스코어링 신뢰도 검증")
print("=" * 70)

backtest_results = {}

for test_year, result_year in [(2022, 2023), (2023, 2024), (2024, 2025)]:
    print(f"\n[{test_year}년 점수 → {result_year}년 성과 추적]")
    
    scored = []
    for c in companies:
        fin_base = get_fin_year(c['id'], test_year)
        fin_next = get_fin_year(c['id'], result_year)
        fin_prev = get_fin_year(c['id'], test_year - 1)
        
        if not fin_base or not fin_next:
            continue
        
        # 전년 대비 성장률 추가
        fin_input = dict(fin_base)
        if fin_prev:
            fin_input['revenue_prev'] = fin_prev.get('revenue')
            fin_input['op_income_prev'] = fin_prev.get('operating_income')
        
        # 산업 리더십 보너스 (display_order 기반)
        order = c.get('display_order') or 99
        leader_bonus = max(0, 10 - order) if order <= 10 else 0
        fin_input['leader_bonus'] = leader_bonus
        
        score, grade, breakdown = calc_leading_score(fin_input)
        
        # 다음 해 성과: 매출 성장률로 측정
        base_rev = safe(fin_base.get('revenue'))
        next_rev = safe(fin_next.get('revenue'))
        next_op  = safe(fin_next.get('operating_income'))
        base_op  = safe(fin_base.get('operating_income'))
        
        actual_growth = None
        if base_rev and next_rev and base_rev > 0:
            actual_growth = (next_rev - base_rev) / base_rev * 100
        
        scored.append({
            **c,
            'score': score,
            'grade': grade,
            'actual_growth': actual_growth,
            'base_rev': base_rev,
            'next_rev': next_rev,
        })
    
    # 점수 그룹별 평균 성과 비교
    groups = {'S(85+)': [], 'A(70-84)': [], 'B(55-69)': [], 'C(40-54)': [], 'D(<40)': []}
    for c in scored:
        s = c['score']
        if s >= 85:   groups['S(85+)'].append(c)
        elif s >= 70: groups['A(70-84)'].append(c)
        elif s >= 55: groups['B(55-69)'].append(c)
        elif s >= 40: groups['C(40-54)'].append(c)
        else:         groups['D(<40)'].append(c)
    
    print(f"  {'등급':10} {'기업수':>5} {'평균성장':>10} {'성장기업비율':>12}")
    print(f"  {'-'*42}")
    
    grade_performance = {}
    for grade_name, comps in groups.items():
        growths = [c['actual_growth'] for c in comps if c['actual_growth'] is not None]
        if growths:
            avg = sum(growths) / len(growths)
            pos_ratio = sum(1 for g in growths if g > 10) / len(growths) * 100
            print(f"  {grade_name:10} {len(comps):>5}개   {avg:>+9.1f}%  {pos_ratio:>10.0f}%")
            grade_performance[grade_name] = avg
        else:
            print(f"  {grade_name:10} {len(comps):>5}개   데이터부족")
    
    backtest_results[f'{test_year}->{result_year}'] = {
        'scored': scored,
        'grade_performance': grade_performance
    }

# ─────────────────────────────────────────────────────
# 2025년 데이터 기준 최종 순위 산정 (실제 적용)
# ─────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("🏆 2025년 데이터 기준 주도주 최종 순위")
print("=" * 70)

final_scored = []
for c in companies:
    fin_2025 = get_fin_year(c['id'], 2025)
    fin_2024 = get_fin_year(c['id'], 2024)
    
    if not fin_2025:
        fin_2025 = get_fin_year(c['id'], 2024)
        fin_2024 = get_fin_year(c['id'], 2023)
    
    if not fin_2025:
        continue
    
    fin_input = dict(fin_2025)
    if fin_2024:
        fin_input['revenue_prev'] = fin_2024.get('revenue')
        fin_input['op_income_prev'] = fin_2024.get('operating_income')
    
    order = c.get('display_order') or 99
    fin_input['leader_bonus'] = max(0, 10 - order) if order <= 10 else 0
    
    score, grade, breakdown = calc_leading_score(fin_input)
    
    final_scored.append({
        **c,
        'score': score,
        'grade': grade,
        'breakdown': breakdown,
    })

# 산업별 정렬 & 출력
by_industry = defaultdict(list)
for c in final_scored:
    by_industry[c['industry']].append(c)

all_results = []
for industry in sorted(by_industry.keys()):
    comps = sorted(by_industry[industry], key=lambda x: x['score'], reverse=True)
    print(f"\n[{industry}]")
    print(f"  {'순위':4} {'등급':4} {'점수':>5} {'티커':8} {'기업명':25} {'성장':>8} {'GPM':>7} {'FCF마진':>8}")
    print(f"  {'-'*72}")
    for rank, c in enumerate(comps, 1):
        bd = c['breakdown']
        rev_g = bd.get('매출성장', '-')
        gpm   = bd.get('GPM', '-')
        fcfm  = bd.get('FCF마진', bd.get('FCF마진(역산)', '-'))
        print(f"  {rank:4}위 [{c['grade']}]  {c['score']:>3}점  {c['ticker']:8} {c['name'][:24]:25} {rev_g:>8} {gpm:>7} {fcfm:>8}")
        all_results.append({'rank_in_industry': rank, **c})

# 전체 통합 TOP 20
print("\n" + "=" * 70)
print("🌐 전체 통합 TOP 20 (주도주 최우선 투자 대상)")
print("=" * 70)
top20 = sorted(final_scored, key=lambda x: x['score'], reverse=True)[:20]
print(f"  {'순위':4} {'등급':4} {'점수':>5} {'산업':8} {'티커':8} {'기업명':25} {'성장':>8} {'GPM':>6}")
print(f"  {'-'*72}")
for i, c in enumerate(top20, 1):
    bd = c['breakdown']
    print(f"  {i:4}위 [{c['grade']}]  {c['score']:>3}점  {c['industry']:8} {c['ticker']:8} {c['name'][:24]:25} {bd.get('매출성장','-'):>8} {bd.get('GPM','-'):>6}")

# JSON 저장
output = {
    'generated_at': '2025-current',
    'backtest_summary': {
        k: v['grade_performance'] for k, v in backtest_results.items()
    },
    'final_rankings': [
        {
            'ticker': c['ticker'],
            'name': c['name'],
            'industry': c['industry'],
            'score': c['score'],
            'grade': c['grade'],
            'breakdown': c['breakdown'],
        }
        for c in sorted(final_scored, key=lambda x: x['score'], reverse=True)
    ]
}

with open('InvestmentPortal/backend/leading_stock_rankings.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n✅ 결과 저장: leading_stock_rankings.json")
conn.close()
