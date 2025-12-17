from sqlalchemy import Column, Integer, String, Boolean, Numeric

from app.core.db import base

class Menu(base):
  __tablename__ = "menus"

  menu_id = Column(Integer, primary_key=True, index=True)
  menu_name = Column(String(100), nullable=False, index=True)
  category = Column(String(50), nullable=False)   # coffee / dessert
  base_price = Column(Numeric(10, 2), nullable=False)
  is_seasonal = Column(Boolean, default=False)