import psycopg
import sys
import os
from dotenv import load_dotenv

# 1. .env 파일 로드
load_dotenv()

# 2. 환경변수에서 정보 가져오기 (없으면 기본값 사용)
DB_HOST = os.getenv("DB_HOST") # .env 필수
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASSWORD")  # .env에서 반드시 읽어와야 함
DB_NAME = os.getenv("DB_NAME", "postgres")

# 3. 검증
if not DB_PASS or not DB_HOST:
    print("❌ [Critical Error] 환경변수 'DB_PASSWORD' 또는 'DB_HOST'가 설정되지 않았습니다.")
    print("   -> .env 파일을 확인해주세요.")
    sys.exit(1)

conn_info = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"

print(f"\n📡 연결 테스트 시작...")
print(f"   Target: {DB_HOST}")
print(f"   User:   {DB_USER}")

try:
    # 타임아웃 5초 설정
    with psycopg.connect(conn_info, connect_timeout=5) as conn:
        print("\n✅ [성공] AWS RDS 연결 성공!")
        print("   방화벽(보안그룹)은 완벽하게 뚫려있습니다.")
        
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            ver = cur.fetchone()[0]
            print(f"   SERVER: {ver}")

except psycopg.OperationalError as e:
    err_msg = str(e)
    print(f"\n❌ [실패] 연결할 수 없습니다.")
    
    if "password authentication failed" in err_msg:
        print("   🔑 원인: 비밀번호가 틀렸습니다.")
        print("   -> .env 파일의 DB_PASSWORD 값을 확인해주세요.")
    elif "timeout" in err_msg:
        print("   🚧 원인: 연결 시간 초과 (방화벽 막힘 or 퍼블릭 액세스 꺼짐)")
    else:
        print(f"   원인 분석 필요: {err_msg}")

except Exception as e:
    print(f"\n❌ [에러] 예상치 못한 오류: {e}")
