import sys
import os
import random
from sqlalchemy import create_engine, text

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

database_url = "postgresql://ai_user:1234@localhost:5432/ai_project"
# Use sync driver
engine = create_engine(database_url.replace("postgresql+psycopg://", "postgresql://"))

def main():
    try:
        with engine.connect() as conn:
            print("UPDATE Store 2 data (Sync)...")
            conn.execute(text("""
                UPDATE sales_daily 
                SET total_sales = total_sales * (0.5 + random()),
                    total_orders = FLOOR(total_orders * (0.5 + random()))
                WHERE store_id = 2
            """))
            conn.commit()
            print("Done.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
