"""
나스닥/S&P500 핵심 독점 종목을 유니버스에 추가하고 4단계 투자원칙 기반으로 분류
- 인코딩 수정 버전 (이모지 제거)
"""
import sqlite3
import yfinance as yf
from datetime import datetime
import sys

DB_PATH = 'investment_portal.db'

# 4단계 투자원칙 기반 나스닥/S&P500 핵심 독점 종목 목록
NEW_STOCKS = [
    # Core 등급 (S&P500/나스닥 최강 독점)
    {
        "name": "Microsoft",
        "ticker": "MSFT",
        "portfolio_tier": "Core",
        "industry_id": 5,
        "role_description": "글로벌 클라우드(Azure) 2위, Office 365 독점 생산성 플랫폼, GitHub Copilot AI 코딩 도구 1위. 엔터프라이즈 락인(Switching Cost) 최강 수준.",
        "future_growth": "AI 통합 Azure 성장 YoY +33%, Copilot 기업 구독 확대, 연 FCF $70B+ 창출 체질",
        "principle_reason": "제2원칙: Office/Azure/Teams/GitHub 생태계 락인 독점. 제3원칙: OPM 45%+, ROE 35%+. Core 편입.",
    },
    {
        "name": "Alphabet (Google)",
        "ticker": "GOOGL",
        "portfolio_tier": "Core",
        "industry_id": 5,
        "role_description": "검색 광고 90%+ 독점, YouTube 2위 동영상 플랫폼, Google Cloud AI 3위 급성장. Android 생태계 80%+ 점유.",
        "future_growth": "Gemini AI 통합 검색 광고 강화, Google Cloud YoY +28% 성장, Waymo 자율주행 독점",
        "principle_reason": "제2원칙: 검색 독점 90%+ 네트워크 효과. 제3원칙: OPM 32%+, FCF 마진 20%+. Core 편입.",
    },
    {
        "name": "Apple",
        "ticker": "AAPL",
        "portfolio_tier": "Core",
        "industry_id": 8,
        "role_description": "스마트폰 프리미엄 65%+ 점유(iOS), App Store 수수료 30% 독점 플랫폼. 애플 실리콘 온디바이스 AI 하드웨어.",
        "future_growth": "Apple Intelligence(온디바이스 AI) 탑재 아이폰 교체 사이클, 서비스 매출 YoY +15%+ 고마진 성장",
        "principle_reason": "제2원칙: iOS 생태계 락인, App Store 독점 플랫폼. 제3원칙: GPM 46%+, FCF $100B+ p.a. Core 편입.",
    },
    {
        "name": "Meta Platforms",
        "ticker": "META",
        "portfolio_tier": "Core",
        "industry_id": 5,
        "role_description": "SNS 광고 독점(Facebook+Instagram+WhatsApp 30억+ MAU). Llama AI 오픈소스 생태계 주도, Reality Labs AR/VR.",
        "future_growth": "AI 광고 타게팅 수익 YoY +22%+, Llama 모델 엔터프라이즈 확산, Meta AI 어시스턴트 확장",
        "principle_reason": "제2원칙: SNS 네트워크 효과 독점. 제3원칙: OPM 38%+, FCF 마진 30%+. Core 편입.",
    },
    {
        "name": "Amazon",
        "ticker": "AMZN",
        "portfolio_tier": "Core",
        "industry_id": 5,
        "role_description": "글로벌 클라우드 1위(AWS 33% 점유), 이커머스 1위. AWS OPM 38%+ 고마진 독점 인프라.",
        "future_growth": "AWS AI 인프라 수요 급증 YoY +17%+, Bedrock/Trainium 칩 생태계 확대",
        "principle_reason": "제2원칙: AWS 클라우드 인프라 1위 독점. 제3원칙: AWS OPM 38%+. Core 편입.",
    },
    {
        "name": "Broadcom",
        "ticker": "AVGO",
        "portfolio_tier": "Core",
        "industry_id": 9,
        "role_description": "AI ASIC/커스텀 칩 2위(Google TPU, Meta 설계), 네트워킹 반도체 독점. VMware 인수 후 엔터프라이즈 SW 락인.",
        "future_growth": "AI 커스텀 ASIC 수요 YoY +60%+, VMware 구독 전환 3년 내 FCF $20B+ 목표",
        "principle_reason": "제2원칙: AI ASIC 설계 + 네트워킹 반도체 독점. 제3원칙: OPM 35%+, GPM 60%+. Core 편입.",
    },
    {
        "name": "Visa",
        "ticker": "V",
        "portfolio_tier": "Core",
        "industry_id": 5,
        "role_description": "글로벌 결제 네트워크 1위(40%+ 점유). 핀테크 통합 API 네트워크 효과 최강. CAPEX 없는 고마진 자산경량 모델.",
        "future_growth": "글로벌 디지털 결제 확산, Visa Flexible Credential 신사업, 개도국 결제 인프라 확장",
        "principle_reason": "제2원칙: 글로벌 결제 네트워크 독점. 제3원칙: OPM 65%+, ROE 50%+. Core 편입.",
    },
    {
        "name": "Mastercard",
        "ticker": "MA",
        "portfolio_tier": "Core",
        "industry_id": 5,
        "role_description": "글로벌 결제 네트워크 2위(30%+ 점유). 국경간 결제 독점 마진, 핀테크 데이터 서비스 고성장.",
        "future_growth": "국경간 결제 YoY +17%+, 결제 데이터 분석(Mastercard Economics) 서비스 확대",
        "principle_reason": "제2원칙: 글로벌 결제 네트워크 2위 독점. 제3원칙: OPM 55%+. Core 편입.",
    },
    {
        "name": "Synopsys",
        "ticker": "SNPS",
        "portfolio_tier": "Core",
        "industry_id": 9,
        "role_description": "반도체 EDA(전자설계자동화) 1위(Cadence와 양분). ASML/TSMC/NVIDIA 모든 칩 설계 의존. AI 설계 플랫폼 확산.",
        "future_growth": "AI 반도체 설계 복잡도 상승으로 EDA 수요 폭발, Ansys 인수 후 시뮬레이션 생태계 독점",
        "principle_reason": "제2원칙: 반도체 EDA 소프트웨어 독점. 제3원칙: OPM 30%+, GRR 90%+. Core 편입.",
    },
    {
        "name": "Cadence Design Systems",
        "ticker": "CDNS",
        "portfolio_tier": "Core",
        "industry_id": 9,
        "role_description": "반도체 EDA 2위(Synopsys와 과점). 맞춤형 IC 검증/시뮬레이션 독점. AI 칩 설계 필수 인프라.",
        "future_growth": "AI 칩 설계 사이클 폭발, Cadence.AI 설계 자동화 확산, 데이터센터 Si 수요",
        "principle_reason": "제2원칙: 반도체 EDA 과점 독점. 제3원칙: OPM 30%+. Core 편입.",
    },
    # Satellite 등급 (나스닥/S&P500 고성장 알파)
    {
        "name": "Palantir Technologies",
        "ticker": "PLTR",
        "portfolio_tier": "Satellite",
        "industry_id": 5,
        "role_description": "정부/군사 AI 데이터 플랫폼(Gotham) 독점. AIP(AI Platform) 엔터프라이즈 확산, 상업 고객 YoY +55%.",
        "future_growth": "AI Platform 상업 고객 폭발 성장 YoY +55%, 미 국방 TITAN/AI 계약 확대",
        "principle_reason": "제2원칙: 군사/정부 AI 플랫폼 독점 락인. 제3원칙: OPM 흑전+12%~18%. Satellite 편입.",
    },
    {
        "name": "Tesla",
        "ticker": "TSLA",
        "portfolio_tier": "Satellite",
        "industry_id": 2,
        "role_description": "전기차 소프트웨어 OTA 독점(FSD/오토파일럿). Optimus 인간형 로봇 양산 준비, 슈퍼차저 네트워크 1위.",
        "future_growth": "FSD v12 로보택시 상용화, Optimus 로봇 2025년 양산, 에너지 저장(Megapack) 고성장",
        "principle_reason": "제2원칙: FSD AI SW 누적 데이터 독점 + Optimus 로봇 IP. Satellite 편입.",
    },
    {
        "name": "ServiceNow",
        "ticker": "NOW",
        "portfolio_tier": "Satellite",
        "industry_id": 5,
        "role_description": "기업 IT 워크플로 자동화 플랫폼 1위. Now AI 에이전틱 AI 통합 확산. GRR 98%+의 초강력 락인.",
        "future_growth": "Now AI 에이전트 워크플로 확산 YoY +22%+, GRR 98%+ 유지, $15B ARR 목표",
        "principle_reason": "제2원칙: 기업 IT 워크플로 독점 플랫폼. 제3원칙: OPM 20%+, FCF 마진 30%+. Satellite 편입.",
    },
    {
        "name": "CrowdStrike",
        "ticker": "CRWD",
        "portfolio_tier": "Satellite",
        "industry_id": 5,
        "role_description": "클라우드 엔드포인트 보안 1위(30%+ 점유). Falcon 플랫폼 AI 보안 탐지. GRR 120%+ 초과 수익 구조.",
        "future_growth": "Falcon Flex 번들 확산 YoY +25%+, AI SIEM/ID 보안 영역 확장",
        "principle_reason": "제2원칙: AI 클라우드 보안 플랫폼 1위 락인. 제3원칙: OPM 흑전+10%+. Satellite 편입.",
    },
    {
        "name": "Eli Lilly",
        "ticker": "LLY",
        "portfolio_tier": "Satellite",
        "industry_id": 5,
        "role_description": "GLP-1 비만/당뇨 치료제(젭바운드/마운자로) 글로벌 1위. 신약 특허 독점 2030년대까지.",
        "future_growth": "GLP-1 글로벌 시장 2030년 $150B 성장 선점, 경구형 GLP-1 파이프라인",
        "principle_reason": "제2원칙: GLP-1 치료제 특허 독점. 제3원칙: OPM 38%+, 매출 YoY +30%+. Satellite 편입.",
    },
    {
        "name": "S&P Global",
        "ticker": "SPGI",
        "portfolio_tier": "Satellite",
        "industry_id": 5,
        "role_description": "채권 신용등급 2위(Moody's와 양분), 금융 데이터/분석 플랫폼(Market Intelligence). 금융 인프라 독점.",
        "future_growth": "AI 데이터 분석 수요 YoY +10%+, 채권 발행 회복 시 신용등급 수수료 급증",
        "principle_reason": "제2원칙: 채권 신용등급 과점 독점. 제3원칙: OPM 45%+. Satellite 편입.",
    },
    {
        "name": "TransDigm Group",
        "ticker": "TDG",
        "portfolio_tier": "Satellite",
        "industry_id": 5,
        "role_description": "항공기 독점 부품(단일소스 80%+) 제조사. 교체 부품 독점으로 가격 결정력 최강. M&A 성장 전략.",
        "future_growth": "민항기 교체부품 수요 회복, 방산 부품 수요 증가, M&A 지속적 규모 확대",
        "principle_reason": "제2원칙: 항공 독점 부품 단일소스 공급. 제3원칙: EBITDA 마진 50%+. Satellite 편입.",
    },
    {
        "name": "Booking Holdings",
        "ticker": "BKNG",
        "portfolio_tier": "Satellite",
        "industry_id": 5,
        "role_description": "글로벌 온라인 여행 1위(Booking.com+Priceline+Kayak). 숙박 플랫폼 네트워크 효과 독점. EBITDA 마진 30%+.",
        "future_growth": "AI 여행 어시스턴트 통합, 숙박 외 지상 교통/액티비티 확장, 가격 결정력",
        "principle_reason": "제2원칙: 글로벌 여행 예약 플랫폼 1위 네트워크 효과. 제3원칙: OPM 30%+. Satellite 편입.",
    },
    {
        "name": "Marvell Technology",
        "ticker": "MRVL",
        "portfolio_tier": "Satellite",
        "industry_id": 9,
        "role_description": "AI 데이터센터 커스텀 ASIC 고성장(Amazon/Microsoft 설계), 광전자 집적회로(DSP) 1위.",
        "future_growth": "AI ASIC 매출 YoY +100%+ 성장 구간, 광전자 IC 병목 해소 불가",
        "principle_reason": "제2원칙: AI ASIC 설계/광전자 반도체 병목 독점. 제3원칙: 고성장 알파. Satellite 편입.",
    },
    {
        "name": "Arista Networks",
        "ticker": "ANET",
        "portfolio_tier": "Satellite",
        "industry_id": 1,
        "role_description": "AI 데이터센터 이더넷 스위치 1위(클라우드 하이퍼스케일러 점유율 35%+). EOS 네트워크 OS 독점.",
        "future_growth": "AI 클러스터 이더넷 수요 YoY +20%+, 800G 이더넷 초고속 스위치 병목 공급자",
        "principle_reason": "제2원칙: AI 데이터센터 이더넷 스위치 1위 독점. 제3원칙: OPM 38%+. Satellite 편입.",
    },
    {
        "name": "Fortinet",
        "ticker": "FTNT",
        "portfolio_tier": "Satellite",
        "industry_id": 5,
        "role_description": "네트워크 보안 방화벽/SD-WAN 글로벌 1위(FortiGate). ASIC 기반 자체 하드웨어 + 클라우드 SASE 통합.",
        "future_growth": "SASE/제로트러스트 전환 수요 YoY +15%+, FortiAI 위협 탐지 AI 플랫폼",
        "principle_reason": "제2원칙: 방화벽 독점 ASIC + SW 플랫폼. 제3원칙: OPM 25%+. Satellite 편입.",
    },
    {
        "name": "Palo Alto Networks",
        "ticker": "PANW",
        "portfolio_tier": "Satellite",
        "industry_id": 5,
        "role_description": "클라우드 보안 플랫폼 통합(SASE+XDR+SOAR) 1위. Cortex AI 위협 대응 자동화.",
        "future_growth": "AI SIEM/SOAR 통합 플랫폼 수요 YoY +20%+, Next-Gen Firewall 클라우드 전환 가속",
        "principle_reason": "제2원칙: AI 클라우드 보안 플랫폼 1위 통합. 제3원칙: FCF 마진 35%+. Satellite 편입.",
    },
    # Watchlist 등급
    {
        "name": "UnitedHealth Group",
        "ticker": "UNH",
        "portfolio_tier": "Watchlist",
        "industry_id": 5,
        "role_description": "미국 최대 건강보험/의료 플랫폼(OptumHealth+Optum Rx). 의료 데이터 독점 플랫폼.",
        "future_growth": "OptumHealth AI 의료관리 확장, 의약품 약가 협상력, 고령화 의료 수요 구조적 성장",
        "principle_reason": "제2원칙: 의료 데이터/플랫폼 독점. 제3원칙: OPM 8%+안정. Watchlist (MDD -45%+ 대기). 편입.",
    },
    {
        "name": "Snowflake",
        "ticker": "SNOW",
        "portfolio_tier": "Watchlist",
        "industry_id": 5,
        "role_description": "클라우드 데이터 플랫폼(Data Cloud) 1위. AI/ML 워크로드 급증, Cortex AI 분석 플랫폼 확산.",
        "future_growth": "AI 데이터 워크로드 YoY +29%+, Snowpark 데이터 과학 생태계, NRR 128%+",
        "principle_reason": "제2원칙: 멀티클라우드 데이터 독점 플랫폼. 제3원칙: NRR 128%+ 고성장. Watchlist (가격 고평가) 편입.",
    },
]

def update_universe():
    conn = sqlite3.connect(DB_PATH)
    conn.text_factory = lambda b: b.decode('utf-8', errors='ignore')
    cur = conn.cursor()

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    added = 0
    updated = 0
    price_updated = 0

    for s in NEW_STOCKS:
        ticker = s['ticker']
        name = s['name']
        
        # 이미 존재하는지 확인
        existing = cur.execute(
            "SELECT id, portfolio_tier FROM companies WHERE ticker=? LIMIT 1", 
            (ticker,)
        ).fetchone()
        
        if existing:
            comp_id, old_tier = existing
            tier_rank = {'Core':1,'Satellite':2,'Watchlist':3,'Standard':4}
            if tier_rank.get(s['portfolio_tier'],5) < tier_rank.get(old_tier,5):
                cur.execute("""
                    UPDATE companies SET portfolio_tier=?, principle_reason=?
                    WHERE id=?
                """, (s['portfolio_tier'], s['principle_reason'], comp_id))
                updated += 1
                print(f"  UPDATE tier: {name} ({ticker}): {old_tier} -> {s['portfolio_tier']}")
            else:
                print(f"  SKIP: {name} ({ticker}) already exists as {old_tier}")
        else:
            # 신규 삽입
            cur.execute("""
                INSERT INTO companies (name, ticker, industry_id, role_description, future_growth, portfolio_tier, principle_reason)
                VALUES (?,?,?,?,?,?,?)
            """, (name, ticker, s['industry_id'], s['role_description'], s['future_growth'], s['portfolio_tier'], s['principle_reason']))
            comp_id = cur.lastrowid
            added += 1
            print(f"  ADD: {name} ({ticker}) as {s['portfolio_tier']}")

        # yfinance 가격 조회 (전체 공통)
        existing_id = cur.execute("SELECT id FROM companies WHERE ticker=? ORDER BY id LIMIT 1", (ticker,)).fetchone()
        if existing_id:
            comp_id = existing_id[0]
        
        try:
            yf_data = yf.Ticker(ticker)
            hist = yf_data.history(period='1y')
            if not hist.empty:
                current_price = float(hist['Close'].iloc[-1])
                high_52w = float(hist['High'].max())
                mdd_pct = round(((current_price - high_52w) / high_52w) * 100, 2)
                
                buy_signal = 'WAIT'
                if mdd_pct <= -40: buy_signal = 'DEEP_DISCOUNT (3차매수)'
                elif mdd_pct <= -30: buy_signal = 'BUY_READY (2차매수)'
                elif mdd_pct <= -20: buy_signal = 'BUY_READY (1차매수)'
                
                prof = cur.execute("SELECT id FROM company_profiles WHERE company_id=?", (comp_id,)).fetchone()
                if prof:
                    cur.execute("""
                        UPDATE company_profiles SET current_price=?, high_52w=?, mdd_pct=?, buy_signal=?, last_updated=?
                        WHERE company_id=?
                    """, (current_price, high_52w, mdd_pct, buy_signal, now, comp_id))
                else:
                    cur.execute("""
                        INSERT INTO company_profiles (company_id, current_price, high_52w, mdd_pct, buy_signal, last_updated)
                        VALUES (?,?,?,?,?,?)
                    """, (comp_id, current_price, high_52w, mdd_pct, buy_signal, now))
                price_updated += 1
                print(f"    Price: ${current_price:.2f} (52wH: ${high_52w:.2f}, MDD: {mdd_pct:.1f}%, {buy_signal})")
            else:
                print(f"    WARN: No price data for {ticker}")
        except Exception as e:
            print(f"    ERROR price for {ticker}: {e}")

    conn.commit()
    conn.close()
    
    print(f"\nDone: {added} added, {updated} tier upgraded, {price_updated} price updated")
    return added, updated, price_updated

if __name__ == '__main__':
    print("Starting NASDAQ/SP500 universe update...")
    update_universe()
