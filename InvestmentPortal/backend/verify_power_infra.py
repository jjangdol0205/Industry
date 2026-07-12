import sys, warnings
warnings.filterwarnings('ignore')
import database, models, json

db = database.SessionLocal()

print("=" * 60)
print("=== 6. 전력 인프라 산업 체크 ===")
print("=" * 60)

# 1. 산업 리포트
ind = db.query(models.IndustryReport).filter(models.IndustryReport.id == 6).first()
if not ind:
    print("[FAIL] 산업 리포트(id=6) 없음!")
else:
    print(f"[OK] IndustryReport id=6")
    print(f"     title    : {ind.title}")
    print(f"     tag      : {ind.tag}")
    print(f"     file_path: {ind.file_path}")
    print(f"     summary  : {ind.summary[:80] if ind.summary else 'N/A'}...")

print()

# 2. 밸류체인 노드
nodes = db.query(models.ValueChainNode).filter(models.ValueChainNode.industry_id == 6).all()
print(f"[{'OK' if nodes else 'FAIL'}] ValueChainNodes: {len(nodes)}개")
for n in nodes:
    print(f"     id={n.id}: {n.node_name}")

print()

# 3. 기업 목록 + 프로필 + 재무 데이터
companies = db.query(models.Company).filter(models.Company.industry_id == 6).all()
print(f"[{'OK' if len(companies) >= 10 else 'WARN'}] Companies: {len(companies)}개")
print(f"{'ID':<5} {'Ticker':<6} {'Name':<30} {'Profile':<9} {'Annual':<8} {'Qtr':<6} {'Price':>10} {'MarketCap':>12}")
print("-" * 90)

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

    price = f"${profile.current_price:.2f}" if profile and profile.current_price else "N/A"
    cap_val = profile.market_cap if profile and profile.market_cap else 0
    if cap_val >= 1e9:
        cap_str = f"${cap_val/1e9:.1f}B"
    elif cap_val > 0:
        cap_str = f"${cap_val/1e6:.0f}M"
    else:
        cap_str = "N/A"

    status = "OK" if profile and annual >= 3 else "WARN"
    if status == "OK":
        ok_count += 1
    else:
        warn_list.append(c.ticker)

    print(f"{c.id:<5} {c.ticker:<6} {c.name:<30} {str(bool(profile)):<9} {annual:<8} {qtr:<6} {price:>10} {cap_str:>12}")

print()
print(f"==> 결과: {ok_count}/{len(companies)}개 기업 정상 (프로필 + 재무 모두 OK)")
if warn_list:
    print(f"==> 주의 필요: {', '.join(warn_list)}")

print()

# 4. DB 파일 경로 vs 실제 파일 존재 여부
import os
if ind:
    abs_pdf_paths = [
        f"D:\\Industry\\산업자료\\{ind.file_path}",
        f"D:\\Industry\\산업자료\\{ind.file_path.replace('/', '\\')}",
    ]
    found = False
    for p in abs_pdf_paths:
        if os.path.exists(p):
            size_mb = os.path.getsize(p) / 1024 / 1024
            print(f"[OK] PDF 파일 존재: {p} ({size_mb:.1f} MB)")
            found = True
            break
    if not found:
        print(f"[WARN] PDF 파일 없음 - 경로: D:\\Industry\\산업자료\\{ind.file_path}")

# 5. 사이드바 표시 확인 (태그 목록)
print()
print("=== 전체 산업 목록 (사이드바 표시 확인) ===")
all_inds = db.query(models.IndustryReport).all()
for i in all_inds:
    comp_cnt = db.query(models.Company).filter(models.Company.industry_id == i.id).count()
    print(f"  id={i.id}: [{i.tag}] {i.title} ({comp_cnt}개 기업)")

db.close()
print()
print("=" * 60)
print("체크 완료!")
