# ☁️ AWS EC2 Server Management Guide

이 문서는 AWS EC2 서버에 배포된 `AiProjectLangGraph` 프로젝트의 관리 및 유지보수를 위한 명령어 가이드입니다.

## 🔑 1. SSH 접속 (Connection)
PowerShell 또는 터미널에서 아래 명령어로 서버에 접속합니다.

```powershell
ssh -i "C:\Users\addmin\OneDrive\Desktop\AwsKey\aws_portfolio\aws_son_key.pem" ubuntu@15.164.230.250
```

---

## 🔄 2. 서버 재시작 (Restart) - **가장 중요!**
코드를 수정하거나 배포한 뒤에는 **반드시** 이 과정을 수행해야 합니다.

### [원스텝 명령어] (복사해서 붙여넣기)
```bash
# 1. 기존 프로세스 종료 (죽이기)
pkill -f uvicorn
pkill -f streamlit

# 2. 가상환경 활성화 (혹시 모르니)
source venv/bin/activate

# 3. Backend 실행 (FastAPI, 8080포트)
nohup python -m uvicorn main:app --host 0.0.0.0 --port 8080 > server.log 2>&1 &

# 4. Frontend 실행 (Streamlit, 8501포트)
nohup streamlit run ui/main_ui.py --server.port 8501 --server.address 0.0.0.0 > ui.log 2>&1 &
```

> **💡 명령어 해설**
> - **`nohup`**: "No Hang Up"의 약자. **SSH 접속을 끊거나 터미널을 꺼도 서버가 죽지 않고 계속 돌아가게 만듭니다.**
> - **`&`**: 백그라운드 실행. 명령어를 실행하고 즉시 터미널 입력창(`$`)을 돌려받습니다.
> - **`> logfile 2>&1`**: 정상 출력(1)과 에러 출력(2)을 모두 지정한 파일(`logfile`)에 저장합니다.

---

## 📜 3. 로그 확인 (Monitoring)
서버가 잘 돌아가고 있는지, 혹은 에러가 났는지 확인할 때 사용합니다.

```bash
# Backend 로그 실시간 확인 (나갈 땐 Ctrl + C)
tail -f server.log

# Frontend 로그 실시간 확인
tail -f ui.log
```

## 🚪 4. 포트 확인 (Check Ports)
현재 8080, 8501 포트가 정상적으로 열려있는지 확인합니다.

```bash
sudo netstat -tulpn | grep python
```
(결과에 `8080`과 `8501`이 보여야 정상입니다.)
