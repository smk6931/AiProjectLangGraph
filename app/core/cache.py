import json
import redis.asyncio as redis
from datetime import date, datetime
from typing import Any, Optional

# ---------------------------------------------------------
# [Redis 및 메모리 캐시 통합 관리] 
# Redis가 연결 가능한 상태면 Redis를 쓰고, 아니면 메모리(Local)를 씁니다.
# ---------------------------------------------------------

# Redis 연결 설정 (기본값: localhost:6379 / DB: 0)
REDIS_URL = "redis://localhost:6379/0"
_redis_client = None
_local_cache = {} # Redis 실패 시 사용될 백업 메모리 캐시

async def get_redis():
    """Redis 클라이언트 싱글톤 반환"""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            # 연결 확인용 테스트
            await _redis_client.ping()
            print("🚀 [Redis] 연결 성공 (localhost:6379)")
        except Exception:
            print("⚠️ [Redis] 연결 실패! 메모리 캐시(Local) 모드로 작동합니다.")
            _redis_client = False # 연결 실패 표시
    return _redis_client

def _make_key(store_id: int, target_date: date) -> str:
    """캐시 키 생성: 'report:1:2025-12-21'"""
    return f"report:{store_id}:{target_date.isoformat()}"



async def get_report_cache(store_id: int, target_date: date) -> Optional[dict]:
    """캐시에서 데이터 조회 (Redis or Memory)"""
    key = _make_key(store_id, target_date)
    client = await get_redis()
    
    # 1. Redis에서 시도
    if client:
        try:
            raw_data = await client.get(key)
            if raw_data:
                print(f"⚡ [Redis Hit] '{key}' 데이터를 불러왔습니다.")
                data = json.loads(raw_data)
                data["cached"] = True
                return data
        except Exception as e:
            print(f"❌ [Redis Error] 조회 실패: {str(e)}")

    # 2. Redis 실패 시 메모리에서 시도
    if key in _local_cache:
        print(f"✅ [Local Hit] '{key}' 데이터를 메모리에서 불러왔습니다.")
        data = _local_cache[key]
        data["cached"] = True
        return data
        
    return None



async def set_report_cache(store_id: int, data: Any, target_date: date, ttl: int = 86400):
    """캐시에 데이터 저장 (Redis & Memory)"""
    key = _make_key(store_id, target_date)
    client = await get_redis()
    
    # JSON 직렬화
    json_data = json.dumps(data, default=str)
    
    # 1. Redis 저장
    if client:
        try:
            await client.set(key, json_data, ex=ttl)
            print(f"💾 [Redis Set] '{key}' 저장 완료 (TTL: {ttl}s)")
        except Exception as e:
            print(f"❌ [Redis Error] 저장 실패: {str(e)}")

    # 2. 메모리에도 백업 저장
    _local_cache[key] = data
    print(f"💾 [Local Set] '{key}' 메모리 저장 완료")

async def get_report_object_cache(store_id: int, target_date: date) -> Optional[dict]:
    """캐시에서 'report' 필드만 쏙 뽑아오기 (Service 간결화용)"""
    cached = await get_report_cache(store_id, target_date)
    return cached.get("report") if cached else None
