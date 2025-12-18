# ui/api_utils.py
import streamlit as st
import requests

API_BASE_URL = "http://localhost:8080"


def get_api(endpoint: str, params: dict = None):
    """
    HTTP GET 요청 공통 함수
    """
    try:
        url = f"{API_BASE_URL}{endpoint}"
        response = requests.get(url, params=params)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            st.warning("데이터를 찾을 수 없습니다. (404)")
            return None
        else:
            st.error(f"API 오류 발생: {response.status_code}")
            return None

    except requests.exceptions.ConnectionError:
        st.error("🔌 백엔드 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.")
        return None
    except Exception as e:
        st.error(f"알 수 없는 오류 발생: {e}")
        return None


def post_api(endpoint: str, json_data: dict = None):
    """
    HTTP POST 요청 공통 함수
    """
    try:
        url = f"{API_BASE_URL}{endpoint}"
        response = requests.post(url, json=json_data)

        if response.status_code in [200, 201]:
            return response.json()
        else:
            # 에러 응답 처리 (백엔드 상세 메시지가 있으면 표시)
            error_detail = response.json().get('detail', response.status_code)
            st.error(f"요청 실패: {error_detail}")
            return None

    except requests.exceptions.ConnectionError:
        st.error("🔌 백엔드 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.")
        return None
    except Exception as e:
        st.error(f"알 수 없는 오류 발생: {e}")
        return None
