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
            print("Randomizing sales data for ALL stores to ensure variety...")
            
            # 1. Get all store IDs
            result = conn.execute(text("SELECT store_id FROM stores"))
            store_ids = [row.store_id for row in result.fetchall()]
            
            for sid in store_ids:
                # Generate a random factor for each store (e.g., 0.8 to 1.5 multiplier baseline)
                # But we want to apply this to existing data.
                # Use a random seed per store to make it consistent but unique per store.
                
                # Simple approach: Update each store's sales with a random multiplier different for each store
                # We use a SQL random() * multiplier approach but unique per store execution
                
                factor = 0.7 + (random.random() * 0.8) # 0.7 ~ 1.5
                print(f"Store {sid}: Applying multiplier {factor:.2f}")
                
                conn.execute(text(f"""
                    UPDATE sales_daily 
                    SET total_sales = FLOOR(total_sales * {factor}),
                        total_orders = FLOOR(total_orders * {factor})
                    WHERE store_id = {sid}
                """))
                
            conn.commit()
            print("Done. All stores now have distinct sales figures.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
