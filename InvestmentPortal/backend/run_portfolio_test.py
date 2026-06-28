import sys
import warnings
warnings.filterwarnings('ignore')

import database
import models
import agent_harness
import json

db = database.SessionLocal()
try:
    print('포트폴리오 구성 시작...')
    agent_harness.run_portfolio_construction(db)
    print('run_portfolio_construction 완료!')

    report = db.query(models.OrchestrationReport).order_by(
        models.OrchestrationReport.id.desc()
    ).first()

    if report:
        data = json.loads(report.content)
        print('result type:', data.get('type'))
        print('screened:', data.get('total_companies_screened'))
        portfolio = data.get('portfolio', [])
        print('portfolio count:', len(portfolio))
        for item in portfolio:
            r = item['rank']
            t = item['ticker']
            w = item['weight']
            s = item['portfolio_score']
            print(f'  #{r} {t}: {w}%, Score={s}')
        
        sc = data.get('scenario', {})
        if sc:
            base = sc.get('base', {})
            print(f'\nBase scenario: +{base.get("return_pct")}%, CAGR {base.get("cagr")}%/yr')
    else:
        print('ERROR: 보고서가 생성되지 않았습니다!')

except Exception as e:
    import traceback
    print('ERROR:', e)
    traceback.print_exc()
finally:
    db.close()
