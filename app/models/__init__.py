"""
Aggregate SQLAlchemy models so importing this module registers them on Base.

Add new models here to ensure Alembic autogenerate picks them up.
"""

from app.menu.menu import Menu  # noqa: F401
