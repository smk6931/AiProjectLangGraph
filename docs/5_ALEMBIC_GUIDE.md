# 🏺 Alembic Setup Guide (DB Migration)

**Alembic**은 SQLAlchemy 모델(Python Class)의 변경 사항을 감지하여 DB 스키마(Table)를 자동으로 관리해주는 도구입니다. 다음 프로젝트 시작 시 이 가이드를 따라 하세요.

---

## 🚀 1. Installation & Init (설치 및 등기)

```bash
# 1. 필수 패키지 설치
pip install alembic sqlalchemy psycopg

# 2. Alembic 초기화 (프로젝트 루트에서 실행)
# 실행하면 'alembic/' 폴더와 'alembic.ini' 파일이 생성됨
alembic init alembic
```

---

## ⚙️ 2. Configuration (연결 설정)

Alembic이 내 DB와 Python 모델을 인식하도록 설정해야 합니다.

### 2.1 `alembic.ini` (DB 주소 연결)
`sqlalchemy.url` 부분을 실제 DB 주소로 수정합니다. (보안상 환경변수 사용 권장)
```ini
# alembic.ini 파일 수정
sqlalchemy.url = postgresql+psycopg://user:password@localhost/dbname
```

### 2.2 `alembic/env.py` (모델 인식시키기) 🔥 **가장 중요!**
Alembic이 파이썬 모델(`class`)을 스캔할 수 있도록 `Base` 객체와 `models`를 임포트해야 합니다.

```python
# alembic/env.py 파일 열기

# 1. 내 프로젝트의 Base와 모델들 임포트
# (주의: 모든 모델을 import해야 Base.metadata에 등록됨)
from app.core.db import base  # 내 프로젝트의 declarative_base
from app.user.user_schema import User
from app.store.store_schema import Store

# 2. target_metadata 설정
# target_metadata = None  <-- 원래 이거 지우고 아래처럼 수정
target_metadata = base.metadata

# ... 나머지 코드는 그대로
```

---

## 📝 3. Model Definition (모델 작성)

`Base(declarative_base)`를 상속받아 클래스를 만듭니다.

```python
# app/core/db.py
from sqlalchemy.orm import declarative_base
base = declarative_base()

# app/user/user_schema.py
from sqlalchemy import Column, Integer, String
from app.core.db import base

class User(base):
    __tablename__ = "users"  # 👈 실제 생성될 테이블 이름

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True)
```

---

## 🏃 4. Migration Execution (실행)

이제 준비 끝! 명령어로 DB를 주무르세요.

### Step 1. 마이그레이션 파일 생성 (변경 감지)
파이썬 모델을 수정했다면, Alembic에게 "차이점을 찾아서 기록해!"라고 명령합니다.
```bash
alembic revision --autogenerate -m "create user table"
```
*   결과: `alembic/versions/` 폴더에 파일이 생김. (열어보면 `CREATE TABLE` 코드가 들어있음)

### Step 2. DB 반영 (업그레이드)
만들어진 설계도를 DB에 실제로 적용합니다.
```bash
alembic upgrade head
```
*   결과: DB에 `users` 테이블이 짠! 하고 나타남.

---

## 💡 Tip: 자주 쓰는 명령어

*   **배포할 때**: 서버에서는 `alembic upgrade head`만 실행하면 됨.
*   **되돌리기**: 실수했다면? `alembic downgrade -1` (한 단계 취소).
