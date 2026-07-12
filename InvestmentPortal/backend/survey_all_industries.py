import sys, warnings
warnings.filterwarnings('ignore')
import database, models

db = database.SessionLocal()

print("=" * 80)
print("전체 산업 & 기업 현황 조사")
print("=" * 80)

all_inds = db.query(models.IndustryReport).order_by(models.IndustryReport.id).all()

for ind in all_inds:
    companies = db.query(models.Company).filter(
        models.Company.industry_id == ind.id
    ).order_by(models.Company.display_order).all()
    
    print(f"\n{'='*60}")
    print(f"[id={ind.id}] {ind.title} (tag={ind.tag}) | 총 {len(companies)}개 기업")
    print(f"{'='*60}")
    
    nodes = db.query(models.ValueChainNode).filter(
        models.ValueChainNode.industry_id == ind.id
    ).all()
    node_map = {n.id: n.node_name for n in nodes}
    
    for c in companies:
        node_name = node_map.get(c.value_chain_node_id, "N/A")[:30]
        print(f"  [{c.id:>3}] {c.ticker:<15} {c.name:<35} | {node_name}")

db.close()
print("\n조사 완료!")
