import psycopg
import sys

# 강제로 값 주입 (테스트용)
DB_HOST = "localhost"
DB_PORT = "5433"
DB_USER = "postgres"
DB_PASS = "chlrkd1234"  # 여기에 진짜 비밀번호 string으로 박음
DB_NAME = "postgres"

conn_info = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

print(f"\n📡 [하드코딩 테스트] 연결 시도...")
print(f"   Target: {DB_HOST}:{DB_PORT}")
print(f"   Pass:   {DB_PASS}")

try:
    with psycopg.connect(conn_info, connect_timeout=5) as conn:
        print("\n✅ [성공] 와! 드디어 연결됨!")
        print("   -> 결론: .env 파일에 보이지 않는 공백/문자가 숨어있었음.")
        
        with conn.cursor() as cur:
             cur.execute("SELECT version();")
             print(f"   Server: {cur.fetchone()[0]}")

except Exception as e:
    print(f"\n❌ [실패] {e}")
    print("   -> 만약 여기서도 실패하면 SSH 터널링 포트 설정 문제일 가능성 높음.")
