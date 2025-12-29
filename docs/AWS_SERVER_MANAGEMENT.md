# AWS Server Management Guide (feat. Tmux)

이 문서는 AWS EC2 서버에서 **SSH 접속을 종료해도 애플리케이션이 계속 실행되도록 유지**하기 위한 `tmux` 사용법을 정리합니다.

## 1. Why Tmux? (왜 Tmux를 쓰는가?)

SSH로 서버에 접속해서 프로그램을 실행하면, 기본적으로 **터미널 세션이 끊기는 순간 실행 중인 프로그램도 함께 종료**됩니다.
이를 방지하기 위해 **"서버 안에 가상의 모니터(세션)"**를 만들어두고, 우리는 그 모니터만 껐다 켰다 하는 방식을 사용합니다. 이게 바로 **Tmux**입니다.

- **Persistence (지속성)**: 내가 접속을 끊어도 Tmux 세션 안의 프로그램은 영원히 돌아갑니다.
- **Multitasking**: 하나의 SSH 창에서 여러 개의 터미널 화면을 분할해서 쓸 수 있습니다.

---

## 2. Tmux 설치 & 실행 (Workflow)

### Step 1. 설치 (최초 1회)
우분투 서버에 접속한 상태에서 설치합니다.

```bash
sudo apt-get update
sudo apt-get install tmux -y
```

### Step 2. 새로운 세션 만들기 (Start)
프로젝트를 실행할 '방(Session)'을 하나 만듭니다. 이름은 `portfolio`로 지정합니다.

```bash
# 'portfolio'라는 이름의 새로운 세션 시작
tmux new -s portfolio
```
> *명령어를 입력하면 화면 하단에 녹색 띠(상태 바)가 생깁니다. 이제 가상 세션 안에 들어온 것입니다.*

### Step 3. 애플리케이션 실행
가상 세션 안에서 평소처럼 서버를 실행합니다.

```bash
cd AiProjectLangGraph
source venv/bin/activate
streamlit run ui/dashboard.py --server.port 8501 --server.address 0.0.0.0
```

### Step 4. 방 나가기 (Detach) - **중요!**
서버가 돌아가는 상태에서 **프로그램을 끄지 않고** 몸만 빠져나옵니다.

1. **`Ctrl`** + **`b`** 를 누른다. (손을 뗀다)
2. **`d`** 를 누른다.

> *`[detached (from session portfolio)]` 라는 메시지가 뜨며 원래 터미널로 돌아오면 성공입니다.*
> *이제 SSH 접속을 종료해도 서버는 계속 돌아갑니다.*

---

## 3. 다시 접속하기 & 관리 (Maintenance)

나중에 로그를 확인하거나 서버를 재시작해야 할 때 사용합니다.

### 실행 중인 세션 목록 확인
```bash
tmux ls
```

### 세션으로 다시 들어가기 (Re-attach)
```bash
# 'portfolio' 세션으로 복귀
tmux attach -t portfolio
```

### 세션 아예 삭제하기 (Kill)
서버를 완전히 끄거나 세션을 없애고 싶을 때 사용합니다.
```bash
# 'portfolio' 세션 강제 종료
tmux kill-session -t portfolio
```

---

## 4. Tmux 단축키 모음 (Cheat Sheet)
모든 단축키는 **`Ctrl` + `b`** 를 먼저 누르고(Prefix), 손을 뗀 뒤 다음 키를 누릅니다.

- `Ctrl + b`, `d`: 세션 분리하기 (Detach - 밖으로 나가기)
- `Ctrl + b`, `%`: 화면 세로 분할
- `Ctrl + b`, `"`: 화면 가로 분할
- `Ctrl + b`, `방향키`: 분할된 화면 간 이동
- `Ctrl + b`, `x`: 현재 패널(창) 닫기
