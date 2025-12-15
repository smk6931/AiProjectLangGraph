from fastapi import APIRouter, Body

from app.user.user_schema import UserLogin, Users
from app.user.user_service import user_insert, user_select_byemail

router = APIRouter()

@router.post("/user/create")
async def user_create(body : Users):
  response = await user_insert(body)
  return response

@router.post("/user/login")
async def user_get_byemail(body : UserLogin):
  response = await user_select_byemail(body)
  return response


# @router.post("/user/create")
# async def user_create(user_id : str = Body(...) ):
#   response = await user_insert(user_id)
#   return response