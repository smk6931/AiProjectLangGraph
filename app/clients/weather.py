import httpx
from datetime import date, datetime

# WMO 기상 코드 매핑 (Open-Meteo 기준)
def map_wmo_code(code: int) -> str:
    if code == 0:
        return "맑음"
    elif code in [1, 2, 3]:
        return "구름"
    elif code in [45, 48]:
        return "안개"
    elif code in [51, 53, 55, 61, 63, 65, 80, 81, 82]:
        return "비"
    elif code in [71, 73, 75, 77, 85, 86]:
        return "눈"
    elif code in [95, 96, 99]:
        return "뇌우/비"
    else:
        return "흐림"

async def fetch_weather_data(dates: list, lat: float = 37.5665, lon: float = 126.9780) -> dict:
    """
    Open-Meteo Archive API를 사용하여 실제 과거 날씨 데이터를 조회합니다.
    API Key가 필요 없으며 무료입니다.
    
    Args:
        dates (list): datetime.date 객체 또는 'YYYY-MM-DD' 문자열 리스트
        lat (float): 위도 (기본값: 서울 시청)
        lon (float): 경도 (기본값: 서울 시청)
        
    Returns:
        dict: { "2024-01-01": "맑음", ... }
    """
    if not dates:
        return {}

    # 1. 날짜 포맷 통일 및 범위 설정
    # 입력된 날짜 중 가장 과거와 가장 미래를 찾아 API 요청 범위를 정합니다.
    sorted_dates = sorted([str(d) for d in dates])
    start_date = sorted_dates[0]
    end_date = sorted_dates[-1]

    # 2. Open-Meteo API 호출 (과거 데이터 아카이브)
    # daily=weather_code : 하루 대표 기상 코드만 요청
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "weather_code",
        "timezone": "auto"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=5.0)
            response.raise_for_status()
            data = response.json()

        # 3. 결과 파싱 및 매핑
        daily_data = data.get("daily", {})
        time_list = daily_data.get("time", []) # ["2024-01-01", "2024-01-02", ...]
        code_list = daily_data.get("weather_code", []) # [0, 3, 61, ...]

        result_map = {}
        for date_str, code in zip(time_list, code_list):
            if code is not None:
                result_map[date_str] = map_wmo_code(code)
            else:
                result_map[date_str] = "알수없음"

        # 요청한 날짜들에 대해서만 필터링하여 반환 (API는 범위 전체를 주므로)
        final_result = {d: result_map.get(d, "기록없음") for d in sorted_dates}
        return final_result

    except Exception as e:
        print(f"❌ [Weather] API 호출 실패: {str(e)}")
        # 실패 시 빈 값 대신 '알수없음' 반환하여 로직 에러 방지
        return {d: "확인불가" for d in sorted_dates}
