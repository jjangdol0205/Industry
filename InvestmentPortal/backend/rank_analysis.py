"""
4개 산업 전체 기업 협업 분석 및 투자 순위 선별
- 병목(Bottleneck) / 해자(Moat) / 주가 성장가능성 종합 평가
- Gemini API 활용한 산업·기업 애널리스트 협업 시뮬레이션
"""
import sqlite3, sys, os, math
sys.stdout.reconfigure(encoding='utf-8')

try:
    import google.generativeai as genai
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if api_key:
        genai.configure(api_key=api_key)
        USE_AI = True
    else:
        USE_AI = False
except:
    USE_AI = False

DB = 'investment_portal.db'

def safe(v):
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except: return None

def fmt(v, unit='', decimals=1):
    v = safe(v)
    if v is None: return 'N/A'
    return f"{v:.{decimals}f}{unit}"

def gemini(prompt, fallback):
    if not USE_AI: return fallback
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        r = model.generate_content(prompt)
        return r.text.strip()
    except Exception as e:
        print(f"  Gemini 오류: {e}")
        return fallback

conn = sqlite3.connect(DB)
cur = conn.cursor()

# ── 전체 기업 + 프로파일 + 최근 재무 로드 ──────────────────
cur.execute('''
    SELECT c.id, c.name, c.ticker, ir.tag as industry,
        cp.current_price, cp.market_cap, cp.pe_ratio, cp.pb_ratio, cp.ev_ebitda,
        cp.revenue_growth, cp.gross_margin_ttm, cp.net_margin_ttm, cp.op_margin_ttm,
        cp.roe, cp.debt_to_equity, cp.current_ratio, cp.beta, cp.ev_sales,
        c.role_description, c.future_growth
    FROM companies c
    LEFT JOIN industry_reports ir ON c.industry_id = ir.id
    LEFT JOIN company_profiles cp ON c.id = cp.company_id
    ORDER BY ir.tag, c.ticker
''')
companies = cur.fetchall()
cols = ['id','name','ticker','industry','price','market_cap','pe','pb','ev_ebitda',
        'rev_growth','gm_ttm','nm_ttm','om_ttm','roe','d_e','curr_ratio','beta','ev_sales',
        'role','future']
companies = [dict(zip(cols, r)) for r in companies]
print(f"전체 분석 대상: {len(companies)}개 기업")

# ── 최근 연간 재무 로드 ──────────────────────────────────────
def get_latest_annual(cid):
    cur.execute('''
        SELECT revenue, cost_of_revenue, gross_profit, operating_income,
               net_income, ebitda, free_cash_flow, total_assets,
               cash_and_equivalents, total_debt, shareholders_equity,
               gross_margin, op_margin, roe, roa
        FROM financial_data
        WHERE company_id=? AND period_type='annual'
        ORDER BY date DESC LIMIT 1
    ''', (cid,))
    r = cur.fetchone()
    if not r: return {}
    keys = ['revenue','cogs','gp','op_income','net_income','ebitda','fcf',
            'total_assets','cash','debt','equity','gm','om','roe','roa']
    return dict(zip(keys, r))

# ── Quant 스코어링 ────────────────────────────────────────────
def calc_quant(c, fin):
    score = 50
    reasons = []

    # 1. 수익성 (25점)
    gm = safe(c.get('gm_ttm')) or safe(fin.get('gm'))
    nm = safe(c.get('nm_ttm')) or safe(fin.get('nm'))
    om = safe(c.get('om_ttm')) or safe(fin.get('om'))

    if gm is not None:
        if gm > 0.6:   score += 15; reasons.append(f"✅ 초고마진 GPM {gm*100:.0f}%")
        elif gm > 0.4: score += 10; reasons.append(f"✅ 고마진 GPM {gm*100:.0f}%")
        elif gm > 0.2: score += 5;  reasons.append(f"🟡 중간마진 GPM {gm*100:.0f}%")
        else:          score -= 5;  reasons.append(f"⚠️ 저마진 GPM {gm*100:.0f}%")
    if nm is not None:
        if nm > 0.2:   score += 10; reasons.append(f"✅ 고순이익률 {nm*100:.0f}%")
        elif nm > 0.1: score += 6;  reasons.append(f"✅ 적정 순이익률 {nm*100:.0f}%")
        elif nm > 0:   score += 2
        else:          score -= 10; reasons.append(f"🔴 적자 {nm*100:.0f}%")

    # 2. 성장성 (25점)
    rg = safe(c.get('rev_growth'))
    if rg is not None:
        if rg > 0.5:   score += 20; reasons.append(f"🚀 초고성장 {rg*100:.0f}%")
        elif rg > 0.25: score += 15; reasons.append(f"✅ 고성장 {rg*100:.0f}%")
        elif rg > 0.1: score += 8;  reasons.append(f"✅ 성장 {rg*100:.0f}%")
        elif rg > 0:   score += 3
        else:          score -= 10; reasons.append(f"🔴 역성장 {rg*100:.0f}%")

    # 3. 밸류에이션 (20점)
    pe = safe(c.get('pe'))
    ev_sales = safe(c.get('ev_sales'))
    if pe is not None and pe > 0:
        if pe < 15:    score += 15; reasons.append(f"✅ 저평가 PER {pe:.0f}x")
        elif pe < 30:  score += 8;  reasons.append(f"🟡 적정 PER {pe:.0f}x")
        elif pe < 60:  score += 3
        else:          score -= 5;  reasons.append(f"⚠️ 고평가 PER {pe:.0f}x")
    elif ev_sales is not None and ev_sales > 0:
        if ev_sales < 3:   score += 10; reasons.append(f"✅ 저EV/Sales {ev_sales:.1f}x")
        elif ev_sales < 8: score += 4
        else:              score -= 3

    # 4. 재무건전성 (15점)
    roe = safe(c.get('roe')) or safe(fin.get('roe'))
    de  = safe(c.get('d_e'))
    if roe is not None:
        if roe > 0.2:  score += 8;  reasons.append(f"✅ ROE {roe*100:.0f}%")
        elif roe > 0.1: score += 4
        elif roe < 0:  score -= 8;  reasons.append(f"🔴 마이너스 ROE")
    if de is not None:
        if de < 50:    score += 7;  reasons.append(f"✅ 낮은 부채비율")
        elif de < 150: score += 3
        else:          score -= 7;  reasons.append(f"⚠️ 고부채")

    # 5. FCF (15점)
    fcf = safe(fin.get('fcf'))
    rev = safe(fin.get('revenue'))
    if fcf is not None and rev and rev > 0:
        fcf_margin = fcf / rev
        if fcf_margin > 0.2:   score += 15; reasons.append(f"✅ FCF마진 {fcf_margin*100:.0f}%")
        elif fcf_margin > 0.1: score += 8
        elif fcf_margin > 0:   score += 3
        else:                  score -= 5;  reasons.append(f"⚠️ 마이너스FCF")

    score = max(0, min(100, score))
    if score >= 75:   grade = "STRONG BUY ⭐⭐"
    elif score >= 60: grade = "BUY ⭐"
    elif score >= 45: grade = "HOLD 🟡"
    elif score >= 30: grade = "WATCH ⚠️"
    else:             grade = "AVOID 🔴"
    return score, grade, reasons

# ── 병목·해자·성장 스코어 ────────────────────────────────────
def calc_moat_score(c, fin):
    """해자(경쟁 우위) 스코어"""
    score = 0
    moats = []
    gm = safe(c.get('gm_ttm')) or safe(fin.get('gm'))
    rg = safe(c.get('rev_growth'))
    roe = safe(c.get('roe')) or safe(fin.get('roe'))

    # 높은 마진 = 가격 결정력 있음
    if gm and gm > 0.5: score += 30; moats.append("가격결정력(高마진)")
    elif gm and gm > 0.35: score += 15; moats.append("적정 가격결정력")

    # 지속 성장 = 네트워크 효과 또는 전환비용 높음
    if rg and rg > 0.2: score += 20; moats.append("지속 고성장")
    elif rg and rg > 0.1: score += 10

    # 높은 ROE = 자본 효율성 (진짜 해자)
    if roe and roe > 0.25: score += 30; moats.append("자본효율성(高ROE)")
    elif roe and roe > 0.15: score += 15

    # 낮은 PE + 성장 = 가격매력
    pe = safe(c.get('pe'))
    if pe and 0 < pe < 25 and rg and rg > 0.1: score += 20; moats.append("저평가성장주")

    return min(100, score), moats

def calc_bottleneck_score(c, fin):
    """밸류체인 병목 위치 스코어"""
    score = 0
    reasons = []
    role = (c.get('role') or '').lower()

    # 역할 설명에서 병목 키워드 탐지
    bottleneck_keywords = {
        'lidar': 30, 'sensor': 20, 'chip': 25, 'semiconductor': 25,
        'platform': 20, 'license': 30, 'ip ': 35, 'standard': 20,
        '독점': 35, '1위': 25, 'largest': 25, 'leading': 15,
        'usdc': 30, 'custody': 25, 'stablecoin': 30,
        'launch': 20, 'rocket': 20, 'satellite': 15,
        '핵심': 20, '필수': 25, 'critical': 25,
    }
    for kw, pts in bottleneck_keywords.items():
        if kw in role:
            score += pts
            reasons.append(f"[{kw}] 포지션")
            if score >= 60: break

    # 시총 대비 높은 매출 = 실질적 인프라 역할
    rev = safe(fin.get('revenue'))
    mc = safe(c.get('market_cap'))
    if rev and mc and mc > 0:
        ps = mc / rev
        if ps < 2: score += 15; reasons.append("저PS(인프라적가치)")
        elif ps < 5: score += 8

    return min(100, score), reasons

def calc_growth_potential(c, fin):
    """현재 밸류에이션 대비 주가 성장 잠재력"""
    score = 0
    reasons = []

    rg = safe(c.get('rev_growth'))
    pe = safe(c.get('pe'))
    ev_sales = safe(c.get('ev_sales'))
    gm = safe(c.get('gm_ttm')) or safe(fin.get('gm'))

    # 고성장 + 합리적 밸류에이션 = 최고의 조합
    if rg and rg > 0.3:
        if ev_sales and ev_sales < 10: score += 40; reasons.append("고성장+적정밸류에이션")
        elif ev_sales and ev_sales < 20: score += 25; reasons.append("고성장(밸류에이션 주의)")
        else: score += 10

    # 흑자전환 임박 기업
    nm = safe(c.get('nm_ttm'))
    if nm is not None and -0.3 < nm < 0 and rg and rg > 0.2:
        score += 25; reasons.append("흑자전환 임박")
    elif nm and nm > 0: score += 10

    # 저PER + 성장
    if pe and 5 < pe < 20 and rg and rg > 0.1:
        score += 20; reasons.append("저PER+성장 (안전한 업사이드)")

    # 마진 개선 기대
    if gm and gm > 0.4 and nm and nm < gm * 0.3:
        score += 15; reasons.append("마진 개선 여지")

    return min(100, score), reasons

# ── 전체 기업 분석 실행 ──────────────────────────────────────
print("\n=== 전체 기업 분석 시작 ===")
analyzed = []
for c in companies:
    fin = get_latest_annual(c['id'])
    q_score, q_grade, q_reasons = calc_quant(c, fin)
    moat_score, moat_reasons = calc_moat_score(c, fin)
    bottle_score, bottle_reasons = calc_bottleneck_score(c, fin)
    growth_score, growth_reasons = calc_growth_potential(c, fin)

    # 종합 점수 (Quant 40% + Moat 25% + Bottleneck 15% + Growth 20%)
    total = q_score * 0.40 + moat_score * 0.25 + bottle_score * 0.15 + growth_score * 0.20

    analyzed.append({
        **c,
        'fin': fin,
        'q_score': q_score,
        'q_grade': q_grade,
        'q_reasons': q_reasons,
        'moat_score': moat_score,
        'moat_reasons': moat_reasons,
        'bottle_score': bottle_score,
        'bottle_reasons': bottle_reasons,
        'growth_score': growth_score,
        'growth_reasons': growth_reasons,
        'total_score': total,
    })

# 종합 순위 정렬
analyzed.sort(key=lambda x: x['total_score'], reverse=True)

# ── Gemini 협업 분석 ─────────────────────────────────────────
print("\n=== Gemini 산업·기업 애널리스트 협업 분석 시작 ===")

# 산업별 그룹핑
from collections import defaultdict
by_industry = defaultdict(list)
for c in analyzed:
    by_industry[c['industry']].append(c)

industry_reports = {}
for ind, comps in by_industry.items():
    print(f"\n[{ind}] 산업 분석 중... ({len(comps)}개 기업)")

    # 상위 8개 기업 데이터 정리
    top_comps = comps[:8]
    comp_summary = "\n".join([
        f"  {i+1}. {c['ticker']}({c['name']}): "
        f"매출성장{fmt(c['rev_growth'],unit='%',decimals=0) if c['rev_growth'] else 'N/A'} | "
        f"GPM {fmt(c['gm_ttm'],unit='%',decimals=0) if c['gm_ttm'] else 'N/A'} | "
        f"PER {fmt(c['pe'],unit='x',decimals=0) if c['pe'] and c['pe'] > 0 else 'N/A'} | "
        f"Quant {c['q_score']}점({c['q_grade']}) | 해자{c['moat_score']}점 | 성장잠재{c['growth_score']}점"
        for i, c in enumerate(top_comps)
    ])

    prompt = f"""당신은 {ind} 산업 수석 애널리스트입니다. 아래 기업들을 분석하여 투자 보고서를 한국어로 작성하세요.

[{ind} 산업 내 기업 현황]
{comp_summary}

다음을 분석하세요:
1. **산업 병목(Bottleneck)**: 이 산업에서 대체불가한 핵심 인프라를 장악한 기업 (최대 3개)
2. **경쟁 해자(Moat)**: 지속 가능한 경쟁우위를 보유한 기업 (높은 마진, 전환비용, 네트워크 효과)
3. **성장 잠재 TOP 3**: 현재 주가 대비 향후 12-24개월 상승 가능성 높은 기업 선정 근거

형식: 마크다운, 구체적 수치 인용 필수, 3~4문단"""

    fallback = f"""## {ind} 산업 분석
**병목기업**: 상위 정량점수 기업이 산업 내 핵심 인프라 포지션 장악
**해자기업**: 고마진·고ROE 기업이 지속 가능한 경쟁우위 보유
**성장TOP3**: 고성장+적정밸류에이션 조합의 기업 우선 추천"""

    ind_report = gemini(prompt, fallback)
    industry_reports[ind] = ind_report
    print(f"  완료")

# ── 종합 순위 보고서 생성 ─────────────────────────────────────
print("\n=== 종합 투자 순위 보고서 생성 ===")

top30_summary = "\n".join([
    f"  {i+1:2}. [{c['industry']:5}] {c['ticker']:6} {c['name'][:20]:20} "
    f"종합{c['total_score']:.0f}점 | Q:{c['q_score']}점 | 해자:{c['moat_score']}점 | 성장:{c['growth_score']}점 | {c['q_grade']}"
    for i, c in enumerate(analyzed[:30])
])

ind_summaries = "\n\n".join([f"## {ind}\n{rep}" for ind, rep in industry_reports.items()])

prompt_final = f"""당신은 수석 투자 오케스트레이터입니다. 4개 산업 전체 기업에 대한 종합 투자 순위 최종 보고서를 작성하세요.

[종합 점수 TOP 30]
{top30_summary}

[산업별 분석]
{ind_summaries[:3000]}

다음 형식으로 작성하세요:

# 🏆 4개 산업 통합 투자 순위 — 병목·해자·성장가능성 종합

## 핵심 인사이트 (3줄)

## 📊 투자 등급별 분류

### ⭐⭐ STRONG BUY (즉시 매수)
(상위 5개, 각각: 종목명, 핵심 이유 2줄, 목표 주가 근거)

### ⭐ BUY (매수 권고)  
(6~15위, 각각: 종목명, 핵심 이유 1줄)

### 🟡 HOLD / WATCH (관망)
(나머지 주목할 기업들)

## 🔍 산업별 병목 기업 (대체불가 포지션)

## 🛡️ 해자(Moat) 기업 TOP 5

## 🚀 단기(12개월) 고성장 가능성 TOP 5

## ⚠️ 리스크 주의 기업"""

fallback_final = f"""# 🏆 4개 산업 통합 투자 순위\n\n{top30_summary}"""

final_report = gemini(prompt_final, fallback_final)

# ── 결과 출력 및 저장 ─────────────────────────────────────────
output_lines = [final_report, "\n\n---\n\n## 📋 전체 기업 정량 데이터\n"]
output_lines.append(f"{'순위':>4} {'산업':6} {'티커':6} {'기업명':22} {'종합':>5} {'Quant':>5} {'해자':>4} {'병목':>4} {'성장':>4} {'등급'}")
output_lines.append("-" * 95)
for i, c in enumerate(analyzed):
    output_lines.append(
        f"{i+1:>4} {c['industry']:6} {c['ticker']:6} {c['name'][:22]:22} "
        f"{c['total_score']:>5.1f} {c['q_score']:>5} {c['moat_score']:>4} "
        f"{c['bottle_score']:>4} {c['growth_score']:>4} {c['q_grade']}"
    )

report_text = "\n".join(output_lines)

# 파일 저장
with open('investment_ranking_report.md', 'w', encoding='utf-8') as f:
    f.write(report_text)

print("\n=== 보고서 저장 완료: investment_ranking_report.md ===")
print(f"\nTOP 10 기업:")
for i, c in enumerate(analyzed[:10]):
    print(f"  {i+1:2}. [{c['industry']:5}] {c['ticker']:6} {c['name'][:20]} — 종합 {c['total_score']:.0f}점 {c['q_grade']}")

conn.close()
