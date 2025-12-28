from app.core.db import execute_return, fetch_one
from app.core.response import Response
from app.user.user_router import Users
from app.user.user_schema import UserLogin

async def user_insert(body : Users):
  user_id = await execute_return("""
    insert into users (email, nickname)
    values (%s, %s)
    returning id;
  """,(body.email, body.nickname))
  print("user_insert user_id 값은?", user_id)
  return "user_insert 완료 user_id는", user_id["id"]

async def user_select_byemail(body : UserLogin):
  row = await fetch_one("""
    select id, email, nickname
    from users
    where email = %s
  """,(body.email,))

  if(row):
    return Response(success=True, data=row["id"], message="user success")
  return Response(success=False, data="",message="user not found")