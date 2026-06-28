import sys, warnings, json
warnings.filterwarnings('ignore')

import database, models

db = database.SessionLocal()
report = db.query(models.OrchestrationReport).order_by(models.OrchestrationReport.id.desc()).first()
if report:
    data = json.loads(report.content)
    for item in data.get('portfolio', []):
        print('---')
        ticker = item['ticker']
        cur = item['current_price']
        tgt = item['target_price_5y']
        cagr = item['cagr_5y']
        ret = item['total_return_5y']
        reason = item['selection_reason']
        risk = item['key_risk']
        print(f'{ticker}: current=${cur} target=${tgt} cagr={cagr}%/yr total=+{ret}%')
        print(f'  reason: {reason[:150]}')
        print(f'  risk: {risk[:100]}')
db.close()
