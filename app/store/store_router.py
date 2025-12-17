from fastapi import APIRouter
from app.store.store_service import select_stores_all

router = APIRouter()

@router.get("/store/get")
async def get_stores_all():
    results = await select_stores_all()
    return results