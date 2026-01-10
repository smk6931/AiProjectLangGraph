# 🧠 AI-Powered Franchise Manager (LangGraph Agent)

> LangGraph 기반의 자율 에이전트(Autonomous Agent)가 매장 데이터를 분석하고, 외부 정보(날씨, 트렌드)를 결합하여 경영 전략을 제안하는 지능형 프랜차이즈 관리 시스템입니다.

## 🚀 Key Features (핵심 기능)

### 1. 🤖 AI 매니저 (Autonomous Agent)
- **LangGraph(ReAct) Architecture**: 단순 질의응답이 아닌, 스스로 필요한 도구(Tool)를 판단하고 사용하는 에이전트.
- **Cycle & Self-Correction**: 웹 검색 결과가 부족하면 스스로 검색어를 수정하여 재검색하는 **Self-Correction** 루프 구현.
- **Multi-Tool Integration**:
  - `Manual Search`: 매장 운영 매뉴얼 검색 (RAG)
  - `Policy Search`: 본사 규정/정책 검색 (RAG)
  - `Web Search (Tavily)`: 최신 트렌드 및 외부 정보 검색

### 2. 📊 주간 성과 분석 리포트 (Weekly Insight Report)
- **Weekly Comparison Algorithm**: 단순 누적 매출이 아닌, **"지난주 vs 이번주(WoW)"** 성장률을 자동 비교 분석.
- **Context-Aware Analysis**: 매출 데이터와 **날씨(Weather) 정보**를 결합하여, *"비가 와서 배달 매출이 늘었다"*는 식의 인과관계 추론.
- **Automated Workflow**: `Data Fetch` → `Metric Calculation` → `AI Reasoning` → `DB Save`의 파이프라인 자동화.

### 3. 💬 리뷰 심층 분석 (Vector Search RAG)
- **pgvector & OpenAI Embeddings**: 단순 키워드 검색이 아닌, 의미 기반의 벡터 유사도 검색(Semantic Search).
- **Sentiment Analysis**: "커피가 식었어요" 같은 불만 리뷰를 분석하여 운영 개선점 도출.
- **Scenario**: *"비 오는 날 고객들의 주요 불만은?"* 같은 복합 질문에 대해 벡터 검색으로 답변.

## 🛠️ Tech Stack (기술 스택)

| Category | Technology | Usage |
|----------|------------|-------|
| **AI Core** | **LangGraph** | 에이전트 상태 관리, 순환(Cycle) 구조 및 의사결정 워크플로우 구현 |
| | **LangChain** | LLM 인터페이스 및 Tool Chain 구성 |
| | **OpenAI / Gemini** | 추론(Reasoning) 및 텍스트 생성, 임베딩(Vector) 생성 |
| **Backend** | **Python (FastAPI)** | 비동기 API 서버 및 비즈니스 로직 처리 |
| **Database** | **PostgreSQL** | 관계형 데이터 저장 (매출, 주문) |
| | **pgvector** | 벡터 데이터베이스 (매뉴얼, 리뷰 임베딩 저장) |
| **Frontend** | **Streamlit** | 인터랙티브 대시보드 및 채팅 UI 구현 |
| **Search** | **Tavily API** | AI 전용 실시간 웹 검색 |


## 🏁 Getting Started (실행 방법)

### 1. 환경 설정 (Environment Setup)
```bash
# Repository Clone
git clone https://github.com/your-repo/ai-franchise-manager.git

# Install Dependencies
pip install -r requirements.txt
```

### 2. 환경 변수 설정 (.env)
```ini
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIza...
TAVILY_API_KEY=tvly-...
DB_URL=postgresql://user:password@localhost:5432/dbname
```

### 3. 데이터베이스 초기화 및 시딩 (Data Seeding)
```bash
# DB 테이블 생성 및 초기화 (Menu, Stores)
# 15종 메뉴 및 3개 지점(강남, 부산, 속초) 자동 생성
python scripts/reset_and_seed_v2.py

# AI 기반 고품질 리뷰 및 임베딩 생성 (Optional)
python scripts/seed_reviews_monthly.py
```

### 4. 서버 실행 (Run Server)
```bash
# 1. Backend API Server (FastAPI)
python -m uvicorn main:app --reload --port 8080
# 2. Frontend UI (Streamlit)
streamlit run ui/main_ui.py

./venv/scripts/activate

pkill -f uvicorn
pkill -f streamlit
# 2. 백엔드 시작 (Backend Start)
nohup python -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload > server.log 2>&1 &
# 3. 프론트엔드 시작 (Frontend Start)
nohup streamlit run ui/main_ui.py --server.port 8501 --server.address 0.0.0.0 > ui.log 2>&1 &

## AWS RDS 연결
ssh -i "C:\Users\addmin\OneDrive\Desktop\AwsKey\aws_portfolio\aws_son_key.pem" -N -L 5433:database-aws.cpusiq4esjqv.ap-northeast-2.rds.amazonaws.com:5432 ubuntu@15.164.230.250 -o ServerAliveInterval=60

## AWS Redis 연결
ssh -i "C:\Users\addmin\OneDrive\Desktop\AwsKey\aws_portfolio\aws_son_key.pem" -N -L 6379:localhost:6379 ubuntu@15.164.230.250 -o ServerAliveInterval=60
      
## RC2 터미널 접속
ssh -i "C:\Users\addmin\OneDrive\Desktop\AwsKey\aws_portfolio\aws_son_key.pem" ubuntu@15.164.230.250
cd AiProjectLangGraph
source venv/bin/activate

## RC2 파일 복사 Back
scp -i "C:\Users\addmin\OneDrive\Desktop\AwsKey\aws_portfolio\aws_son_key.pem" `
    -r "c:\GitHub\AiProjectLangGraph\app" `
    ubuntu@15.164.230.250:/home/ubuntu/AiProjectLangGraph/

## RC2 파일 복사 Front
scp -i "C:\Users\addmin\OneDrive\Desktop\AwsKey\aws_portfolio\aws_son_key.pem" `
    -r "c:\GitHub\AiProjectLangGraph\ui" `
    ubuntu@15.164.230.250:/home/ubuntu/AiProjectLangGraph/

scp -i "C:\Users\addmin\OneDrive\Desktop\AwsKey\aws_portfolio\aws_son_key.pem" -r . ubuntu@15.164.230.250:/home/ubuntu/AiProjectLangGraph/





## 💡 Trouble Shooting & Insights

### Q. LangGraph를 왜 사용했나요?
단순한 Chain(선형 구조)으로는 복잡한 문제 해결이 어렵습니다. 검색 결과가 불충분할 때 **다시 검색(Loop)**하거나, 질문의 의도를 파악해 **다른 도구(Tool)로 우회**하는 등 유연한 흐름 제어가 필요했기에 상태 머신(State Machine) 기반의 LangGraph를 도입했습니다.

### Q. 날씨 데이터는 어떻게 분석에 활용되나요?
매일 생성되는 매출 데이터(`sales_daily`)에는 당시의 날씨 정보가 함께 태깅됩니다. 리포트 생성 에이전트는 *"지난주 대비 매출 하락"*이라는 Fact와 *"지난주 내내 비가 옴"*이라는 Context를 결합하여 **"우천으로 인한 내점 고객 감소"**라는 인사이트를 도출합니다.

pkill -f uvicorn
pkill -f streamlit
# 2. 백엔드 시작 (Backend Start)
nohup python -m uvicorn main:app --host 0.0.0.0 --port 8080 > server.log 2>&1 &
# 3. 프론트엔드 시작 (Frontend Start)
nohup streamlit run ui/main_ui.py --server.port 8501 --server.address 0.0.0.0 > ui.log 2>&1 &


## 추후에 도전할것
FireCrawl사용 크롤링??

## 📂 서버로 파일 전송 (SCP)
로컬에 있는 프로젝트 파일을 서버로 전송할 때 사용하는 명령어입니다.

```bash
# 로컬(Windows) -> 서버(AWS Ubuntu) 파일 전송
scp -i "C:\Users\addmin\OneDrive\Desktop\AwsKey\aws_portfolio\aws_son_key.pem" -r . ubuntu@15.164.230.250:/home/ubuntu/AiProjectLangGraph/

# 1. Redis 설치
sudo apt update
sudo apt install redis-server -y
# 2. Redis 설정 변경 (외부 접속 허용은 위험하니 로컬만 허용 - 기본값 유지)
# sudo nano /etc/redis/redis.conf  # (필요시 'supervised systemd'로 변경)
# 3. 서비스 시작 및 상태 확인
sudo systemctl restart redis.service
sudo systemctl status redis

redis-cli
keys *

. 🐍 Backend (FastAPI) 로그 보기
API 요청 들어오는 거나 에러 터지는 거 보고 싶을 때:

bash
tail -f server.log
2. 🎨 Frontend (Streamlit) 로그 보기
누가 페이지 접속했는지 보고 싶을 때:

bash
tail -f ui.log
3. 👀 두 개 동시에 보기 (짬뽕 모드)

화면이 좀 정신없을 수 있지만, 둘 다 한 번에 보고 싶으면:
bash
tail -f server.log ui.log


DB_HOST=database-aws.cpusiq4esjqv.ap-northeast-2.rds.amazonaws.com
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres