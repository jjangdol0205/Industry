"""
코인 산업 PDF 2개 합치기 + DB 정리
"""
import pypdf
import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

PDF1 = r"D:\Industry\산업자료\4. 코인\코인 산업.pdf"
PDF2 = r"D:\Industry\산업자료\4. 코인\코인 산업2.pdf"
OUT  = r"D:\Industry\산업자료\4. 코인\코인 블록체인 산업 심층 분석.pdf"

# ── 1. PDF 병합 ──────────────────────────────
writer = pypdf.PdfWriter()

r1 = pypdf.PdfReader(PDF1)
r2 = pypdf.PdfReader(PDF2)

for page in r1.pages:
    writer.add_page(page)
for page in r2.pages:
    writer.add_page(page)

with open(OUT, "wb") as f:
    writer.write(f)

import os
total_pages = len(r1.pages) + len(r2.pages)
size_mb = os.path.getsize(OUT) / 1024 / 1024
print(f"[OK] PDF 병합 완료: {total_pages}페이지, {size_mb:.1f} MB")
print(f"     저장 경로: {OUT}")

# ── 2. DB 업데이트 ───────────────────────────
conn = sqlite3.connect(r"D:\Industry\InvestmentPortal\backend\investment_portal.db")
cur = conn.cursor()

# id=4를 통합 리포트로 업데이트
cur.execute("""
    UPDATE industry_reports SET
        title    = '코인 & 블록체인 산업 심층 분석',
        summary  = '비트코인·이더리움을 중심으로 한 암호화폐 생태계의 전방위 밸류체인 완전 분석. 채굴(Mining) 인프라부터 거래소, 결제 플랫폼, 기관 금융, 기업 재무전략까지 디지털 자산 산업의 5개 레이어를 심층 분석합니다. BTC 현물 ETF 승인 이후 기관 자금 유입, 반감기(Halving) 사이클, 미국 친암호화폐 정책 전환이 만드는 구조적 기회를 총 45페이지에 걸쳐 분석합니다.',
        file_path = '4. 코인/코인 블록체인 산업 심층 분석.pdf',
        tag      = '코인'
    WHERE id = 4
""")
print("[OK] industry_report id=4 updated to merged report")

# id=5 삭제
cur.execute("DELETE FROM industry_reports WHERE id = 5")
print("[OK] industry_report id=5 deleted")

conn.commit()

# 확인
cur.execute("SELECT id, title, file_path, tag FROM industry_reports ORDER BY id")
print("\n=== 최종 리포트 목록 ===")
for r in cur.fetchall():
    print(f"  [{r[0]}] {r[1]}")
    print(f"       파일: {r[2]}")

conn.close()
print("\n완료!")
