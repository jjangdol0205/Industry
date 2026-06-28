import sys
sys.path.insert(0, 'InvestmentPortal/backend')

import database
import models
import agent_harness

db = database.SessionLocal()
try:
    # 기업 수 확인
    companies = db.query(models.Company).all()
    print(f"Total companies: {len(companies)}")
    
    # 프로파일 수 확인
    profiles = db.query(models.CompanyProfile).all()
    print(f"Total profiles: {len(profiles)}")
    
    industries = db.query(models.IndustryReport).all()
    print(f"Total industries: {len(industries)}")
    
    # 샘플 기업 스코어 테스트
    if companies:
        c = companies[0]
        profile = db.query(models.CompanyProfile).filter(
            models.CompanyProfile.company_id == c.id
        ).first()
        
        print(f"\n=== 샘플 테스트: {c.name} ({c.ticker}) ===")
        print(f"Profile exists: {profile is not None}")
        
        if profile:
            q, grade, sigs = agent_harness.calc_quant_score(profile, [])
            g = agent_harness.calc_growth_score(c, profile, [])
            u = agent_harness.calc_upside_score(c, profile, [])
            port = 0.30 * q + 0.40 * g + 0.30 * u
            print(f"Quant: {q}, Growth: {g}, Upside: {u}")
            print(f"Portfolio Score: {port:.1f}")
            
    # 전체 포트폴리오 구성 실행
    print("\n=== 포트폴리오 구성 시작 ===")
    agent_harness.run_portfolio_construction(db)
    print("\n=== 완료 ===")
    
    # 결과 확인
    report = db.query(models.OrchestrationReport).order_by(
        models.OrchestrationReport.id.desc()
    ).first()
    if report:
        import json
        try:
            data = json.loads(report.content)
            print(f"Portfolio type: {data.get('type')}")
            print(f"Portfolio count: {len(data.get('portfolio', []))}")
            for item in data.get('portfolio', []):
                print(f"  #{item['rank']} {item['ticker']}: {item['weight']}% (Score: {item['portfolio_score']})")
        except Exception as e:
            print(f"JSON parse error: {e}")
            print(report.content[:500])
    
finally:
    db.close()
