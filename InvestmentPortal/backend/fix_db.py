import sqlite3
conn = sqlite3.connect('investment_portal.db')
cur = conn.cursor()
cur.execute("UPDATE industry_reports SET file_path='6. 전력 인프라/전력 인프라 산업.pdf' WHERE id=6")
conn.commit()
conn.close()
print("DB updated successfully")
