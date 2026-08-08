"""
Render 환경에서 /api/reports 500 에러 재현 및 디버깅
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')

# Render와 동일하게 환경 설정
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "investment_portal.db")
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# industry_reports 쿼리
cur.execute("SELECT id, title, tag FROM industry_reports ORDER BY id")
reports = cur.fetchall()
print(f"[OK] industry_reports: {len(reports)} rows")
for r in reports:
    print(f"  id={r[0]}, tag={r[1]}, title={r[2][:30]}")

# companies 쿼리
cur.execute("SELECT COUNT(*) FROM companies")
print(f"\n[OK] companies: {cur.fetchone()[0]} rows")

# value_chain_nodes 쿼리
cur.execute("SELECT COUNT(*) FROM value_chain_nodes")
print(f"[OK] value_chain_nodes: {cur.fetchone()[0]} rows")

# company_profiles 쿼리
cur.execute("SELECT COUNT(*) FROM company_profiles")
print(f"[OK] company_profiles: {cur.fetchone()[0]} rows")

# NULL role_description 확인
cur.execute("SELECT id, name, role_description FROM companies WHERE role_description IS NULL OR role_description=''")
null_role = cur.fetchall()
print(f"\n[CHECK] NULL role_description: {len(null_role)} rows")
for r in null_role[:5]:
    print(f"  id={r[0]}, name={r[1]}")

# NULL future_growth 확인
cur.execute("SELECT COUNT(*) FROM companies WHERE future_growth IS NULL OR future_growth=''")
print(f"[CHECK] NULL future_growth: {cur.fetchone()[0]} rows")

# Simulate Pydantic schema validation
print("\n[TEST] Testing FastAPI schema import...")
try:
    import sqlalchemy
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine)
    db = Session()
    
    import models
    reports_orm = db.query(models.IndustryReport).all()
    print(f"[OK] ORM query: {len(reports_orm)} reports")
    
    import schemas
    from pydantic import ValidationError
    for rep in reports_orm:
        try:
            schema_rep = schemas.IndustryReport.model_validate(rep)
            print(f"[OK] report id={rep.id} ({rep.tag}) validated OK - {len(schema_rep.companies)} companies")
        except Exception as e:
            print(f"[ERROR] report id={rep.id} ({rep.tag}) FAILED: {e}")
    db.close()
except Exception as e:
    print(f"[CRITICAL] Schema test failed: {e}")
    import traceback
    traceback.print_exc()

conn.close()
print("\n[DONE] Debug complete")
