import sys, warnings, json
warnings.filterwarnings('ignore')
import database, models

db = database.SessionLocal()

# 기존 산업 목록
industries = db.query(models.IndustryReport).all()
print("=== 기존 산업 목록 ===")
for ind in industries:
    comp_count = db.query(models.Company).filter(models.Company.industry_id == ind.id).count()
    print(f"  ID={ind.id}, tag={ind.tag}, file_path={ind.file_path}, companies={comp_count}")

# 에너지 산업 샘플로 구조 확인
energy = db.query(models.IndustryReport).filter(models.IndustryReport.tag.like('%에너지%')).first()
if energy:
    print(f"\n=== 에너지 산업 구조 (샘플) ===")
    print(f"title: {energy.title}")
    print(f"overview: {energy.overview[:200] if energy.overview else 'N/A'}")
    print(f"key_companies_json: {energy.key_companies_json[:200] if energy.key_companies_json else 'N/A'}")
    
    # 에너지 기업 샘플
    comps = db.query(models.Company).filter(models.Company.industry_id == energy.id).limit(3).all()
    for c in comps:
        print(f"  Company: {c.name}({c.ticker}) - {c.segment}")

db.close()
