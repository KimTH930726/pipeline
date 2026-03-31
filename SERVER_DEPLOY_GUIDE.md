# 폐쇄망 서버 배포 가이드

## 개요

Pipeline 포탈 + SMAgentLab을 폐쇄망 서버에 배포하는 가이드입니다.

```
[로컬 PC]                    [폐쇄망 서버]
  이미지 빌드 + tar 생성  →    이미지 로드 + 기동
  소스 코드 복사          →    bare repo + 포탈 세팅
```

## 사전 조건

- 폐쇄망 서버에 Docker + Docker Compose 설치됨
- 팀원 SSH 접속 가능
- 로컬 PC에 Docker, Git 설치됨

---

## 1단계: 로컬에서 이미지 준비 (인터넷 PC)

### SMAgentLab 이미지
```bash
cd SMAgentLab
bash scripts/export-images.sh
# → smagentlab-images-latest.tar.gz 생성 (약 1.5~2GB)
```

### Pipeline 포탈 이미지
```bash
cd pipeline
bash scripts/export-images.sh
# → pipeline-images.tar.gz 생성
```

### 서버로 전달
USB 또는 SCP로 아래 파일을 폐쇄망 서버에 전달:
```
smagentlab-images-latest.tar.gz   # SMAgentLab Docker 이미지
pipeline-images.tar.gz            # Pipeline 포탈 Docker 이미지
SMAgentLab/                       # 소스 코드 전체
pipeline/                         # 포탈 소스 코드 전체
```

---

## 2단계: SMAgentLab 기동 (폐쇄망 서버)

```bash
cd SMAgentLab

# .env 생성
cp .env.example .env
vi .env   # DB 비밀번호, LLM 설정 등 편집

# 이미지 로드 + 서비스 기동
bash scripts/import-and-run.sh

# 확인
docker compose ps
curl http://localhost:8000/health
```

결과: `postgres(5432)`, `redis(6379)`, `backend(8000)`, `frontend(8501)` 기동

---

## 3단계: Git bare repo 생성 (폐쇄망 서버, 1회)

팀원들이 clone/push할 중앙 저장소:
```bash
# bare repo 생성
git clone --bare /path/to/SMAgentLab /srv/repos/SMAgentLab.git

# push 허용 설정
cd /srv/repos/SMAgentLab.git
git config receive.denyCurrentBranch updateInstead
```

팀원 확인:
```bash
git clone ssh://user@서버IP/srv/repos/SMAgentLab.git
```

---

## 4단계: Pipeline 포탈 기동 (폐쇄망 서버)

### .env 생성

**docker-compose.yml은 수정하지 마세요.** 모든 환경별 설정은 `.env` 파일로 관리합니다.

```bash
cd pipeline
cp backend/.env.example .env
vi .env
```

### .env 필수 설정

```bash
# === 필수 (반드시 환경에 맞게 변경) ===

# Git 레포 호스트 경로
# - bare repo 경로 또는 프로젝트 소스 경로
# - 주의: 호스트 절대 경로 사용 (Docker 소켓 공유 방식이라 호스트 기준으로 실행됨)
REPO_HOST_PATH=/srv/repos/SMAgentLab.git

# 배포 대상 프로젝트 호스트 경로
# - docker compose restart가 실행되는 위치
# - 주의: 반드시 호스트 절대 경로 (컨테이너 내부 경로 X)
# - 이유: Pipeline 컨테이너가 docker.sock으로 호스트 Docker를 제어하므로
#         compose 파일의 볼륨 마운트가 호스트 기준으로 해석됨
DEPLOY_TARGET_PATH=/home/deploy/SMAgentLab

# API Key 암호화 키
# 생성: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FERNET_SECRET_KEY=생성한키

# JWT 서명 키 (운영 환경에서 반드시 변경)
JWT_SECRET_KEY=운영용키

# 팀원용 clone URL (시작 가이드 페이지에 표시)
GIT_CLONE_URL=ssh://user@서버IP/srv/repos/SMAgentLab.git
```

### .env 선택 설정

```bash
# 초기 관리자 비밀번호 (기본: admin1234)
ADMIN_DEFAULT_PASSWORD=admin1234

# 배포 모드 (기본: restart)
DEPLOY_MODE=restart

# 포탈 포트 (기본: 8080/3000)
PORTAL_PORT=8080
FRONTEND_PORT=3000
```

### 이미지 로드 + 기동
```bash
bash scripts/import-and-run.sh

# 확인
curl http://localhost:8080/api/health
```

결과: 포탈 `frontend(3000)`, `backend(8080)` 기동

---

## 5단계: 관리자 초기 설정

1. 브라우저에서 `http://서버IP:3000` 접속
2. `admin` / `admin1234` 로그인
3. 설정(톱니바퀴) → **비밀번호 변경** (필수)
4. 설정(톱니바퀴) → **LLM API Key 등록** (AI 분석 사용 시)

---

## 6단계: 팀원 온보딩

1. 팀원이 `http://서버IP:3000/signup` 에서 회원가입
2. 관리자가 **사용자 관리** 에서 승인
3. 팀원이 로그인 → **시작 가이드** 탭 참고하여 세팅:
   ```bash
   git clone ssh://user@서버IP/srv/repos/SMAgentLab.git
   cd SMAgentLab
   code .
   ```

---

## 이후 운영

### 일반 배포 흐름 (포탈에서 자동)
```
포탈에서 브랜치 생성
→ 팀원 VSCode에서 개발 + push
→ 포탈 코드 리뷰 + 승인
→ 포탈 배포 실행
→ Python 구문 검사 → main 머지 → docker restart backend
→ 서비스 재기동 (빌드 없이 소스만 반영)
```

### 패키지 추가 시 (pip install 필요한 경우)
소스만 restart로는 새 패키지 반영 불가. 이미지 재빌드 필요:
```
1. 로컬에서 SMAgentLab 이미지 재빌드
   bash scripts/export-images.sh

2. tar 파일 서버 전달

3. 서버에서 이미지 업데이트
   bash scripts/update-images.sh smagentlab-images-latest.tar.gz
```

### Pipeline 포탈 업데이트
```
1. 로컬에서 포탈 이미지 재빌드
   cd pipeline && bash scripts/export-images.sh

2. 서버에서
   docker compose down
   docker load -i pipeline-images.tar.gz
   docker compose up -d
```

---

## 포트 정리

| 서비스 | 포트 | 설명 |
|--------|------|------|
| Pipeline 포탈 (프론트) | 3000 | 웹 UI |
| Pipeline 포탈 (백엔드) | 8080 | API |
| SMAgentLab (백엔드) | 8000 | 앱 서비스 |
| SMAgentLab (프론트) | 8501 | 앱 UI |
| PostgreSQL | 5432 | DB |
| Redis | 6379 | 캐시 |
| 샌드박스 | 9100~9199 | 브랜치별 테스트 환경 |

---

## 스크립트 역할

| 스크립트 | 위치 | 용도 | 사용 시점 |
|---------|------|------|----------|
| `export-images.sh` | SMAgentLab/scripts/ | 앱 이미지 빌드+내보내기 | 로컬, 최초+패키지 변경 시 |
| `import-and-run.sh` | SMAgentLab/scripts/ | 앱 이미지 로드+기동 | 서버, 최초 1회 |
| `update-images.sh` | SMAgentLab/scripts/ | 앱 이미지 업데이트 | 서버, 패키지 변경 시 |
| `export-images.sh` | pipeline/scripts/ | 포탈 이미지 빌드+내보내기 | 로컬, 최초+포탈 업데이트 시 |
| `import-and-run.sh` | pipeline/scripts/ | 포탈 이미지 로드+기동 | 서버, 최초 1회 |
