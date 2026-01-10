# ⚡ High Performance Data Strategy (Redis + PostgreSQL)

이 문서는 AI Store Manager 프로젝트의 **데이터 관리 철학**과 **기술적 전략**을 상세히 기술합니다.
우리는 **"생산성"**과 **"성능"**이라는 두 마리 토끼를 잡기 위해 **Hybrid Storage Strategy**를 채택했습니다.

---

## 🏗️ 1. Architecture Overview (데이터 아키텍처)

> **"복잡한 연산은 RDB가, 빠른 조회는 Redis가 담당한다."**

| Layer | Technology | Role | Strategy |
| :--- | :--- | :--- | :--- |
| **Hot Storage** | **Redis** (In-Memory) | 캐싱, 실시간 조회 | `Cache-Aside Pattern`, `TTL` 관리 |
| **Cold Storage** | **PostgreSQL** (RDBMS) | 원본 데이터 저장, 복잡한 통계 | `Hybrid CRUD` (ORM + Raw SQL) |
| **Vector Engine** | **pgvector** | AI 임베딩 검색 (Semantic Search) | 코사인 유사도 연산 (`<=>`) |

---

## 🚀 2. Redis Caching Strategy (고성능 조회)

Redis는 테이블 구조가 없으므로 **Key 설계**가 성능의 90%를 좌우합니다.

### 2.1 Key Naming Convention (키 설계 원칙)
**'합성 키(Composite Key)'** 패턴을 사용하여 데이터의 계층 구조를 직관적으로 표현합니다.
*   **Format**: `{resource_type}:{resource_id}:{date_pk}:{category}`
*   **Example**: `report:1:2025-01-09:sales` (1번 매장의 1월 9일 매출 리포트)

### 2.2 Data Synchronization (동기화)
데이터의 정합성을 위해 **Write-Through**와 **Cache-Aside** 전략을 혼합 사용합니다.
1.  **Read**: Redis 먼저 확인 -> 없으면 DB 조회 후 Redis 적재 (Lazy Loading).
2.  **Reset**: 데이터 초기화 시 `report:{store_id}:*` 패턴으로 관련 캐시 일괄 삭제.

### 2.3 TTL (Time-To-Live)
*   일일 리포트: `24시간` (변동성 낮음)
*   실시간 현황: `10분` (변동성 높음)

---

## 🛡️ 3. RDBMS Strategy (데이터 무결성 & 통계)

PostgreSQL은 데이터의 **원본(Source of Truth)**을 담당하며, 상황에 따라 유연한 쿼리 전략을 사용합니다.

### 3.1 Schema Management (Alembic)
*   **Role**: "DB의 Git". 스키마 변경 사항(버전)을 코드로 관리합니다.
*   **Workflow**:
    1.  Python Model(`class StoreReport`) 수정
    2.  `alembic revision --autogenerate` (마이그레이션 파일 자동 생성)
    3.  `alembic upgrade head` (DB 테이블 자동 변경)

### 3.2 Hybrid CRUD Pattern (ORM vs Raw SQL)
우리는 생산성과 성능 최적화를 위해 두 가지 방식을 적재적소에 사용합니다.

#### (1) SQLAlchemy ORM (사용 비중: 90%)
*   **용도**: 일반적인 데이터 생성(Create), 조회(Read), 수정(Update), 삭제(Delete).
*   **코드 예시**:
    ```python
    # 직관적이고 안전한 객체 지향 코드
    new_report = StoreReport(store_id=1, summary="Clear")
    session.add(new_report)
    session.commit()
    ```
*   **장점**: 개발 속도가 빠르고, 오타로 인한 런타임 에러를 방지함.

#### (2) Raw SQL (사용 비중: 10%)
*   **용도**: 복잡한 통계, 다중 `JOIN`, `Window Function`이 필요한 분석 쿼리.
*   **실제 사례 (`order_service.py`)**:
    *   "최근 7일 vs 지난 7일 메뉴별 매출 비교" 같은 쿼리는 ORM으로 작성 시 코드가 매우 난해해짐.
    *   이 경우 **Raw SQL**을 사용하여 쿼리 의도를 명확히 하고, 실행 계획(Execution Plan)을 최적화함.
    ```python
    # 복잡한 집계는 SQL이 훨씬 강력하고 가독성이 좋음
    sql = """
        SELECT menu_name, 
               SUM(CASE WHEN date >= ... THEN price ELSE 0 END) as recent_sales
        FROM orders ...
        GROUP BY menu_name
    """
    ```

---

## 🤖 4. AI & Vector Strategy (pgvector)
*   **임베딩 저장**: 매뉴얼/규정 텍스트를 OpenAI Embedding API로 벡터화(`Vector[1536]`)하여 DB에 저장.
*   **유사도 검색**: 사용자 질문이 들어오면 `pgvector`의 코사인 거리 연산자(`<=>`)를 사용하여 가장 유사한 문서를 0.1초 내외로 검색.
