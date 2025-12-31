# 📱 Project Master Guide (Mobile Friendly)

> **지하철/이동 중에 빠르게 훑어보는 프로젝트 핵심 요약집**
> 현재 날짜: 2025-12-30

---

## 🚨 1. Emergency Cheat Sheet (필수 명령어)

### A. AWS 서버 접속 & 실행 (순서대로)
1. **EC2 접속 (SSH)**
   ```bash
   ssh -i "key.pem" ubuntu@15.164.230.250
   ```
2. **Tmux 세션 열기 (백그라운드 유지)**
   ```bash
   tmux attach -t portfolio
   # (없으면) tmux new -s portfolio
   ```
3. **가상환경 활성화**
   ```bash
   source venv/bin/activate
   ```
4. **Backend 실행 (안 죽게)**
   ```bash
   # --host 0.0.0.0 필수 (외부 접속용)
   python -m uvicorn main:app --host 0.0.0.0 --port 8080
   ```
5. **Tmux 나가기 (서버 켜둔 채로)**
   - `Ctrl` + `b` 누르고 손 떼고 -> `d`

### B. 로컬 개발 환경 (내 컴퓨터)
1. **DB 터널링 연결 (필수)**
   - 별도 터미널 1개 희생해서 켜둬야 함.
   ```powershell
   ssh -i "key.pem" -N -L 5433:database-aws...:5432 ubuntu@15.164...
   ```
2. **Backend 실행**
   ```powershell
   python -m uvicorn main:app --reload --port 8080
   ```
3. **Frontend 실행**
   ```powershell
   streamlit run ui/main_ui.py
   ```

---

## 🏗️ 2. System Architecture (구조도)

### Flow (데이터 흐름)
1. **User**가 `Streamlit UI`에서 질문/버튼 클릭
2. **UI**는 `requests`로 **Backend API (FastAPI)** 호출
3. **Backend**는 `LangGraph Agent`를 깨워 일을 시킴
4. **Agent**는 판단함:
   - "매출 질문이네?" → `Report Agent` (SQL 쿼리)
   - "매뉴얼 질문이네?" → `Inquiry Agent` (RAG 검색)
   - "날씨/트렌드네?" → `Tavily/Google Search` (웹 검색)
5. **DB (PostgreSQL)**에서 데이터를 꺼내 `Gemini`가 요약 후 답변

### 핵심 Tech Stack
- **LangGraph**: 에이전트의 '뇌' (순환, 판단, 메모리 담당)
- **FastAPI**: 에이전트의 '팔다리' (외부와 소통하는 창구)
- **PostgreSQL + pgvector**: '기억 저장소' (매출 데이터 + 매뉴얼 벡터)
- **Streamlit**: '얼굴' (사용자 인터페이스)

---

## 📂 3. Key Files & Modules (뭐가 어디 있는지)

### 🧠 App Core (`app/`)
- `main.py`: 서버 시작점. 모든 라우터(Router)가 모이는 곳.
- `core/db.py`: DB 연결 관리 (Connection Pool).
- **`inquiry/inquiry_agent.py`**: **가장 중요!** 챗봇의 모든 로직(검색, 판단, 답변)이 들어있음.
- **`report/report_graph.py`**: 매출 리포트 생성용 LangGraph.
- `clients/genai.py`: Google Gemini API 호출 함수들.

### 🎨 Frontend (`ui/`)
- `main_ui.py`: 화면 시작점.
- `inquiry_page.py`: 챗봇 화면 구성.
- `sales_component.py`: 매출 리포트 팝업 & 차트(Altair).

---

## 🐍 4. Python & LangGraph Knowledge (면접 대비)

### Q1. 왜 LangGraph를 썼나요?
- **일반 Chain**: A -> B -> C (일직선). 중간에 실패하면 끝.
- **LangGraph**: A -> (판단) -> B or C -> (검색 실패 시) -> A로 돌아가 재검색 (**Cycle**).
- **이유**: "복잡한 현실 문제(데이터 부족, 검색 실패)를 해결하려면 **스스로 루프를 돌며 수정하는 로직**이 필요해서."

### Q2. Async/Await가 뭔가요?
- **비동기 처리**. DB 조회나 AI 응답을 기다리는 동안, 서버가 멈추지 않고 다른 유저 요청을 처리하게 해줌.
- `await fetch_all(...)`: "데이터 가져올 때까지 잠깐 딴 거 하고 있을게."

### Q3. RAG가 뭔가요? (Retrieval-Augmented Generation)
- LLM(Gemini)은 우리 가게 매출을 모름.
- 그래서 **"관련된 문서(Manual)나 데이터(Sales)"를 먼저 찾아서(Retrieval)**,
- 프롬프트에 끼워 넣어주고 **"이거 보고 대답해"라고 시키는 것(Augmentation)**.

---

## 📅 5. Today's Checkpoint (2025-12-30)

- [x] **AWS 서버 메모리**: Swap 2GB 설정 완료 (밤샘 가능)
- [x] **리포트 기능**: '기간 선택' & '초기화' 버튼 추가됨 (시연용 완벽)
- [x] **검색 기능**: Google Grounding(실시간 검색) 탑재 완료
- [ ] **Next Step**: DB 접속 이슈 해결하고, 테이블 구조 개편(Manual/Policy 분리)

> **💡 팁**: 지하철에서 이 문서만 읽어도 프로젝트 전체 흐름이 머리속에 그려질 거야!
