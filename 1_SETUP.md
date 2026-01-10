# 🏗️ AI Store Manager - Project Setup Guide

이 문서는 **AI Store Manager** 프로젝트의 로컬 개발 환경 구축부터 AWS EC2 배포, 그리고 DB/Redis 인프라 셋팅까지의 전체 과정을 상세히 안내합니다.

---

## 📌 1. Prerequisites (사전 준비)
*   **Python**: 3.10 이상 (3.12 권장)
*   **Database**: PostgreSQL 15+ (pgvector 확장 필수)
*   **Cache**: Redis
*   **OS**: Windows (Local) / Ubuntu 22.04 LTS (AWS EC2)

---

## �️ 2. Local Development Setup (로컬 개발 환경)

### 2.1 Repository Clone & Virtual Env
```bash
# 프로젝트 다운로드
git clone https://github.com/your-repo/AiProjectLangGraph.git
cd AiProjectLangGraph

# 가상환경 생성 (Windows)
python -m venv venv
.\venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 2.2 Environment Variables (.env)
프로젝트 루트에 `.env` 파일을 생성하고 키를 설정합니다.
```ini
# AI Credentials
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIza...

# Database (Local)
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=ai_project

# Security
SECRET_KEY=super_secret_key_1234
```

---

## ☁️ 3. AWS Infrastructure Setup (EC2 & Infra)

EC2 인스턴스(Ubuntu)에 접속하여 필요한 서비스를 설치합니다.

### 3.1 Redis Installation (EC2)
리포트 조회 속도 향상을 위해 인메모리 캐시인 Redis를 설치합니다.

1.  **설치 및 실행**
    ```bash
    sudo apt update
    sudo apt install redis-server -y
    
    # 설정 파일 수정 (외부 접속 필요 시 bind 수정, 보안 주의)
    # sudo vim /etc/redis/redis.conf
    # bind 127.0.0.1 ::1  <-- 기본값 (Localhost만 허용)
    
    # 재시작 및 상태 확인
    sudo systemctl restart redis.service
    sudo systemctl status redis
    ```

### 3.2 Database Configuration (Architecture Code)

이 프로젝트는 **Modern Python Storage Stack**을 사용하여 데이터베이스를 체계적으로 관리합니다.

#### 🛠️ Tech Stack Roles
*   **PostgreSQL**: 메인 관계형 데이터베이스 (RDBMS).
*   **pgvector**: PostgreSQL의 Extension으로, AI 임베딩 벡터(`Vector[1536]`)를 저장하고 **유사도 검색(Cosine Similarity)**을 가능하게 합니다.
*   **SQLAlchemy (ORM)**: 파이썬 객체(`Class`)와 DB 테이블(`Table`)을 매핑해주는 드라이버입니다. Raw SQL 없이 파이썬 코드로 DB를 조작합니다.
*   **Alembic (Migration)**: DB 스키마의 변경 이력(History)을 버전별로 관리하고 배포하는 도구입니다.

#### ⚙️ Setup Steps

1.  **PostgreSQL pgvector 활성화**
    벡터 검색 기능을 사용하기 위해 DB 내에 확장 기능을 설치해야 합니다. (Admin 권한 필요)
    ```sql
    -- psql 접속 또는 쿼리 툴 사용
    CREATE EXTENSION IF NOT EXISTS vector;
    ```

2.  **Alembic을 이용한 마이그레이션 (Table Create)**
    `models`에 정의된 파이썬 클래스들을 실제 DB 테이블로 변환합니다.

    ```bash
    # 1. 마이그레이션 파일 생성 (DB 설계도 만들기)
    # SQLAlchemy 모델 변경사항을 감지하여 파이썬 스크립트(versions/) 생성
    alembic revision --autogenerate -m "Initial setup"

    # 2. DB 반영 (설계도로 건물 짓기)
    # 실제 CREATE TABLE 쿼리가 실행됨
    alembic upgrade head
    ```

---

## 🏃 4. Running the Application

### 4.1 Backend Server (API)
```bash
# 개발 모드 (Auto Reload)
python -m uvicorn main:app --reload --port 8080

# 배포 모드 (Background Run)
nohup python -m uvicorn main:app --host 0.0.0.0 --port 8080 > server.log 2>&1 &
```

### 4.2 Frontend Client (UI)
```bash
# 개발 모드
streamlit run ui/main_ui.py

# 배포 모드
nohup streamlit run ui/main_ui.py --server.port 8501 --server.address 0.0.0.0 > ui.log 2>&1 &
```

---

## 📡 5. Deploy Code to AWS (코드 배포)

Windows(PowerShell)에서 `scp` 명령어로 코드를 서버에 전송합니다.

```powershell
# 1. Backend 코드 전송
scp -i "key.pem" -r ./app ubuntu@<EC2_IP>:/home/ubuntu/AiProjectLangGraph/

# 2. Frontend 코드 전송
scp -i "key.pem" -r ./ui ubuntu@<EC2_IP>:/home/ubuntu/AiProjectLangGraph/

# 3. 루트 파일(main.py 등) 전송
scp -i "key.pem" main.py requirements.txt alembic.ini ubuntu@<EC2_IP>:/home/ubuntu/AiProjectLangGraph/
```
