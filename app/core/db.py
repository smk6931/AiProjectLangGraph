from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from app.store.store import  create_store_table
from app.user.user_schema import create_user_table

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

pool: AsyncConnectionPool

# database_url = "postgresql://ai_user:1234@localhost:5432/ai_project"
database_url = "postgresql+psycopg://ai_user:1234@localhost:5432/ai_project"

engine = create_engine(database_url, echo = True)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

base = declarative_base()

async def init_pool():
  global pool
  pool = AsyncConnectionPool(
    conninfo = database_url,
    kwargs={"row_factory": dict_row},
    min_size= 1,
    max_size= 50,
    open=False,
  )
  await pool.open()
  print("🔥 DB pool initialized")

async def close_pool():
  global pool
  if pool:
    await pool.close()
    print("🧹 DB pool closed")

def get_pool() -> AsyncConnectionPool:
  if pool is None:
      raise RuntimeError("DB pool is not initialized")
  return pool

tables = [
  create_user_table,
  # create_store_table
]

async def create_tables():
  async with pool.connection() as conn:
      async with conn.cursor() as cur:
        for sql in tables:
          await cur.execute(sql)
        await conn.commit()

async def fetch_one(sql:str, params = ()) -> dict | None:
  async with pool.connection() as conn:
    async with conn.cursor() as cur:
      await cur.execute(sql, params)
      return await cur.fetchone()

async def fetch_all(sql:str, params = ()) -> list[dict]:
  async with pool.connection() as conn:
    async with conn.cursor() as cur:
      await cur.execute(sql, params)
      return await cur.fetchall()

async def execute(sql:str, params = ()):
  async with pool.connection() as conn:
    try:
      async with conn.cursor() as cur:
        await cur.execute(sql, params)
      await conn.commit()
    
    except Exception as e:
      print("execute 실행 실패", e)
      await conn.rollback()

async def execute_return(sql:str, params = ()) -> dict | None:
  async with pool.connection() as conn:
    try:
      async with conn.cursor() as cur:
        await cur.execute(sql, params)
        row = await cur.fetchone()
      await conn.commit()
      return row
    except Exception as e:
      print("execute_insert 실행 실패", e)
      await conn.rollback()