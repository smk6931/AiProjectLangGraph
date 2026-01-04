# 📘 AI Franchise Manager Project Portfolio
> **"단순한 자동화를 넘어, 생각하고 판단하는 AI 매니저"**  
> Streamlit, FastAPI, LangGraph 기반의 자율형 프랜차이즈 관리 시스템

---

## 📅 1. Project Overview (프로젝트 개요)
- **프로젝트명**: AI Franchise Manager (AI 매니저)
- **한 줄 소개**: 가맹점주를 대신해 매출 데이터를 분석하고, 매장 운영 이슈(매뉴얼, 정책)를 해결해주는 AI 에이전트 서비스
- **개발 인원**: 1인 (Full Stack + AI Engineering)
- **주요 기능**:
  1. **주간 매출 분석 리포트**: 100% 자동화된 데이터 수집 및 전략 제안
  2. **AI Inquiry System**: 매뉴얼/규정 RAG 검색 + 웹 검색(Tavily) 기반 하이브리드 답변
  3. **Data Localization**: 한국어 최적화 및 국내 날씨/트렌드 반영

---

## 🏗️ 2. System Architecture (시스템 아키텍처)

### 2.1 Overall Architecture
FastAPI를 중심으로 LangGraph 에이전트가 두뇌 역할을 수행하며, Streamlit UI를 통해 사용자와 소통합니다.

```mermaid
graph TD
    User(Store Owner) --> UI[Streamlit UI]
    UI --> API[FastAPI Server]
    
    subgraph "AI Brain (LangSource)"
        API --> Agent1[🤖 Report Agent\n(Batch Analysis)]
        API --> Agent2[🧠 Inquiry Agent\n(Real-time Chat)]
    end
    
    subgraph "Infrastructure"
        DB[(PostgreSQL\nRDS)]
        VectorDB[(pgvector)]
        Ext1[Tavily Search API]
        Ext2[OpenAI/Gemini API]
    end
    
    Agent1 --> DB
    Agent2 --> VectorDB
    Agent2 --> Ext1
```

### 2.2 Tech Stack (기술 스택)
| 영역 | 기술 | 선정 이유 |
| :--- | :--- | :--- |
| **Language** | Python 3.12 | 최신 비동기 처리에 최적화된 생태계 |
| **AI Core** | **LangGraph** | 복잡한 상태 관리(State)와 순환(Cycle) 구조 구현을 위해 단순 LangChain 대신 채택 |
| **Backend** | **FastAPI** | 높은 성능의 비동기 API 서버, Swagger 문서 자동화 |
| **Database** | **PostgreSQL (RDS)** | 관계형 데이터(매출)와 벡터 데이터(pgvector)를 단일 DB에서 처리하여 관리 복잡도 최소화 |
| **Frontend** | Streamlit | 데이터 시각화와 채팅 UI의 빠른 프로토타이핑 및 배포 |
| **Deployment** | AWS EC2 (Ubuntu) | 리눅스 환경에서의 실제 서비스 배포 경험 |

---

## 💡 3. Key Engineering Features (핵심 기술 역량)

### 3.1 Reliability Engineering (데이터 신뢰성 확보)
**문제**: LLM이 생성하는 JSON 데이터는 형식이 자주 깨지며, 이로 인해 전체 파이프라인이 중단되는 문제가 빈번했습니다.
**해결**:
- **Tag Parsing Strategy**: JSON 파싱 대신 `<SECTION>...</SECTION>` 형태의 커스텀 태그 파싱 로직을 직접 구현하여 파싱 성공률을 획기적으로 높였습니다.
- **Hybrid Validation**: 매출 합계, 성장률 같은 핵심 수치는 AI에게 맡기지 않고 **Python 코드로 직접 계산(Pre-calculation)**하여 AI의 연산 오류(Hallucination)를 원천 차단했습니다.

### 3.2 State-Driven Pipeline (LangGraph)
**문제**: 단순한 함수 호출 방식(Chain)으로는 중간 단계 데이터 확인이나 재시도(Retry) 로직 구현이 어렵습니다.
**해결**: 
- `ReportState`라는 TypedDict를 정의하여, 각 노드(`Fetch` -> `Analyze` -> `Save`)가 명확한 상태를 공유하도록 설계했습니다.
- 이를 통해 데이터 흐름을 시각화하고, 특정 단계에서 문제가 발생했을 때 디버깅이 용이한 구조를 갖췄습니다.

### 3.3 Dynamic Visualization (동적 시각화)
- `Plotly`를 활용하여 단순한 표가 아닌, 반응형 차트(Line, Bar)를 UI에 통합했습니다.
- AI가 분석한 데이터(Top 5 메뉴, 리스크 요인)를 시각적으로 매핑하여 사용자의 의사결정을 돕습니다.

---

## 🛠️ 4. Troubleshooting Logs (트러블 슈팅)

### #1. AWS Connection Refused 사건
- **증상**: 로컬에서는 잘 돌던 서버가 AWS 배포 후 DB 연결을 거부함.
- **원인**: 로컬 개발 시 SSH 터널링 포트(`5433`)를 사용했으나, 서버(`.env`) 설정까지 그대로 복사되어 로컬호스트를 참조함.
- **해결**:
  1. 서버와 로컬 환경을 분리하여 생각하는 습관 형성.
  2. 서버에서는 RDS 엔드포인트를 직접(`5432`) 바라보도록 설정을 수정하고, `pkill` 명령어로 좀비 프로세스를 정리 후 재시동.

### #2. LLM Hallucination 제어
- **증상**: AI가 존재하지 않는 메뉴를 분석 결과로 내놓거나, 매출 합계를 틀림.
- **해결**: RAG(검색 증강 생성)를 통해 DB에 있는 메뉴 정보만 참고하게 강제하고, 수치 계산은 Python 로직으로 이관함.

---

## 🚀 5. Future Roadmap (향후 계획)
1. **Self-Correction Loop 도입**: LangGraph의 Cycle 기능을 활용해, AI가 포맷을 틀리면 스스로 교정하는 로직 추가.
2. **Multi-turn Chat Upgrade**: 현재 Single-turn 위주의 질의응답을 대화 맥락(Context)을 기억하는 구조로 고도화.
