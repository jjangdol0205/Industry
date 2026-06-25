"""
전체 기업 COGS(매출원가) 전수 수정
- cost_of_revenue가 NULL 또는 0인 경우: revenue - gross_profit으로 채움
- 양쪽 역방향도 처리 (gross_profit이 NULL인 경우: revenue - cost_of_revenue)
"""
import sqlite3, sys, math
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('investment_portal.db')
cur = conn.cursor()

# ── 1단계: 현황 파악 ──────────────────────────────────────────
cur.execute("SELECT COUNT(*) FROM financial_data")
total = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM financial_data WHERE cost_of_revenue IS NULL OR cost_of_revenue = 0")
needs_fix = cur.fetchone()[0]
print(f"전체 {total}개 레코드 중 COGS 수정 필요: {needs_fix}개")

# ── 2단계: NULL 또는 0 → revenue - gross_profit ────────────────
cur.execute("""
    UPDATE financial_data
    SET cost_of_revenue = revenue - gross_profit
    WHERE (cost_of_revenue IS NULL OR cost_of_revenue = 0)
      AND revenue IS NOT NULL AND revenue > 0
      AND gross_profit IS NOT NULL AND gross_profit > 0
      AND (revenue - gross_profit) > 0
""")
fixed_from_gp = cur.rowcount
print(f"revenue - gross_profit으로 채움: {fixed_from_gp}개")

# ── 3단계: gross_profit NULL → revenue - cost_of_revenue (역방향) ─
cur.execute("""
    UPDATE financial_data
    SET gross_profit = revenue - cost_of_revenue
    WHERE (gross_profit IS NULL OR gross_profit = 0)
      AND revenue IS NOT NULL AND revenue > 0
      AND cost_of_revenue IS NOT NULL AND cost_of_revenue > 0
      AND (revenue - cost_of_revenue) > 0
""")
fixed_gp = cur.rowcount
print(f"revenue - cost_of_revenue로 gross_profit 채움: {fixed_gp}개")

# ── 4단계: gross_margin 재계산 (0이거나 NULL인 경우) ───────────
cur.execute("""
    UPDATE financial_data
    SET gross_margin = (gross_profit / revenue) * 100
    WHERE gross_profit IS NOT NULL AND gross_profit > 0
      AND revenue IS NOT NULL AND revenue > 0
      AND (gross_margin IS NULL OR gross_margin = 0)
""")
fixed_gm = cur.rowcount
print(f"gross_margin 재계산: {fixed_gm}개")

# ── 5단계: op_margin 재계산 ──────────────────────────────────────
cur.execute("""
    UPDATE financial_data
    SET op_margin = (operating_income / revenue) * 100
    WHERE operating_income IS NOT NULL
      AND revenue IS NOT NULL AND revenue > 0
      AND (op_margin IS NULL OR op_margin = 0)
""")
fixed_om = cur.rowcount
print(f"op_margin 재계산: {fixed_om}개")

# ── 6단계: net_margin 재계산 ─────────────────────────────────────
cur.execute("""
    UPDATE financial_data
    SET net_margin = (net_income / revenue) * 100
    WHERE net_income IS NOT NULL
      AND revenue IS NOT NULL AND revenue > 0
      AND (net_margin IS NULL OR net_margin = 0)
""")
fixed_nm = cur.rowcount
print(f"net_margin 재계산: {fixed_nm}개")

conn.commit()

# ── 7단계: 최종 검증 ──────────────────────────────────────────────
cur.execute("SELECT COUNT(*) FROM financial_data WHERE cost_of_revenue IS NULL AND revenue IS NOT NULL AND gross_profit IS NOT NULL")
still_null = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM financial_data WHERE cost_of_revenue = 0 AND revenue IS NOT NULL AND gross_profit IS NOT NULL")
still_zero = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM financial_data WHERE cost_of_revenue IS NOT NULL AND cost_of_revenue != 0")
now_ok = cur.fetchone()[0]

print(f"\n=== 최종 결과 ===")
print(f"COGS 정상: {now_ok}개")
print(f"여전히 NULL (gp도 없는 경우): {still_null}개")
print(f"여전히 0 (문제): {still_zero}개")

# 기업별 점검
print(f"\n=== 주요 기업별 최신 연간 데이터 검증 ===")
cur.execute("""
    SELECT c.ticker, c.name, fd.date,
        ROUND(fd.revenue/1e9, 2),
        ROUND(fd.cost_of_revenue/1e9, 2),
        ROUND(fd.gross_profit/1e9, 2),
        ROUND(fd.gross_margin, 1)
    FROM financial_data fd
    JOIN companies c ON fd.company_id = c.id
    WHERE fd.period_type = 'annual'
    ORDER BY c.ticker, fd.date DESC
""")
rows = cur.fetchall()

# 티커별 최신 1개만
seen = {}
for r in rows:
    if r[0] not in seen:
        seen[r[0]] = r

print(f"{'티커':8} {'매출(B)':>10} {'매출원가(B)':>12} {'매출총이익(B)':>14} {'GPM%':>7} {'검증'}")
print("-" * 60)
for ticker, row in sorted(seen.items()):
    ticker, name, date, rev, cogs, gp, gm = row
    check = ''
    if rev and cogs and gp:
        diff = abs(rev - cogs - gp)
        check = '✅' if diff < 0.01 else f'⚠️ diff={diff:.2f}'
    elif rev and not cogs:
        check = '❌ COGS없음'
    print(f"{ticker:8} {str(rev):>10} {str(cogs):>12} {str(gp):>14} {str(gm):>7} {check}")

conn.close()
print("\n완료!")
