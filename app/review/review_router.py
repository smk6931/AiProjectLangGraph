from fastapi import APIRouter
from app.review.review_service import select_reviews_by_store

router = APIRouter(prefix="/review", tags=["review"])


@router.get("/store/{store_id}")
async def get_reviews_by_store(store_id: int):
    return await select_reviews_by_store(store_id)
