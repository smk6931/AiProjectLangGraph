from fastapi import APIRouter
from app.menu.menu_service import select_menus_all

# router = APIRouter(prefix="/menu", tags=["menu"])
router = APIRouter()

@router.get("/menu/get")
async def get_menus_all():
    results = await select_menus_all()
    return results
