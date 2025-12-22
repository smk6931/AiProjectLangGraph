# 캐싱 전략 가이드

## 🤔 Redis vs 메모리 캐싱 vs DB만 사용

### 상황별 권장사항

#### 1. **메모리 캐싱 (권장 ✅)**
**언제?**
- 서버를 추가로 열고 싶지 않을 때
- 단일 서버 환경
- 리포트 같은 가벼운 캐싱

**장점:**
- 서버 추가 불필요
- 매우 빠름 (메모리 직접 접근)
- 구현 간단

**단점:**
- 서버 재시작 시 캐시 사라짐
- 여러 서버 간 공유 불가

**사용법:**
```python
from app.core.cache_simple import get_report_cache, set_report_cache
```

---

#### 2. **Redis 캐싱**
**언제?**
- 여러 서버 간 캐시 공유 필요
- 높은 트래픽
- 복잡한 데이터 구조 필요

**장점:**
- 서버 간 캐시 공유
- 영구 저장 가능
- 다양한 데이터 구조 지원

**단점:**
- 별도 서버 필요
- 원격 환경에서는 네트워크 지연
- 설정 복잡

**사용법:**
```python
from app.core.cache import get_report_cache, set_report_cache
```

---

#### 3. **DB만 사용 (가장 간단)**
**언제?**
- 리포트가 자주 생성되지 않음
- DB 조회가 충분히 빠름
- 캐싱 복잡도 원하지 않음

**장점:**
- 추가 설정 없음
- 이미 구현되어 있음
- 데이터 일관성 보장

**단점:**
- 매번 DB 조회 (약간 느림)
- LLM 호출 비용 절감 없음

**사용법:**
```python
# 캐싱 없이 DB만 조회
report = await select_latest_report(store_id)
```

---

## 📊 속도 비교

### 로컬 환경 (같은 서버)
```
메모리 캐싱: ~0.001ms (가장 빠름) ⚡
Redis: ~0.1ms
PostgreSQL: ~1-5ms
```

### 원격 환경 (클라이언트 → 서버)
```
메모리 캐싱: 네트워크 지연 없음 (서버 내부) ⚡
Redis: 네트워크 지연(10-50ms) + 0.1ms = ~10-50ms
PostgreSQL: 네트워크 지연(10-50ms) + 1-5ms = ~11-55ms
→ 원격에서는 메모리 캐싱이 압도적으로 빠름!
```

---

## 🎯 현재 프로젝트 권장사항

### 리포트 캐싱: 메모리 캐싱 사용 ✅

**이유:**
1. 리포트는 자주 생성되지 않음
2. 같은 날 같은 지점 리포트는 동일
3. 서버 재시작해도 다음 날 새로 생성하면 됨
4. 원격 환경에서도 서버 내부에서 빠르게 조회

**구현:**
- `app/core/cache_simple.py` 사용
- `report_service.py`에서 이미 적용됨

---

## 💡 실무 관점

### 면접에서 어필할 포인트

**"상황에 맞는 캐싱 전략을 선택했습니다"**

1. **메모리 캐싱 선택 이유:**
   - "서버를 추가로 열 필요 없이 Python 메모리만으로 캐싱 구현"
   - "원격 환경에서도 서버 내부에서 빠르게 조회 가능"
   - "리포트는 자주 생성되지 않아 메모리 캐싱으로 충분"

2. **Redis도 이해하고 있음:**
   - "여러 서버 간 캐시 공유가 필요하면 Redis 사용 가능"
   - "높은 트래픽이나 복잡한 데이터 구조가 필요하면 Redis 선택"

3. **비용 최적화:**
   - "LLM API 호출 비용 절감을 위해 캐싱 전략 수립"
   - "같은 날 같은 지점 리포트는 캐시에서 즉시 반환"

---

## 🔄 전환 방법

### 메모리 캐싱 → Redis로 전환

1. `report_service.py`에서 import 변경:
```python
# from app.core.cache_simple import ...  # 주석 처리
from app.core.cache import get_report_cache, set_report_cache  # Redis 사용
```

2. `main.py`에서 Redis 초기화:
```python
from app.core.cache import init_redis, close_redis

async def lifespan(app: FastAPI):
    await init_redis()  # 주석 해제
    ...
    await close_redis()  # 주석 해제
```

3. Redis 서버 실행:
```bash
docker run -d --name redis-cache -p 6379:6379 redis:7-alpine
```

---

## 📝 결론

**현재 프로젝트에서는 메모리 캐싱이 최적입니다.**

- 서버 추가 불필요
- 원격 환경에서도 빠름
- 구현 간단
- 리포트 특성에 적합

Redis는 나중에 필요할 때 추가하면 됩니다.

