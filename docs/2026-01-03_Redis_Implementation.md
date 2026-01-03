# Redis Caching & Performance Architecture (2026-01-03)

## 1. Project Goal
본 프로젝트는 AI 기반 상권 분석 리포트 생성 시스템의 **응답 속도 개선**과 **시스템 안정성 확보**를 목표로 합니다.
특히, 고비용/고지연의 AI 생성 프로세스를 보완하기 위해 **Redis Caching**을 도입하였으며, 이를 단순 캐싱을 넘어 **Data Integrity**와 **Performance Visualization**까지 고려한 아키텍처로 설계하였습니다.

---

## 2. Infrastructure Architecture
*   **Compute Layer (AWS EC2)**:
    *   **Backend Server**: FastAPI (Python) 기반의 AI 리포트 생성 서버.
    *   **Cache Server**: Redis (In-Memory)가 EC2 내부에 배포되어 네트워크 레이턴시를 최소화한 초고속 응답 보장.
*   **Data Layer (AWS RDS)**:
    *   **Database**: PostgreSQL을 완전 관리형 서비스(RDS)로 분리 운영.
    *   **Benefit**: 컴퓨팅 리소스(EC2)와 데이터 리소스(RDS)의 독립적인 스케일링이 가능하며, 데이터 영속성과 자동 백업을 보장.

---

## 3. Key Features

### A. Hybrid Caching Strategy
*   **Primary**: **Redis (AWS EC2)** - 서버 기반의 고성능 In-Memory DB.
*   **Fallback**: **Local Memory** - Redis 연결 실패 시 자동으로 애플리케이션 메모리 캐시로 전환되어 무중단 서비스 보장.
*   **Zero-Config Dev Env**: SSH Tunneling을 통해 로컬 개발 환경에서도 코드 수정 없이 서버의 Redis 자원을 활용.

### B. "Race Condition" Performance Logic 🏎️
Redis의 성능 우위를 정량적으로 증명하기 위해, 리포트 조회 시 **Redis와 RDBMS(PostgreSQL)의 조회 속도를 실시간으로 경쟁**시키는 로직을 구현하였습니다.
*   **Async Logic**: `asyncio.gather`를 사용하여 두 데이터 소스를 병렬로 조회.
*   **Winning Criteria**: 더 빠른 응답을 준 소스를 승자로 판정하고 채택.
*   **Visualization**: 사용자 UI에 **"Redis Win! (0.003s vs 0.165s)"** 와 같은 로그를 노출하여 약 **50배 이상의 성능 향상**을 시각적으로 입증.

### C. Data Integrity & Validation
*   **Smart Invalidation**: 리포트 초기화(Reset) 시, **DB의 영구 데이터**와 **Redis의 캐시 데이터**를 원자적으로(Atomically) 동시 삭제하여 데이터 불일치 방지.
*   **Quality Gate**: AI가 생성한 JSON 데이터가 손상되었거나 Risk Score가 0점인 불량 리포트는 **캐시 및 DB 저장을 원천 차단**하여 시스템 오염 방지.

---

## 3. Implementation Details

### `app/report/report_service.py`
*   **Flattened Function Structure**: `race_condition_check`, `_measure_redis_speed`, `_measure_db_speed` 등으로 함수를 세분화하여 가독성 및 테스트 용이성 확보.
*   **Race Logic**:
    ```python
    (redis_time, redis_data), (db_time, db_data) = await asyncio.gather(
        _measure_redis_speed(s_id, check_date), 
        _measure_db_speed(s_id, check_date)
    )
    # Winner Selection Logic...
    ```

### `app/core/cache.py`
*   **Singleton Pattern**: Redis 클라이언트 객체를 싱글톤으로 관리하여 커넥션 오버헤드 최소화.
*   **Failover**: `try-except` 블록을 통해 Redis 연결 실패 시 즉시 Local Cache 모드로 전환하는 로버스트한 설계.

---

## 4. Development & Deployment
*   **Local**: `ssh -N -L 6379:localhost:6379 ...` 명령어를 통해 로컬 포트를 서버 Redis로 포워딩.
*   **Server**: EC2 내부에서는 `localhost:6379`로 직접 접속.
*   이로써 **Environment Variable 분기 없이** 단일 코드베이스로 로컬/운영 환경 모두 대응 가능.

---

## 5. Performance Result (Benchmark)
*   **AI Generation**: ~15s (Initial)
*   **DB Retrieval**: ~0.15s
*   **Redis Retrieval**: ~0.003s (**50x Faster**)
➞ Redis 도입을 통해 반복 조회 시 **사용자 경험(UX)을 획기적으로 개선**함.
