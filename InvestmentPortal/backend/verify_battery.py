import sys, warnings
warnings.filterwarnings('ignore')
import database, models, os

db = database.SessionLocal()

print("=" * 65)
print("=== 7. 이차전지 산업 체크 ===")
print("=" * 65)

# 1. 산업 리포트
ind = db.query(models.IndustryReport).filter(models.IndustryReport.id == 7).first()
if not ind:
    print("[FAIL] 산업 리포트(id=7) 없음!")
else:
    print(f"[OK] IndustryReport id=7")
    print(f"     title    : {ind.title}")
    print(f"     tag      : {ind.tag}")
    print(f"     file_path: {ind.file_path}")
    print(f"     summary  : {ind.summary[:80] if ind.summary else 'N/A'}...")

print()

# 2. PDF 파일 존재 확인
if ind:
    pdf_path = f"D:\\Industry\\산업자료\\{ind.file_path.replace('/', chr(92))}"
    if os.path.exists(pdf_path):
        size_mb = os.path.getsize(pdf_path) / 1024 / 1024
        print(f"[OK] PDF 파일 존재: {pdf_path} ({size_mb:.1f} MB)")
    else:
        print(f"[FAIL] PDF 파일 없음: {pdf_path}")

print()

# 3. 밸류체인 노드
nodes = db.query(models.ValueChainNode).filter(models.ValueChainNode.industry_id == 7).all()
print(f"[{'OK' if len(nodes) >= 4 else 'FAIL'}] ValueChainNodes: {len(nodes)}개")
for n in nodes:
    print(f"     id={n.id}: {n.node_name}")

print()

# 4. 기업 목록 + 프로필 + 재무 데이터
companies = db.query(models.Company).filter(models.Company.industry_id == 7).order_by(models.Company.display_order).all()
print(f"[{'OK' if len(companies) >= 9 else 'FAIL'}] Companies: {len(companies)}개")
print()
print(f"{'ID':<5} {'Ticker':<12} {'Name':<25} {'Profile':<9} {'Ann':<6} {'Qtr':<6} {'Price':>14} {'MarketCap':>14}")
print("-" * 95)

ok_count = 0
warn_list = []

for c in companies:
    profile = db.query(models.CompanyProfile).filter(models.CompanyProfile.company_id == c.id).first()
    annual = db.query(models.FinancialData).filter(
        models.FinancialData.company_id == c.id,
        models.FinancialData.period_type == 'annual'
    ).count()
    qtr = db.query(models.FinancialData).filter(
        models.FinancialData.company_id == c.id,
        models.FinancialData.period_type == 'quarterly'
    ).count()

    if profile and profile.current_price:
        # KRW 종목은 단위가 원
        if profile.current_price > 10000:
            price_str = f"KRW{profile.current_price:,.0f}"
        else:
            price_str = f"${profile.current_price:.2f}"
    else:
        price_str = "N/A"

    if profile and profile.market_cap:
        mc = profile.market_cap
        if mc > 1e12:
            cap_str = f"KRW{mc/1e12:.1f}T"
        elif mc > 1e9:
            cap_str = f"KRW{mc/1e9:.0f}B"
        else:
            cap_str = f"KRW{mc/1e6:.0f}M"
    else:
        cap_str = "N/A"

    status = "OK" if profile and annual >= 3 else "WARN"
    if status == "OK":
        ok_count += 1
    else:
        warn_list.append(c.ticker)

    node = db.query(models.ValueChainNode).filter(models.ValueChainNode.id == c.value_chain_node_id).first()
    node_name = node.node_name[:15] if node else "N/A"

    print(f"{c.id:<5} {c.ticker:<12} {c.name:<25} {str(bool(profile)):<9} {annual:<6} {qtr:<6} {price_str:>14} {cap_str:>14}")

print()
print(f"==> 결과: {ok_count}/{len(companies)}개 기업 정상 (프로필 + 재무 OK)")
if warn_list:
    print(f"==> 주의 필요: {', '.join(warn_list)}")

print()

# 5. 밸류체인 레이어별 기업 분류 확인
print("=== 밸류체인 레이어별 배치 ===")
for n in nodes:
    layer_comps = [c for c in companies if c.value_chain_node_id == n.id]
    print(f"  [{n.node_name}] → {', '.join(c.name for c in layer_comps)}")

print()

# 6. 전체 산업 현황
print("=== 전체 산업 목록 ===")
all_inds = db.query(models.IndustryReport).all()
for i in all_inds:
    comp_cnt = db.query(models.Company).filter(models.Company.industry_id == i.id).count()
    flag = " ← NEW" if i.id == 7 else ""
    print(f"  id={i.id}: [{i.tag}] {i.title} ({comp_cnt}개 기업){flag}")

db.close()

print()
print("=" * 65)
print("이차전지 산업 체크 완료!")
