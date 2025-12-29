# AWS 서버 배포 및 DB 마이그레이션 (트러블슈팅 로그)

## 📌 1. AWS EC2 (Ubuntu) 서버 접속 및 초기 세팅

### 1-1. SSH 접속 (Permission Denied / Timeout 해결)
- **명령어**:  
  `ssh -i "키파일.pem" ubuntu@퍼블릭IP`
- **트러블슈팅**:
  - `Connection timed out`:
    - **원인 1**: 서버가 RAM 부족으로 뻗음(Freeze) -> **AWS 콘솔에서 강제 재부팅**으로 해결.
    - **원인 2**: 보안 그룹(Security Group)에서 내 IP가 차단됨 -> **인바운드 규칙(Port 22)**에 `내 IP` 또는 `0.0.0.0/0` 추가.
  - **결과**: 서버 접속 성공 (`ubuntu@ip-xx-xx...` 프롬프트 확인).

### 1-2. Swap 메모리 설정 (1GB RAM의 한계 극복)
- **증상**: `pip install` 혹은 앱 실행 시 서버가 멈춤.
- **해결책**: 가상 메모리(Swap) 2GB 할당.
- **명령어 (필수)**:
  ```bash
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
  ```

---

## 📌 2. 로컬 DB → AWS RDS 데이터 마이그레이션 (우회 작전)

### 2-1. 문제 상황 (Why?)
- **상황**: 로컬 PC에서 AWS RDS로 바로 접속하려고 했으나 `Connection Timeout` 지속 발생.
- **원인**: 
  - RDS가 **프라이빗 서브넷(Private Subnet)**에 위치하여 외부(인터넷)에서 직접 접속 불가.
  - 퍼블릭 액세스 설정을 켰으나(Yes), 물리적인 네트워크 경로가 없어 접근 실패.
- **해결 전략 (Bastion Host)**: 
  - **EC2 서버**는 RDS와 같은 VPC(내부망)에 있어 접속이 가능함.
  - 따라서 **"내 PC -> EC2 -> RDS"** 경로로 데이터를 전송하기로 결정.

### 2-2. [내 PC] 데이터 덤프 및 전송 (SCP)
1. **로컬 데이터 파일 준비**:
   - 바탕화면에 있는 `my_backup.sql` 사용 (또는 `pg_dump`로 생성).
2. **EC2로 파일 전송 (SCP 명령어)**:
   ```powershell
   scp -i "키파일.pem" "C:\경로\my_backup.sql" ubuntu@EC2_IP:/home/ubuntu/
   ```
   - **결과**: 100% 전송 완료.

### 2-3. [EC2 서버] RDS로 데이터 복원 (Restore)
1. **PostgreSQL 클라이언트 툴 설치**:
   ```bash
   sudo apt-get update && sudo apt-get install postgresql-client -y
   ```
2. **DB 생성 및 데이터 밀어넣기**:
   ```bash
   # 1. DB 생성
   createdb -h [RDS_ENDPOINT] -U postgres ai_project
   
   # 2. 데이터 복원 (비밀번호 입력)
   psql -h [RDS_ENDPOINT] -U postgres -d ai_project -f my_backup.sql
   ```
   - **결과**: `CREATE TABLE`, `COPY` 로그 확인 후 성공.
   - **pgvector 확인**: `SELECT * FROM pg_extension WHERE extname = 'vector';` -> 버전 확인 완료.

---

## 📌 3. 앱 연동 및 GUI 툴(pgAdmin) 접속

### 3-1. 서버 앱(.env) 설정 수정
- EC2 서버 내 `.env` 파일을 수정하여 로컬 DB(`localhost`)가 아닌 RDS를 바라보게 변경.
  ```ini
  DATABASE_URL=postgresql://postgres:비번@RDS_엔드포인트:5432/ai_project
  ```

### 3-2. pgAdmin으로 RDS 접속 (SSH Tunneling)
- **문제**: RDS가 프라이빗 서브넷이라 pgAdmin에서 직접 접속 불가.
- **해결**: pgAdmin의 **SSH Tunnel** 기능 사용.
  - **Connection 탭**: RDS 정보 입력.
  - **SSH Tunnel 탭**:
    - **Tunnel Host**: EC2 퍼블릭 IP
    - **Username**: ubuntu
    - **Identity File**: `.pem` 키 파일 선택
- **결과**: GUI 툴에서 AWS RDS 데이터 조회 성공.
