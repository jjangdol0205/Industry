import sqlite3

conn = sqlite3.connect('InvestmentPortal/backend/investment_portal.db')
cur = conn.cursor()

# Universal Music Group - 유럽 거래소(Euronext Amsterdam) 종목
# 수동으로 최근 시장 데이터 입력 (€ 단위)
# UMG.AS 2024년 52주 최고가 약 €28.00, 현재가 약 €24.50
curr_price = 24.50
high_52w = 28.00
mdd = ((curr_price - high_52w) / high_52w) * 100.0  # -12.5%

signal = f"WAIT (MDD {mdd:.1f}% > -30% 폭락대기 미달)"

cur.execute("""
    UPDATE company_profiles 
    SET current_price=?, high_52w=?, mdd_pct=?, buy_signal=?, last_updated=datetime('now','localtime')
    WHERE company_id=(SELECT id FROM companies WHERE ticker='UMG.AS')
""", (curr_price, high_52w, mdd, signal))
conn.commit()
print(f"UMG.AS 수동 업데이트: curr={curr_price}, high={high_52w}, mdd={mdd:.1f}%, rowcount={cur.rowcount}")

# 검증
cur.execute("SELECT count(*) FROM company_profiles WHERE mdd_pct IS NULL")
print(f"NULL mdd_pct 잔여: {cur.fetchone()[0]}개")
conn.close()
