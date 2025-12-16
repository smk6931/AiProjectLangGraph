import os
import re
import time
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

async def genai_generate_text(prompt: str):
        print("genai_generate_text 시작")
        start = time.perf_counter()

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[{"role": "user", "parts": [{"text": prompt}]}],
            config={
                "response_mime_type": "application/json",
            }
        )
        clean = re.sub(r'[\x00-\x1F\x7F]', ' ', response.text)
        end = time.perf_counter()
        print("genai_generate_text 완료", clean)
        print(f"⏱️ 텍스트 생성 시간: {end-start:.3f}초")
        return clean

# client = genai.Client(api_key = os.gotenv("GEMINI_API_KEY"))

# async def genai_generate_text(prompt: str):
