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