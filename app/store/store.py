create_store_table = """
  CREATE TABLE stores (
      store_id INT PRIMARY KEY,
      store_name VARCHAR(100) NOT NULL,
      region VARCHAR(50) NOT NULL,          -- 서울 / 대구 / 강원 등
      city VARCHAR(50) NOT NULL,            -- UI·지도 표시용
      lat DOUBLE PRECISION NOT NULL,         -- 위도
      lon DOUBLE PRECISION NOT NULL,         -- 경도
      open_date DATE,
      franchise_type VARCHAR(20)             -- 직영 / 가맹
  );
""";