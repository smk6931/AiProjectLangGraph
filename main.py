from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.clients import genai
from app.core.db import close_pool, init_pool
from app.user import user_router
from app.store import store_router
from app.menu import menu_router
from app.order import order_router
from app.review import review_router
from app.report import report_router
from app.inquiry import inquiry_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    print("🚀 App startup complete")

    yield

    await close_pool()
    print("🧹 App shutdown complete")

app = FastAPI(lifespan=lifespan)

app.include_router(user_router.router)
app.include_router(store_router.router)
app.include_router(menu_router.router)
app.include_router(order_router.router)
app.include_router(review_router.router)
app.include_router(report_router.router)
app.include_router(inquiry_router.router)

# response = genai.genai_generate_text("안녕하세요")
# print("genai 실행", response)


@app.get("/")
def root():
    return {"message": "Ai_Project Run"}
