# AiProjectLangGraph

PostGre 연결 설정
  docker run -d `
  --name postgres-db `
  -e POSTGRES_USER=ai_user `
  -e POSTGRES_PASSWORD=1234 `
  -e POSTGRES_DB=ai_project `
  -p 5432:5432 `
  postgres:16