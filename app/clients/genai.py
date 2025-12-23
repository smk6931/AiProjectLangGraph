import os
import re
from dotenv import load_dotenv
from google import genai
from app.util.decorators import perform_async_logging

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

@perform_async_logging
async def genai_generate_text(prompt: str):
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[{"role": "user", "parts": [{"text": prompt}]}],
        config={
            "response_mime_type": "application/json",
        }
    )
    clean = re.sub(r'[\x00-\x1F\x7F]', ' ', response.text)
    return clean
