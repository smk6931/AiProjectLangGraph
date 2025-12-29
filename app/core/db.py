
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

pool: AsyncConnectionPool

import os
from dotenv import load_dotenv

load_dotenv()

database_url = os.getenv("DATABASE_URL", "postgresql://ai_user:1234@localhost:5432/ai_project")

# SQLAlchemy는 "postgresql://"만 주면 기본적으로 psycopg2를 찾으므로,
# 설치된 psycopg(v3)를 사용하도록 스키마를 명시해줍니다.
engine = create_engine(database_url.replace(
    "postgresql://", "postgresql+psycopg://"), echo=True)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

base = declarative_base()
# Import models directly so Base.metadata is populated for Alembic autogenerate.

# 새 모델이 생기면 아래에 추가하세요.

from app.menu.menu_schema import Menu  # noqa: F401
from app.user.user_schema import User  # noqa: F401
from app.store.store_schema import Store  # noqa: F401
from app.review.review_schema import Review  # noqa: F401
from app.order.order_schema import Order  # noqa: F401
from app.sales.sales_schema import SalesDaily  # noqa: F401
from app.report.report_schema import StoreReport  # noqa: F401
from app.manual.manual_schema import Manual  # noqa: F401
from app.inquiry.inquiry_schema import StoreInquiry  # noqa: F401
from app.policy.policy_schema import Policy  # noqa: F401


async def init_pool():
    global pool
    pool = AsyncConnectionPool(
        conninfo=database_url,
        kwargs={"row_factory": dict_row},
        min_size=1,
        max_size=50,
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


async def fetch_one(sql: str, params=()) -> dict | None:
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, params)
            return await cur.fetchone()


async def fetch_all(sql: str, params=()) -> list[dict]:
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, params)
            return await cur.fetchall()


async def execute(sql: str, params=()):
    async with pool.connection() as conn:
        try:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)
            await conn.commit()
        except Exception as e:
            print("execute 실행 실패", e)
            await conn.rollback()


async def execute_return(sql: str, params=()) -> dict | None:
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
