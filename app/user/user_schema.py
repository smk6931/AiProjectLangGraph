from pydantic import BaseModel

class Users(BaseModel):
  email : str
  nickname : str
  password_hash : str

class UserLogin(BaseModel):
  email: str

create_user_table = """
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    nickname TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);
"""
