import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
from app.util.decorators import perform_async_logging

load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@perform_async_logging
async def openai_generate_text(prompt: str, model: str = "gpt-4o"):
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )
    return response.choices[0].message.content

@perform_async_logging
async def openai_create_embedding(text: str, model: str = "text-embedding-3-small"):
    """
    텍스트를 입력받아 OpenAI Embedding Vector (List[float])를 반환합니다.
    """
    # 줄바꿈 공백 치환 (권장 사항)
    text = text.replace("\n", " ")
    
    response = await client.embeddings.create(
        input=[text],
        model=model
    )
    return response.data[0].embedding