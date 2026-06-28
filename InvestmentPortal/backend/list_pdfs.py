import sys, warnings
warnings.filterwarnings('ignore')
import database, models

db = database.SessionLocal()

# 코인 산업 찾기
coin_industry = db.query(models.IndustryReport).filter(
    models.IndustryReport.tag.like('%코인%')
).first()

if coin_industry:
    print(f"코인 산업 ID: {coin_industry.id}, tag: {coin_industry.tag}")
    # PDF 파일 목록
    pdfs = db.query(models.IndustryPdf).filter(
        models.IndustryPdf.industry_id == coin_industry.id
    ).all()
    print(f"\nPDF 파일 목록 ({len(pdfs)}개):")
    for p in pdfs:
        print(f"  ID={p.id}, filename={p.filename}, title={p.title}, path={p.file_path}")

db.close()
