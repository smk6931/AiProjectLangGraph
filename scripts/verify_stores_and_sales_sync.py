import sys
import os
from sqlalchemy import create_engine, text

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

database_url = "postgresql://ai_user:1234@localhost:5432/ai_project"
engine = create_engine(database_url.replace("postgresql+psycopg://", "postgresql://"))

def main():
    try:
        with engine.connect() as conn:
            print("--- Store IDs ---")
            result = conn.execute(text("SELECT store_id, store_name, city FROM stores"))
            stores = result.fetchall()
            for s in stores:
                print(f"ID {s.store_id}: {s.store_name} ({s.city})")
            
            print("\n--- Sales Data Check (Last 7 days) ---")
            for s in stores:
                sid = s.store_id
                # 'current_date' might need to be explicit or rely on DB
                res = conn.execute(text(f"""
                    SELECT SUM(total_sales) as sum_sales, SUM(total_orders) as sum_orders 
                    FROM sales_daily 
                    WHERE store_id = {sid} 
                      AND sale_date >= (CURRENT_DATE - 7)
                """))
                row = res.fetchone()
                print(f"ID {sid} ({s.store_name}): Sales={row.sum_sales}, Orders={row.sum_orders}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
