import os
import re
from dotenv import load_dotenv
from google import genai
from google.genai.types import Tool, GenerateContentConfig, GoogleSearch
from app.util.decorators import perform_async_logging

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

@perform_async_logging
async def genai_generate_text(prompt: str):
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[{"role": "user", "parts": [{"text": prompt}]}],
        config={
            "response_mime_type": "text/plain", # JSON 강제 제거 (유연성 확보)
        }
    )
    # response.text가 None일 경우 안전하게 처리
    result_text = response.text if response.text else ""
    return result_text.strip()

@perform_async_logging
async def genai_generate_with_grounding(prompt: str):
    """
    Google Search Grounding을 사용하여 최신 정보를 검색하고 답변을 생성합니다.
    (Dynamic Retrieval 설정)
    """
    # Google Search 도구 설정
    google_search_tool = Tool(
        google_search=GoogleSearch()
    )

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[{"role": "user", "parts": [{"text": prompt}]}],
        config=GenerateContentConfig(
            tools=[google_search_tool],
            response_modalities=["TEXT"],
        )
    )
    
    # Grounding 메타데이터 (소스 출처 등) 추출
    citations = []
    if response.candidates and response.candidates[0].grounding_metadata:
        metadata = response.candidates[0].grounding_metadata
        if metadata.grounding_chunks:
            for chunk in metadata.grounding_chunks:
                if chunk.web:
                    title = chunk.web.title or "Link"
                    uri = chunk.web.uri
                    citations.append(f"- [{title}]({uri})")
    
    result_text = response.text if response.text else "답변을 생성하지 못했습니다."
    
    # 출처 목록이 있으면 하단에 추가
    if citations:
        # 중복 제거
        unique_citations = list(dict.fromkeys(citations))
        result_text += "\n\n**🌐 참고 출처:**\n" + "\n".join(unique_citations)
        
    return result_text.strip()
