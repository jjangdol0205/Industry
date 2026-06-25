"""
4개 산업 신규 기업 대량 추가 스크립트
자율주행 5개 + 로봇 5개 + 우주 5개 + 코인 5개 = 20개
"""
import sqlite3, sys, yfinance as yf, math, pandas as pd, time
sys.stdout.reconfigure(encoding='utf-8')

DB = 'investment_portal.db'

def safe(v):
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except: return None

def get_val(df, col, *keys):
    for key in keys:
        try:
            if df is not None and not df.empty and key in df.index:
                v = safe(df.loc[key, col])
                if v is not None: return v
        except: pass
    return None

conn = sqlite3.connect(DB)
cur = conn.cursor()

# 산업 ID 조회
cur.execute("SELECT id, tag FROM industry_reports")
industry_map = {row[1]: row[0] for row in cur.fetchall()}
print("산업 ID:", industry_map)

# ── 신규 기업 정의 ──────────────────────────────────────────
NEW_COMPANIES = [
    # 자율주행
    {
        'ticker': 'AUR', 'name': 'Aurora Innovation', 'industry': '자율주행',
        'role': '자율주행 트럭 소프트웨어(Aurora Driver) 개발사. Paccar·Volvo와 파트너십으로 Class-8 대형 트럭 자율주행 상용화 선도.',
        'growth': '2025년 텍사스 상업 운행 개시로 수익 모델 전환. Aurora Horizon TaaS(Transport-as-a-Service) 구독 수익 본격화.'
    },
    {
        'ticker': 'LAZR', 'name': 'Luminar Technologies', 'industry': '자율주행',
        'role': 'IRIS+ LiDAR 센서 전문 제조사. Volvo, Mercedes-Benz, Nissan, Polestar에 OEM 공급. 자율주행의 핵심 눈(센서) 역할.',
        'growth': '자동차 OEM 양산 채택 가속. 2026년부터 볼보 EX90 대량 탑재로 매출 급증 기대. 범용 LiDAR 칩(Halo) 출시로 단가 혁신.'
    },
    {
        'ticker': 'PONY', 'name': 'Pony.ai', 'industry': '자율주행',
        'role': '중국·미국 동시 운영 로보택시 플랫폼. 도요타 전략 투자 유치. 베이징·광저우 상업 로보택시 면허 보유.',
        'growth': '2024년 나스닥 상장. 중국 로보택시 시장 규모 2030년 $50B 전망. 도요타 글로벌 플랫폼 공급 협약으로 확장성 확보.'
    },
    {
        'ticker': 'WRD', 'name': 'WeRide', 'industry': '자율주행',
        'role': '중국·중동·유럽 로보택시·자율주행 버스·화물트럭 솔루션. UAE 아부다비 첫 무인 로보택시 상업 운행 허가.',
        'growth': '중동·유럽 시장 진출로 지역 다변화. Bosch·Uber Freight 파트너십. 2025년 나스닥 상장.'
    },
    {
        'ticker': 'MOBILEYE', 'name': 'Mobileye Global', 'industry': '자율주행',
        'role': 'ADAS(첨단운전자보조) 칩·소프트웨어 세계 1위. EyeQ 칩 연간 3,000만개 이상 출하. ADAS 센서퓨전 알고리즘 업계 표준.',
        'growth': 'SuperVision(고속도로 자율주행) 확대. Zeekr·Smart·Nio에 채택. 2030년 레벨4 자율주행 상용화 시 최대 수혜.'
    },

    # 로봇
    {
        'ticker': 'ABB', 'name': 'ABB Ltd', 'industry': '로봇',
        'role': '세계 최대 산업용 로봇 제조사. 연간 수만 대 로봇팔 출하. 자동차·전자·물류 자동화 솔루션 글로벌 1위.',
        'growth': '전기차 배터리 조립·반도체 팹 자동화 수요 급증. AI 기반 협동로봇(UR) 보급 확대. 물류 자동화 투자 사이클 진입.'
    },
    {
        'ticker': 'HON', 'name': 'Honeywell International', 'industry': '로봇',
        'role': '산업 자동화·공정 제어·창고 로보틱스 종합 솔루션. Intelligrated 인수로 아마존·월마트 물류 자동화 핵심 공급사.',
        'growth': 'Honeywell Robotics 분사 및 독립 상장 검토. 항공우주·에너지 전환 자동화 시장 확대.'
    },
    {
        'ticker': 'EMR', 'name': 'Emerson Electric', 'industry': '로봇',
        'role': '공정 자동화·유량계·밸브·제어시스템 전문. 화학·석유·가스·식품 산업 자동화의 핵심 인프라.',
        'growth': 'AspenTech 인수로 AI 기반 공정 최적화 솔루션 강화. 에너지 전환(수소·LNG) 자동화 수요 급증.'
    },
    {
        'ticker': 'CEVA', 'name': 'CEVA Inc', 'industry': '로봇',
        'role': 'AI·DSP 반도체 IP 라이선싱. 로봇·드론·IoT·웨어러블의 AI 추론 칩 설계 핵심. Arm처럼 IP를 팔아 로열티 수익.',
        'growth': '엣지AI 로봇 수요로 라이선싱 매출 고성장. 센소리AI 인수로 AI IP 포트폴리오 강화. 로봇 뇌(AI칩) 라이선싱 독점적 위치.'
    },
    {
        'ticker': 'BRZE', 'name': 'Braze Inc', 'industry': '로봇',
        'role': '고객 데이터 플랫폼(CDP)이나 실제로는 자동화 로봇 SaaS — 재분류 필요. 대신 ACMR(AC M Research) 로 대체.',
        'growth': '대체'
    },

    # 우주
    {
        'ticker': 'ASTS', 'name': 'AST SpaceMobile', 'industry': '우주',
        'role': '스마트폰 직접 연결(Direct-to-Cell) 위성 브로드밴드. AT&T·Verizon·Rakuten·Vodafone과 파트너십. BlueBird 위성 배치 중.',
        'growth': '통신 사각지대 해소 TAM $1T. AT&T와 상업 서비스 개시. 2025년 BlueBird 배치 완료 시 전국 커버리지 달성.'
    },
    {
        'ticker': 'IRDM', 'name': 'Iridium Communications', 'industry': '우주',
        'role': '66개 LEO 위성으로 전 지구 위성 통신 서비스. 해운·항공·정부·국방 고객. 프리미엄 위성통신 수익 모델.',
        'growth': 'Iridium Certus 데이터 서비스 고성장. 항공 기내 와이파이·스마트폰 위성 통신 IoT 확대. 연간 $200M+ FCF 창출.'
    },
    {
        'ticker': 'GSAT', 'name': 'Globalstar', 'industry': '우주',
        'role': 'LEO 위성 통신. Apple iPhone 위성 SOS 기능 독점 파트너. Apple이 최대 주주(약 20% 지분 보유).',
        'growth': 'Apple 위성 통신 기능 확장(iOS 생태계 연동). 신규 위성 발사로 용량 확대. Apple 공식 파트너 위치의 가시성.'
    },
    {
        'ticker': 'SPIR', 'name': 'Spire Global', 'industry': '우주',
        'role': '100개+ LEO 위성으로 기상·해양·항공 데이터 수집·분석 SaaS. 기상청·항공사·보험사·해운사 데이터 구독.',
        'growth': '기후 변화로 정밀 기상 데이터 수요 폭증. NOAA 장기 계약 확보. 위성 데이터 구독 SaaS 비즈니스 마진 개선.'
    },
    {
        'ticker': 'BKSY', 'name': 'BlackSky Technology', 'industry': '우주',
        'role': '고해상도 위성 영상 + AI 분석 플랫폼. 미 국방부(NRO·NGA) 장기 계약. 실시간 지구관측 정보 제공.',
        'growth': '국방·정보기관 장기 계약 파이프라인 확대. AI 분석 자동화로 마진 개선. 우크라이나·대만 지정학적 긴장 수혜.'
    },

    # 코인
    {
        'ticker': 'BTDR', 'name': 'Bitdeer Technologies', 'industry': '코인',
        'role': '자체 채굴 칩(SEALMINER) 개발·제조 + 채굴 데이터센터 운영. 반도체 내재화로 채굴 원가 구조 혁신.',
        'growth': 'SEALMINER A2 칩 양산으로 칩 판매 수익 추가. AI 컴퓨팅 데이터센터 전환으로 수익원 다각화.'
    },
    {
        'ticker': 'APLD', 'name': 'Applied Digital', 'industry': '코인',
        'role': '고성능 컴퓨팅(HPC) 데이터센터. 암호화폐 채굴 → AI/HPC 워크로드로 전환 중. Nvidia H100 GPU 클러스터 운영.',
        'growth': 'AI 데이터센터 수요 급증 직접 수혜. 노스다코타 저렴한 전력 기반 마진 우위. NVIDIA·Macquarie 투자 유치.'
    },
    {
        'ticker': 'WULF', 'name': 'TeraWulf', 'industry': '코인',
        'role': '수력·원자력 100% 청정에너지 BTC 채굴. 뉴욕 Nautilus 원자력 발전소 연계 채굴. ESG 코인 채굴 선도.',
        'growth': '탄소중립 채굴로 ESG 기관 수요 대응. 원자력 전력 장기 고정 계약으로 채산성 안정. AI 컴퓨팅 용량 전환 옵션.'
    },
    {
        'ticker': 'IREN', 'name': 'Iris Energy', 'industry': '코인',
        'role': '캐나다·미국·호주 수력발전 연계 친환경 BTC 채굴. Exahash 규모 빠른 확장. AI 클라우드 컴퓨팅 전환 중.',
        'growth': 'AI GPU 클라우드(Nvidia H100) 사업부 고성장. 캐나다 저렴한 수력 전기로 채굴 마진 상위권.'
    },
    {
        'ticker': 'BTBT', 'name': 'Bit Digital', 'industry': '코인',
        'role': 'BTC 채굴 + ETH 스테이킹 + AI 클라우드 컴퓨팅 3분야 운영. 아이슬란드 데이터센터 기반.',
        'growth': 'ETH 스테이킹 수익 + AI 클라우드로 채굴 의존도 감소. 뉴욕 HPC 데이터센터 확장 계획.'
    },
]

# MOBILEYE는 이미 MBLY로 있으므로 제외, BRZE 제외하고 ACMR 추가
NEW_COMPANIES = [c for c in NEW_COMPANIES if c['ticker'] not in ('MOBILEYE', 'BRZE')]
# ACMR 추가
NEW_COMPANIES.append({
    'ticker': 'ACMR', 'name': 'ACM Research', 'industry': '로봇',
    'role': '반도체 세정 장비 전문. 중국 반도체 팹 자동화 핵심 공급사. WAFER CLEANING 장비 고성능화로 AI칩·로봇칩 제조 필수 장비.',
    'growth': '중국 반도체 내재화 정책 수혜. 3D NAND·HBM 생산 증설로 세정장비 수요 급증. 미국 수출 규제 반사이익.'
})

# 이미 있는 ticker 제외
cur.execute("SELECT ticker FROM companies")
existing_tickers = {r[0] for r in cur.fetchall()}
NEW_COMPANIES = [c for c in NEW_COMPANIES if c['ticker'] not in existing_tickers]
print(f"\n추가할 신규 기업: {len(NEW_COMPANIES)}개")
for c in NEW_COMPANIES:
    print(f"  [{c['industry']}] {c['ticker']} - {c['name']}")

# ── 기업 추가 함수 ──────────────────────────────────────────
def add_company(comp_info):
    ticker = comp_info['ticker']
    name = comp_info['name']
    industry_tag = comp_info['industry']
    industry_id = industry_map.get(industry_tag)
    if not industry_id:
        print(f"  [{ticker}] 산업 ID 없음: {industry_tag}")
        return None

    cur.execute(
        'INSERT INTO companies (name, ticker, industry_id, role_description, future_growth) VALUES (?,?,?,?,?)',
        (name, ticker, industry_id, comp_info['role'], comp_info['growth'])
    )
    cid = cur.lastrowid
    conn.commit()
    return cid

def fetch_financials(ticker, cid):
    """yfinance로 재무 데이터 수집 및 DB 저장"""
    t = yf.Ticker(ticker)
    info = t.info
    fin_a = t.financials
    fin_q = t.quarterly_financials
    bs_a  = t.balance_sheet
    bs_q  = t.quarterly_balance_sheet
    cf_a  = t.cashflow
    cf_q  = t.quarterly_cashflow

    inserted = 0
    for df_inc, df_bs, df_cf, ptype in [
        (fin_a, bs_a, cf_a, 'annual'),
        (fin_q, bs_q, cf_q, 'quarterly')
    ]:
        if df_inc is None or df_inc.empty: continue
        for col in df_inc.columns:
            d = pd.Timestamp(col).strftime('%Y-%m-%d')
            rev   = get_val(df_inc, col, 'Total Revenue', 'Revenue')
            cogs  = get_val(df_inc, col, 'Cost Of Revenue', 'Cost Of Goods Sold')
            gp    = get_val(df_inc, col, 'Gross Profit')
            opInc = get_val(df_inc, col, 'Operating Income', 'Ebit')
            netInc= get_val(df_inc, col, 'Net Income')
            ebitda= get_val(df_inc, col, 'EBITDA', 'Normalized EBITDA')
            eps   = get_val(df_inc, col, 'Diluted EPS', 'Basic EPS')

            if gp is None and rev and cogs: gp = rev - cogs
            if cogs is None and rev and gp: cogs = rev - gp
            gm = (gp/rev*100) if (gp and rev and rev > 0) else None
            om = (opInc/rev*100) if (opInc and rev and rev > 0) else None
            nm = (netInc/rev*100) if (netInc and rev and rev > 0) else None

            ta  = get_val(df_bs, col, 'Total Assets') if df_bs is not None and not df_bs.empty else None
            cash= get_val(df_bs, col, 'Cash And Cash Equivalents', 'Cash Cash Equivalents And Short Term Investments')
            debt= get_val(df_bs, col, 'Total Debt', 'Long Term Debt')
            eq  = get_val(df_bs, col, "Stockholders' Equity", 'Total Equity Gross Minority Interest')
            tl  = get_val(df_bs, col, 'Total Liabilities Net Minority Interest')
            ca  = get_val(df_bs, col, 'Current Assets', 'Total Current Assets')
            cl  = get_val(df_bs, col, 'Current Liabilities', 'Total Current Liabilities')

            ocf   = get_val(df_cf, col, 'Operating Cash Flow')
            capex = get_val(df_cf, col, 'Capital Expenditure')
            fcf   = (ocf + capex) if (ocf and capex) else ocf

            roe  = (netInc/eq*100)  if (netInc and eq and eq != 0) else None
            roa  = (netInc/ta*100)  if (netInc and ta and ta != 0) else None
            de   = (debt/eq*100)    if (debt and eq and eq != 0) else None
            cr   = (ca/cl)          if (ca and cl and cl != 0) else None
            nd   = (debt - cash)    if (debt and cash) else None
            fcfm = (fcf/rev*100)    if (fcf and rev and rev > 0) else None

            cur.execute('''
                INSERT OR REPLACE INTO financial_data
                (company_id, date, period_type,
                 revenue, cost_of_revenue, gross_profit, gross_margin,
                 operating_income, op_margin, ebitda, net_income, net_margin, eps,
                 total_assets, cash_and_equivalents, total_debt, total_liabilities,
                 shareholders_equity, net_debt, debt_to_equity_ratio, current_ratio,
                 operating_cash_flow, capital_expenditure, free_cash_flow,
                 roe, roa, fcf_margin)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ''', (cid, d, ptype,
                  rev, cogs, gp, gm, opInc, om, ebitda, netInc, nm, eps,
                  ta, cash, debt, tl, eq, nd, de, cr, ocf, capex, fcf,
                  roe, roa, fcfm))
            inserted += 1

    # company_profiles
    p = info
    cur.execute('''
        INSERT OR REPLACE INTO company_profiles
        (company_id, current_price, market_cap, pe_ratio, pb_ratio, ev_ebitda, ev_sales,
         beta, revenue_growth, gross_margin_ttm, net_margin_ttm, op_margin_ttm,
         eps_growth, roe, roa, debt_to_equity, current_ratio, dividend_yield, description)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (
        cid,
        safe(p.get('currentPrice')),
        safe(p.get('marketCap')),
        safe(p.get('trailingPE') or p.get('forwardPE')),
        safe(p.get('priceToBook')),
        safe(p.get('enterpriseToEbitda')),
        safe(p.get('enterpriseToRevenue')),
        safe(p.get('beta')),
        safe(p.get('revenueGrowth')),
        safe(p.get('grossMargins')),
        safe(p.get('profitMargins')),
        safe(p.get('operatingMargins')),
        safe(p.get('earningsGrowth')),
        safe(p.get('returnOnEquity')),
        safe(p.get('returnOnAssets')),
        safe(p.get('debtToEquity')),
        safe(p.get('currentRatio')),
        safe(p.get('dividendYield')),
        (p.get('longBusinessSummary', '') or '')[:2000]
    ))
    conn.commit()
    return inserted

# ── 실행 ──────────────────────────────────────────────────
print("\n=== 기업 추가 시작 ===")
results = []
for comp in NEW_COMPANIES:
    ticker = comp['ticker']
    print(f"\n[{ticker}] {comp['name']} 추가 중...")
    # 상장 여부 확인
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period='5d')
        if len(hist) == 0:
            print(f"  ⚠️ 가격 데이터 없음 (상장폐지 또는 OTC) - 스킵")
            continue
        price = hist['Close'].iloc[-1]
        cid = add_company(comp)
        if cid is None: continue
        n = fetch_financials(ticker, cid)
        print(f"  ✅ 추가 완료 (id={cid}, 현재가=${price:.2f}, 재무레코드={n}개)")
        results.append({'ticker': ticker, 'name': comp['name'], 'industry': comp['industry'], 'cid': cid, 'price': price})
        time.sleep(1)  # API 속도 제한
    except Exception as e:
        print(f"  ❌ 오류: {e}")

print(f"\n=== 완료: {len(results)}개 기업 추가 ===")
for r in results:
    print(f"  [{r['industry']}] {r['ticker']} {r['name']} (id={r['cid']}, ${r['price']:.2f})")

conn.close()
