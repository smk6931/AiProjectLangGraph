# AiProjectLangGraph

## 데이터베이스 설정

### PostgreSQL (pgvector)
```bash
docker run -d `
  --name postgres-db `
  -e POSTGRES_USER=ai_user `
  -e POSTGRES_PASSWORD=1234 `
  -e POSTGRES_DB=ai_project `
  -p 5432:5432 `
  pgvector/pgvector:pg16
```

## 환경 변수 설정 (.env)
```
GEMINI_API_KEY=your_gemini_api_key
```

## 캐싱
- 리포트 캐싱은 서버 메모리를 사용합니다 (Redis 불필요)
- 서버 재시작 시 캐시는 초기화되지만, 다음 날 새로 생성됩니다