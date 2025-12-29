# 🛠️ Project Command Cheat Sheet

프로젝트 실행 및 배포에 자주 사용되는 명령어 모음입니다.

## 1. Local Development (로컬 실행)

서버 접속 명령어
AWS_EC2 = ssh -i "C:\Users\addmin\OneDrive\Desktop\AwsKey\aws_portfolio\aws_son_key.pem" ubuntu@15.164.230.250

로컬 -> EC2 -> RDS
ssh -i "C:\Users\addmin\OneDrive\Desktop\AwsKey\aws_portfolio\aws_son_key.pem" -L 5433:database-aws.cpusiq4esjqv.ap-northeast-2.rds.amazonaws.com:5432 ubuntu@15.164.230.250 -N

### 가상환경 활성화
```powershell
# Windows PowerShell
./venv/scripts/activate

# Mac/Linux
source venv/bin/activate
```

### Backend 실행 (FastAPI)
```powershell
python -m uvicorn main:app --reload --port 8080
```
> 접속: http://localhost:8080/docs (Swagger UI)

### Frontend 실행 (Streamlit)
```powershell
streamlit run ui/main_ui.py
# 또는
streamlit run ui/dashboard.py
```
> 접속: http://localhost:8501/

---

## 2. Server Deployment (AWS 배포)

### SSH 접속
```powershell
ssh -i "C:\Users\addmin\OneDrive\Desktop\AwsKey\aws_portfolio\aws_son_key.pem" ubuntu@15.164.230.250
```

### Tmux (백그라운드 실행)
```bash
# 세션 생성 (최초)
tmux new -s portfolio

# 세션 다시 접속 (재접속)
tmux attach -t portfolio

# 세션 나가기 (백그라운드 유지)
Ctrl + b 누르고 d
```

---

## 3. Database Info (Reference)

- **AWS RDS Endpoint**: `database-aws.cpusiq4esjqv.ap-northeast-2.rds.amazonaws.com`
- **DB Name**: `postgres`
- **User**: `postgres`


# # AWS RDS 정보
# DB_HOST=database-aws.cpusiq4esjqv.ap-northeast-2.rds.amazonaws.com
# DB_USER=postgres
# DB_PASSWORD=chlrkd1234  # <--- 여기에 아까 그 비밀번호를 넣으세요!
# DB_NAME=postgres
# # DataBase_Url = "database-aws.cpusiq4esjqv.ap-northeast-2.rds.amazonaws.com"
# DATABASE_URL=postgresql://postgres:chlrkd12@database-aws.cpusiq4esjqv.ap-northeast-2.rds.amazonaws.com:5432/postgres