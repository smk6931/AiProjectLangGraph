# AiProjectLangGraph

## 🚀 프로젝트 개요
AI 기반 프랜차이즈/매장 관리 시스템으로, FastApi와 LangGraph를 활용한 지능형 데이터 분석 및 관리를 목표로 합니다.

---

## 🛠️ 개발 환경 설정 및 터미널 명령어 히스토리

### 1. 초기 환경 설정
Python 라이브러리 설치
```powershell
pip install fastapi uvicorn sqlalchemy psycopg psycopg-pool python-dotenv google-generativeai alembic streamlit pandas pydeck pgvector
```

### 2. 데이터베이스 구성 (Docker & Postgres)
pgvector가 포함된 Postgres 컨테이너 실행
```powershell
docker run -d `
  --name postgres-db `
  -e POSTGRES_USER=ai_user `
  -e POSTGRES_PASSWORD=1234 `
  -e POSTGRES_DB=ai_project `
  -p 5432:5432 `
  pgvector/pgvector:pg16
```
*(참고: 기존 실행 중인 일반 Postgres 컨테이너에 pgvector를 수동 설치하는 경우)*
```powershell
docker exec -u 0 postgres-db apt-get update
docker exec -u 0 postgres-db apt-get install -y postgresql-16-pgvector
```

### 3. 디렉토리 구조 생성
```powershell
mkdir app\store
mkdir app\review
mkdir app\order
mkdir app\sales
```

### 4. Alembic 마이그레이션 (DB 스키마 관리)
Alembic 초기화 (최초 1회)
```powershell
alembic init alembic
```

테이블 추가 및 변경 사항 반영
```powershell
# Store 테이블 추가
.\.venv\Scripts\python -m alembic revision --autogenerate -m "Add stores table"
.\.venv\Scripts\python -m alembic upgrade head

# Review, Order 테이블 추가
.\.venv\Scripts\python -m alembic revision --autogenerate -m "Add reviews and orders tables"
.\.venv\Scripts\python -m alembic upgrade head

# SalesDaily 테이블 추가
.\.venv\Scripts\python -m alembic revision --autogenerate -m "Add sales_daily table"
.\.venv\Scripts\python -m alembic upgrade head

# pgvector 확장 및 임베딩 컬럼 추가 (Review, Menu)
.\.venv\Scripts\python -m alembic revision --autogenerate -m "Add pgvector and embeddings"
.\.venv\Scripts\python -m alembic upgrade head
```

---

## 🗂️ 데이터베이스 스키마 구조
현재 구축된 주요 테이블 명세입니다.

### 1. Stores (매장)
- `store_id`: 매장 고유 ID
- `store_name`, `region`, `city`: 매장명 및 위치 정보
- `lat`, `lon`: 지도 표시 좌표
- `population_density_index`: 상권 분석용 인구 밀도 지수

### 2. Menus (메뉴)
- `menu_id`, `menu_name`: 메뉴 기본 정보
- `description`: 메뉴 설명 **(임베딩 대상)**
- `embedding`: 1536차원 벡터 데이터 (AI 추천용)

### 3. Reviews (리뷰 / VOC)
- `review_id`, `rating`, `review_text`: 리뷰 내용
- `delivery_app`: 주문 플랫폼 (배민/쿠팡 등)
- `embedding`: 1536차원 벡터 데이터 **(AI 분석/분류용)**
- *참고: 별도 카테고리 테이블 대신 임베딩 기반 동적 분석 방식을 채택함.*

### 4. Orders (주문)
- `order_id`, `quantity`, `total_price`: 판매 내역 상세

### 5. SalesDaily (매출 집계)
- `store_id`, `sale_date`: 매장별 일자 (복합 Key 역할)
- `total_sales`: 일 매출 합계 (분석 및 대시보드 성능 최적화용)
