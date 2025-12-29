# AWS EC2 & RDS 배포/운영 가이드 (Total Guide)

이 문서는 로컬 개발 환경과 AWS 서버 환경의 차이를 이해하고, `tmux`를 사용하여 서버 프로세스를 관리하며, RDS와 연동하는 모든 과정을 정리한 통합 가이드입니다.

---

## 1. 🏗️ 아키텍처 이해 (가장 중요!)

우리는 **하나의 코드베이스**를 사용하지만, **실행 환경(Local vs Server)**에 따라 DB에 접속하는 방식이 다릅니다.

| 구분 | 로컬(Local) 환경 | AWS 서버(Server) 환경 |
| :--- | :--- | :--- |
| **위치** | 내 컴퓨터 (Windows) | AWS EC2 (Ubuntu) |
| **DB 접속 방식** | **SSH 터널링** (우회 접속) | **Direct Connection** (직통) |
| **Host 설정** | `localhost` | `database-aws.cpusiq4esjqv...` |
| **Port 설정** | `5433` (터널링 포트) | `5432` (기본 포트) |
| **실행 도구** | VS Code 터미널 | `tmux` (가상 터미널) |

---

## 2. ⚙️ 환경변수 (.env) 설정 차이

**보안상 `.env` 파일은 절대 Git에 올리지 않습니다.** 각 환경에서 직접 생성/수정해야 합니다.

### 🏠 2-1. 로컬(Local) `.env`
로컬은 SSH 터널을 통해 접속하므로 `localhost`와 터널 포트(`5433`)를 사용합니다.

```ini
# SSH Tunneling Connection
DB_HOST=localhost
DB_PORT=5433
DB_USER=postgres
DB_PASSWORD=chlrkd1234
DB_NAME=ai_project

# API Keys
GEMINI_API_KEY=AIzaSy...
```

### ☁️ 2-2. 서버(Server) `.env`
서버는 RDS와 같은 네트워크(혹은 허용된 네트워크)에 있으므로 실제 주소를 사용합니다.
*   **수정 방법**: 서버 접속 후 `nano .env` 명령어로 수정.

```ini
# Direct Connection
DB_HOST=database-aws.cpusiq4esjqv.ap-northeast-2.rds.amazonaws.com
DB_PORT=5432  <-- (주의: 5432 정석 포트 사용)
DB_USER=postgres
DB_PASSWORD=chlrkd1234
DB_NAME=ai_project <-- (주의: postgres 아님)

# API Keys
GEMINI_API_KEY=AIzaSy...
```

---

## 3. 🖥️ 서버 프로세스 관리 (Tmux 완벽 가이드)

서버 연결(`ssh`)을 끊어도 프로그램(백엔드/프론트엔드)이 **24시간 계속 돌아가게 하기 위해** `tmux`를 사용합니다.

### ⚡ Tmux 단축키 요약 (Quick Cheat Sheet)

| 동작 | 명령어 / 단축키 | 설명 |
| :--- | :--- | :--- |
| **세션 목록 보기** | `tmux ls` | 현재 실행 중인 모든 세션 확인 |
| **세션 접속하기** | `tmux attach -t portfolio` | 'portfolio' 세션 화면으로 들어가기 |
| **세션 만들기** | `tmux new -s portfolio` | 'portfolio'라는 이름으로 새 방 만들기 |
| **화면 나누기(상하)** | `Ctrl`+`b` 누르고 `"` | 화면을 위/아래로 쪼개기 (백엔드/프론트엔드 동시 실행용) |
| **화면 나누기(좌우)** | `Ctrl`+`b` 누르고 `%` | 화면을 왼쪽/오른쪽으로 쪼개기 |
| **포커스 이동** | `Ctrl`+`b` 누르고 `방향키` | 나눠진 화면 간 이동하기 |
| **스크롤 올리기** | `Ctrl`+`b` 누르고 `[` | 지난 로그 확인 (나갈 땐 `q`) |
| **나가기 (Detach)** | `Ctrl`+`b` 누르고 `d` | **서버를 끄지 않고** 내 컴퓨터로 빠져나오기 |
| **창 닫기** | `exit` 또는 `Ctrl`+`d` | 해당 터미널 창을 완전히 종료 (주의!) |

### 3-1. 실전 사용법 (화면 쪼개서 돌리기)
하나의 창에서 두 개의 서버를 동시에 돌리는 방법입니다.

1.  **접속**: `tmux attach -t portfolio`
2.  **화면 분할**: `Ctrl` + `b` `"` (상하 분할)
3.  **위쪽 창 (Frontend)**:
    ```bash
    streamlit run ui/main_ui.py
    ```
4.  **아래쪽 창 (Backend)**: (이동: `Ctrl`+`b` `↓`)
    ```bash
    python -m uvicorn main:app --host 0.0.0.0 --port 8080
    ```
5.  **나오기**: `Ctrl` + `b` `d`

---

## 4. 🚀 배포 워크플로우 (Local -> Server)

코드를 수정했을 때 서버에 반영하는 순서입니다.

### 1단계: 로컬(Local)에서 작업
```powershell
# 1. 코드 수정 완료
# 2. Git에 올리기
git add .
git commit -m "기능 추가 및 버그 수정"
git push origin feat/migrate-to-rds (또는 main)
```

### 2단계: 서버(Server)에 반영
```bash
# 1. 서버 접속
ssh -i "key.pem" ubuntu@...

# 2. 프로젝트 폴더로 이동
cd AiProjectLangGraph

# 3. 최신 코드 받기
git pull origin feat/migrate-to-rds (또는 main)

# 4. (필요 시) 패키지 설치
source venv/bin/activate
pip install -r requirements.txt

# 5. 서버 재시작 (Tmux 내부)
tmux attach -t portfolio
# -> 각 창에서 Ctrl+C 로 끄고 다시 실행 명령어(화살표 윗키) 입력
```

---

## 5. 🛠️ 트러블슈팅 (자주 겪은 에러)

### Q1. `Connection refused` (111 error)
*   **원인**: 서버 코드가 RDS 주소가 아닌 `localhost`로 접속을 시도함.
*   **해결**: 
    1. 서버 `.env` 파일의 `DB_HOST`가 RDS 주소인지 확인. (`nano .env`)
    2. `app/core/db.py` 코드가 최신인지 확인 (`git pull` 안 했을 가능성).

### Q2. `FATAL: password authentication failed`
*   **원인**: `.env` 파일에 비밀번호 뒤에 **공백(Space)**이 숨어있음.
*   **해결**: `.env` 내용을 지우고 아주 깔끔하게 다시 타이핑.

### Q3. `relation "xxx" does not exist`
*   **원인**: DB 이름이 틀림 (`postgres` vs `ai_project`) 또는 마이그레이션을 안 함.
*   **해결**: 
    1. `.env`의 `DB_NAME=ai_project` 확인.
    2. `alembic upgrade head` 명령어로 테이블 생성.

### Q4. `Missing api_key`
*   **원인**: 서버 `.env`에 `GEMINI_API_KEY` 환경변수가 없음.
*   **해결**: `nano .env`로 키 추가.
