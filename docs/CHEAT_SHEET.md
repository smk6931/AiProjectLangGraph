# 🛠️ Project Command Cheat Sheet

프로젝트 실행 및 배포, 서버 관리에 자주 사용되는 핵심 명령어 모음입니다.

---

## 1. Local Development (로컬 실행)

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
```
> 접속: http://localhost:8501/

---

## 2. Server Deployment & Tunnelling (서버 접속)

### ☁️ AWS EC2 서버 단순 접속
서버 내부 작업(DB 확인, git pull 등)을 할 때 사용합니다.
```powershell
ssh -i "C:\Users\addmin\OneDrive\Desktop\AwsKey\aws_portfolio\aws_son_key.pem" ubuntu@15.164.230.250
```

### 🚇 로컬 -> EC2 -> RDS 터널링 (필수)
로컬에서 AWS RDS 데이터를 조회하거나 개발할 때 **항상 켜둬야 하는** 명령어입니다.
```powershell
# 옵션 설명: 
# -o ServerAliveInterval=60 : 60초마다 생존신고 (끊김 방지)
# -N : 터미널 접속 없이 조용히 터널만 뚫기
ssh -o ServerAliveInterval=60 -i "C:\Users\addmin\OneDrive\Desktop\AwsKey\aws_portfolio\aws_son_key.pem" -L 5433:database-aws.cpusiq4esjqv.ap-northeast-2.rds.amazonaws.com:5432 ubuntu@15.164.230.250 -N
```

---

## 3. ⚡ Tmux 사용법 (서버 화면 관리)

서버에서 프론트엔드와 백엔드를 동시에 띄우고 관리하는 단축키입니다.
**(주의: 모든 명령어는 `Ctrl` 키를 누른 상태에서 `b`를 누르고, 손을 뗀 다음 입력해야 함)**

| 상황 | 명령어 / 키 조작 | 설명 |
| :--- | :--- | :--- |
| **세션 접속** | `tmux attach -t portfolio` | 기존에 켜둔 서버 화면으로 들어가기 |
| **화면 나누기(상하)** | `Ctrl`+`b` 뗴고 `"` (따옴표) | 화면을 위/아래로 반반 쪼개기 |
| **위/아래 이동** | `Ctrl`+`b` 떼고 `방향키(↑ ↓)` | 쪼개진 화면 사이를 왔다갔다 이동하기 |
| **나가기 (Detach)** | `Ctrl`+`b` 떼고 `d` | **서버를 끄지 않고** 내 컴퓨터로 살며시 나오기 |
| **스크롤 보기** | `Ctrl`+`b` 떼고 `[` | 지난 로그 확인 (나갈 땐 `q`) |
| **세션 종료** | `exit` | 해당 창 완전히 종료 (주의!) |

---

## 4. 🚀 배포 순서 (Deploy Flow)

로컬에서 코드를 수정하고 서버에 반영하는 정석 코스입니다.

1.  **[로컬] 코드 수정 및 업로드**
    ```powershell
    git add .
    git commit -m "작업 내용"
    git push origin main
    ```

2.  **[서버] 코드 다운로드 및 재시작**
    ```bash
    # 1. 서버 접속
    ssh -i "C:\Users\addmin\OneDrive\Desktop\AwsKey\aws_portfolio\aws_son_key.pem" ubuntu@15.164.230.250
    
    # 2. 코드 당겨오기 (프로젝트 폴더에서)
    git pull origin main
    
    # 3. Tmux 접속
    tmux attach -t portfolio
    
    # 4. 재시작 (각 창에서 진행 - 위/아래 이동은 Ctrl+b 방향키)
    # Ctrl+C 로 끄고 -> 화살표 위(↑) 키 -> Enter (다시 실행)
    ```

---

## 5. 🗄️ Database Info (Reference)

- **AWS RDS Endpoint**: `database-aws.cpusiq4esjqv.ap-northeast-2.rds.amazonaws.com`
- **DB Name**: `ai_project` (서버용) / `postgres` (로컬 터널링용)
- **User**: `postgres`
