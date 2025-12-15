from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.clients import genai
from app.core.db import close_pool, init_pool, create_tables
from app.user import user_router

@asynccontextmanager
async def lifespan(app: FastAPI):
  await init_pool()
  await create_tables()
  print("🚀 App startup complete")

  yield

  await close_pool()
  print("🧹 App shutdown complete")

app = FastAPI(lifespan=lifespan)

app.include_router(user_router.router)

response = genai.genai_generate_text("안녕하세요")
print("genai 실행", response)

@app.get("/")
def root():
  return {"message" : "Ai_Project Run"}


