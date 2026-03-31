# 폐쇄망 서버 배포 가이드

## 개요

```
[로컬 PC - 인터넷]          [폐쇄망 서버]
  이미지 빌드 + tar    →     이미지 로드 + 자동 세팅
  소스 코드 복사       →     스크립트 1줄로 전체 기동
```

## 사전 조건

- 폐쇄망 서버: Docker + Docker Compose + Git + SSH 설치됨
- 로컬 PC: Docker + Git 설치됨

---

## 1단계: 로컬에서 이미지 준비

```bash
# SMAgentLab 이미지
cd SMAgentLab
bash scripts/export-images.sh
# → smagentlab-images-latest.tar.gz

# Pipeline 포탈 이미지
cd pipeline
bash scripts/export-images.sh
# → pipeline-images.tar.gz
```

## 2단계: 서버로 전달

USB 또는 SCP로 전달:
```
smagentlab-images-latest.tar.gz
pipeline-images.tar.gz
SMAgentLab/     (소스 코드 전체)
pipeline/       (포탈 소스 코드 전체)
```

## 3단계: SMAgentLab 기동

```bash
cd SMAgentLab
bash scripts/import-and-run.sh
```

자동으로: 이미지 로드 → .env 확인 → 서비스 기동 (postgres, redis, backend, frontend)

## 4단계: Pipeline 포탈 기동

```bash
cd pipeline
bash scripts/import-and-run.sh --project-path /path/to/SMAgentLab
```

**이 1줄이 자동으로 처리하는 것:**
- .env 파일 자동 생성 (FERNET_SECRET_KEY, JWT_SECRET_KEY 자동 생성)
- Git bare repo 자동 생성 (`/srv/repos/SMAgentLab.git`)
- GIT_CLONE_URL 자동 설정 (서버 IP 자동 감지)
- Docker 이미지 로드 + 서비스 기동

### 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--project-path` | `../SMAgentLab` | SMAgentLab 소스 경로 |
| `--repo-path` | `/srv/repos/SMAgentLab.git` | bare repo 생성 경로 |
| `--server-ip` | 자동 감지 | 서버 IP |
| `--ssh-user` | 현재 사용자 | SSH 계정명 |
| `--images` | `pipeline-images.tar.gz` | 이미지 파일 |

### .env를 직접 수정하고 싶다면

`import-and-run.sh` 실행 전에 `.env`를 먼저 만들어두면 자동 생성을 건너뜁니다:
```bash
cp backend/.env.example .env
vi .env    # 원하는 값 수정
bash scripts/import-and-run.sh
```

## 5단계: 관리자 로그인

1. `http://서버IP:3000` 접속
2. `admin` / `admin1234` 로그인
3. 설정(톱니바퀴) → 비밀번호 변경 + LLM API Key 등록

## 6단계: 팀원 안내

팀원에게 전달할 내용:
```
1. 포탈 접속: http://서버IP:3000
2. 회원가입 → 관리자 승인 대기
3. 로그인 후 "시작 가이드" 탭 참고
```

---

## 이후 운영

### 일반 배포 (포탈에서 자동)
```
브랜치 생성 → 개발(push) → 코드 리뷰(승인) → 배포 실행
→ 구문 검사 → main 머지 → docker restart backend frontend
```

### 패키지 추가 시 (pip/npm install 필요)
```bash
# 로컬에서
cd SMAgentLab && bash scripts/export-images.sh

# 서버에서
bash scripts/update-images.sh smagentlab-images-latest.tar.gz
```

### 포탈 업데이트
```bash
# 로컬에서
cd pipeline && bash scripts/export-images.sh

# 서버에서
docker compose down
docker load -i pipeline-images.tar.gz
docker compose up -d
```

---

## 포트 정리

| 서비스 | 포트 | 설명 |
|--------|------|------|
| Pipeline 포탈 | 3000 | 웹 UI |
| Pipeline API | 8080 | 백엔드 |
| SMAgentLab 백엔드 | 8000 | 앱 API |
| SMAgentLab 프론트 | 8501 | 앱 UI |
| PostgreSQL | 5432 | DB |
| Redis | 6379 | 캐시 |
| 샌드박스 | 9100~9199 | 테스트 환경 |

## 스크립트 정리

| 스크립트 | 위치 | 실행 시점 |
|---------|------|----------|
| `export-images.sh` | SMAgentLab/scripts/ | 로컬: 이미지 빌드 |
| `import-and-run.sh` | SMAgentLab/scripts/ | 서버: 최초 기동 |
| `update-images.sh` | SMAgentLab/scripts/ | 서버: 패키지 변경 시 |
| `export-images.sh` | pipeline/scripts/ | 로컬: 포탈 이미지 빌드 |
| `import-and-run.sh` | pipeline/scripts/ | 서버: 최초 기동 (자동 세팅) |

## 주의사항

- **docker-compose.yml 직접 수정하지 마세요** — 모든 설정은 `.env`로 관리
- **DEPLOY_TARGET_PATH는 호스트 절대 경로** — Docker 소켓 공유 방식이라 호스트 기준
- **postgres/redis는 배포/샌드박스에서 절대 재시작 안 됨** — backend/frontend만 대상
