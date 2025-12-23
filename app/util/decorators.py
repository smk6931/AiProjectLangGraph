import time
import functools

def perform_async_logging(func):
    """
    [비동기 함수용]
    실행 시간 측정 + 에러 핸들링을 자동으로 해주는 데코레이터
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        func_name = func.__name__
        print(f"🚀 [Start] {func_name}")
        start_time = time.perf_counter()
        
        try:
            # 실제 함수 실행!
            result = await func(*args, **kwargs)
            return result
            
        except Exception as e:
            # 에러 나면 여기서 잡힘
            print(f"💥 [Error] {func_name} 중단: {e}")
            return None # 혹은 raise e
            
        finally:
            # 성공하든 실패하든 무조건 실행
            duration = time.perf_counter() - start_time
            print(f"🏁 [End] {func_name} (⏱️ {duration:.3f}s)")
            
    return wrapper