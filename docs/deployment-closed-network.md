# 폐쇄망 리눅스 서버 배포 가이드

> 인터넷이 차단된 사내 리눅스 서버에 Agentic Deployment Portal(pipeline)을 배포하는 절차.
> SMAgentLab과 같은 서버에 함께 운영하는 시나리오를 전제로 한다.

---

## 0. 배포 전 체크리스트

### 양쪽 환경 사전 준비

| 환경 | 필요 사항 |
|---|---|
| **빌드 PC** (인터넷 가능) | Docker Desktop 또는 Docker 24+, 인터넷 접속, 본 저장소 + SMAgentLab 저장소 clone |
| **운영 서버** (폐쇄망) | Linux (Rocky 9 / RHEL 9 / Ubuntu 22.04 권장), Docker 24+, Docker Compose v2, 디스크 여유 ≥ 20GB |

### 반입할 파일 목록

```
/opt/pipeline/
├── docker-compose.yml                    # base
├── docker-compose.prod.yml               # 운영 오버라이드
├── .env                                  # 시크릿 + IMAGE_TAG + LLM_CLIENT_ID/SECRET
├── scripts/
│   ├── import-and-run.sh
│   ├── update-images.sh
│   ├── backup-db.sh
│   └── restore-db.sh
└── pipeline-images-v1.0.tar.gz           # pipeline 이미지 묶음

/opt/smagentlab/
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env
├── init/                                 # DB 초기화 SQL
├── backend/                              # ★ pipeline 배포 시 호스트 마운트로 사용 (반입 필수)
├── scripts/
└── smagentlab-images-v2.16.tar.gz        # SMAgentLab 이미지 묶음
```

> **중요**: SMAgentLab의 `backend/` 디렉토리는 **반드시 함께 반입**해야 한다. pipeline의 `/deploy` 동작이 호스트의 `./backend`를 git merge로 갱신 → SMAgentLab 컨테이너가 마운트로 읽는 구조이기 때문.
>
> 이를 위해 SMAgentLab을 띄울 때 `docker-compose.prod.yml`(pull 차단) + `docker-compose.dev.yml`(소스 마운트)을 **함께** 적용한다. 명칭은 "dev"지만 pipeline의 운영 워크플로우와 동일한 호스트 마운트 메커니즘이 필요하기 때문.

---

## 1. 빌드 PC에서 이미지 생성 (인터넷 환경)

### 1-1. 저장소 준비
```bash
git clone <사내 git>/pipeline.git
git clone <사내 git>/SMAgentLab.git
```

### 1-2. `.env` 작성 (운영용 — pipeline 쪽)
```bash
cd pipeline
cp backend/.env.example .env
```

`.env`에서 채워야 할 항목:
```env
# 이미지 버전 태그 (운영 환경에서는 :latest 비추천)
IMAGE_TAG=v1.0

# 운영 PC에서 직접 생성한 시크릿
JWT_SECRET_KEY=<python -c "import secrets; print(secrets.token_hex(32))" 결과>
FERNET_SECRET_KEY=<python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 결과>

# 폐쇄망에서는 prod+dev 오버라이드 필수 (SMAgentLab dev.yml의 backend 마운트도 함께 적용)
DEPLOY_COMPOSE_OVERRIDES=docker-compose.prod.yml,docker-compose.dev.yml
DEPLOY_MODE=restart

# 호스트 절대 경로
DEPLOY_TARGET_PATH=/opt/smagentlab
REPO_HOST_PATH=/srv/repos/SMAgentLab.git

ADMIN_DEFAULT_PASSWORD=<초기 admin 비밀번호>

# LLM (DevX Gateway, client_credentials OAuth2 + SSE streaming)
LLM_AUTH_ENDPOINT=https://devx-gw.shinsegae-inc.com/api/v1/auth/token
LLM_CHAT_ENDPOINT=https://devx-gw.shinsegae-inc.com/api/v1/agent/chat
LLM_CLIENT_ID=<발급받은 client_id>
LLM_CLIENT_SECRET=<발급받은 client_secret>
LLM_AGENT_ID=b6958377-73f2-4234-a49c-2aa878350a2e
LLM_AGENT_CODE=playground
```

### 1-3. 이미지 빌드 + 내보내기

**Linux/macOS:**
```bash
bash scripts/export-images.sh v1.0
# → pipeline-images-v1.0.tar.gz
```

**Windows PowerShell:**
```powershell
powershell -ExecutionPolicy Bypass -File scripts\export-images.ps1 -Tag v1.0
```

**SMAgentLab 이미지도 별도 빌드** (SMAgentLab 가이드 참고):
```bash
cd ../SMAgentLab
bash scripts/export-images.sh v2.16
# → smagentlab-images-v2.16.tar.gz
```

### 1-4. 폐쇄망 서버로 반입
USB 또는 사내 SCP로 다음 파일/디렉토리를 운영 서버로 전송:
- `pipeline-images-v1.0.tar.gz`, `smagentlab-images-v2.16.tar.gz`
- `pipeline/` 디렉토리 (compose 2개, scripts/, .env)
- `SMAgentLab/` 디렉토리 (compose 2개, scripts/, init/, **backend/**, .env)

---

## 2. 폐쇄망 서버에서 배포

### 2-1. 배포 디렉토리 구성
```bash
sudo mkdir -p /opt/pipeline /opt/smagentlab
sudo chown -R $USER:$USER /opt/pipeline /opt/smagentlab

# 반입한 파일들 배치
cp -r SMAgentLab/* /opt/smagentlab/
cp -r pipeline/* /opt/pipeline/
mv smagentlab-images-v2.16.tar.gz /opt/smagentlab/
mv pipeline-images-v1.0.tar.gz /opt/pipeline/
```

### 2-2. SMAgentLab 먼저 기동 (배포 대상)
```bash
cd /opt/smagentlab
chmod +x scripts/*.sh
bash scripts/import-and-run.sh smagentlab-images-v2.16.tar.gz
```

### 2-3. pipeline 기동
```bash
cd /opt/pipeline
chmod +x scripts/*.sh
bash scripts/import-and-run.sh pipeline-images-v1.0.tar.gz
```

> `import-and-run.sh`는 SMAgentLab 컨테이너가 이미 떠 있으면 스킵하고, pipeline만 prod 모드로 기동한다.

### 2-4. 접속

| 서비스 | URL |
|---|---|
| pipeline 포탈 UI | `http://<서버IP>:3000` |
| pipeline API | `http://<서버IP>:8080/docs` |
| SMAgentLab 웹 | `http://<서버IP>:8501` |
| SMAgentLab API | `http://<서버IP>:8000/docs` |

방화벽: 외부 노출은 3000, 8501만. 8080, 8000은 사내망 전용 권장.

### 2-5. 초기 관리자 작업
1. `http://<서버IP>:3000` 접속 → admin / `ADMIN_DEFAULT_PASSWORD` 로그인
2. 설정 → 비밀번호 변경 (LLM은 시스템 단일 자격증명 — `.env`의 `LLM_CLIENT_ID/SECRET`이면 충분, 사용자별 등록 불필요)
3. 팀원 회원가입 안내 (`GIT_CLONE_URL` 함께 전달)

---

## 3. 버전 업데이트 (재배포)

### 3-1. 빌드 PC
```bash
cd pipeline
git pull origin main
bash scripts/export-images.sh v1.1   # 새 태그
```

### 3-2. 폐쇄망 서버
```bash
cd /opt/pipeline
# 새 tar.gz 반입 + .env의 IMAGE_TAG=v1.1로 갱신
bash scripts/update-images.sh pipeline-images-v1.1.tar.gz
# → DB 백업 자동 제안 (y) → 새 이미지 로드 → backend/frontend 재생성
```

### 3-3. 롤백
`.env`의 `IMAGE_TAG`를 이전 값으로 되돌리고 재기동만 하면 즉시 롤백 (이전 이미지가 서버에 남아있을 때):
```bash
# .env: IMAGE_TAG=v1.0 으로 되돌리기
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --force-recreate backend frontend
```

> 이전 이미지를 정리했다면 백업 tar.gz를 다시 `docker load` 해야 한다. 직전 버전 1개는 유지 권장.

---

## 4. 운영 작업

### 4-1. DB 백업 (SQLite)
```bash
cd /opt/pipeline
bash scripts/backup-db.sh
# → backups/pipeline-audit-20260508-153012.db.gz
```

자동 일일 백업 (cron):
```cron
0 3 * * * cd /opt/pipeline && bash scripts/backup-db.sh >> /var/log/pipeline-backup.log 2>&1
```

### 4-2. DB 복원
```bash
bash scripts/restore-db.sh backups/pipeline-audit-20260508-153012.db.gz
# 자동으로 backend stop → 복원 → backend up
```

### 4-3. 로그 확인
```bash
COMPOSE="-f docker-compose.yml -f docker-compose.prod.yml"
docker compose $COMPOSE logs -f backend
docker compose $COMPOSE logs --tail=200 backend
docker compose $COMPOSE ps
```

### 4-4. 서비스 제어
```bash
COMPOSE="-f docker-compose.yml -f docker-compose.prod.yml"
docker compose $COMPOSE stop          # 중지 (데이터 유지)
docker compose $COMPOSE start
docker compose $COMPOSE restart backend
docker compose $COMPOSE down          # 컨테이너 제거 (볼륨 유지)
docker compose $COMPOSE down -v       # 볼륨까지 삭제 (데이터 손실)
```

---

## 5. 트러블슈팅

| 증상 | 원인 | 해결 |
|---|---|---|
| `docker load` 실패 (no space left) | 디스크 부족 | `df -h`, `docker image prune -a` |
| pipeline backend 기동 실패 — DB 오류 | db-data 볼륨 권한 | `docker volume inspect`, 권한 확인 |
| pipeline `/deploy` 시 SMAgentLab 코드 갱신 안 됨 | SMAgentLab을 prod.yml만으로 띄움 (마운트 없음) | `DEPLOY_COMPOSE_OVERRIDES=docker-compose.prod.yml,docker-compose.dev.yml` 로 dev.yml 함께 적용 |
| pipeline `/deploy` 시 frontend 변경 미반영 | base에 frontend 마운트 없음 | frontend 변경은 이미지 재빌드/재배포 필요 — pipeline의 자동 배포 대상 아님 |
| `pull_policy: never`로 이미지 못 찾음 | 빌드 PC와 서버 태그 불일치 | `.env`의 `IMAGE_TAG`가 반입한 이미지 태그와 정확히 일치하는지 확인 |
| 이미지 아키텍처 불일치 | 빌드 PC와 서버 아키텍처 다름 | 같은 아키텍처로 통일 또는 `docker buildx --platform linux/amd64` |
| 포트 충돌 (3000/8080 vs 8501/8000) | 다른 서비스 사용 중 | `.env`의 `PORTAL_PORT`/`FRONTEND_PORT` 변경 |

---

## 6. 보안 점검

| 항목 | 확인 |
|---|---|
| `JWT_SECRET_KEY`, `FERNET_SECRET_KEY` | 기본값(`change-this-...`) 금지, 32바이트 랜덤 |
| `ADMIN_DEFAULT_PASSWORD` | 첫 로그인 후 어드민 UI에서 변경 |
| `.env` 파일 권한 | `chmod 600 .env` |
| 백업 디렉토리 | `chmod 700 backups`, 별도 보안 디스크에 주기 백업 |
| Docker 데몬 권한 | `docker` 그룹 가입자는 사실상 root. 운영자 외 가입 금지 |
| 외부 노출 포트 | pipeline은 3000(UI)만 외부, 8080(API)는 사내망 전용 |
| pipeline의 docker.sock 마운트 | pipeline backend가 호스트 docker를 제어함 — 리포 보안 강화 필수 |

---

## 7. 폐쇄망 운영 체크리스트 (요약)

**최초 배포:**
- [ ] 빌드 PC에서 `bash scripts/export-images.sh v1.0` 실행
- [ ] SMAgentLab 이미지도 빌드: `bash ../SMAgentLab/scripts/export-images.sh v2.16`
- [ ] `.env`의 시크릿 키들 운영용으로 새로 생성
- [ ] tar.gz + 설정 파일들 + SMAgentLab의 `backend/` 디렉토리 서버 반입
- [ ] `/opt/smagentlab`, `/opt/pipeline` 구성
- [ ] SMAgentLab → pipeline 순서로 `import-and-run.sh` 실행
- [ ] `http://<서버IP>:3000` 접속 확인
- [ ] admin 로그인 → 비밀번호 변경 (LLM은 .env의 `LLM_CLIENT_ID/SECRET`으로 시스템 단일 호출)
- [ ] cron에 일일 백업 등록

**버전 업데이트:**
- [ ] 빌드 PC에서 `IMAGE_TAG`를 새 버전으로 갱신 후 export
- [ ] 서버 `.env`의 `IMAGE_TAG` 갱신
- [ ] `bash scripts/update-images.sh ...` 실행 (백업 자동 제안 → yes)
- [ ] 헬스체크 통과 후 `docker image prune -f` 로 이전 이미지 정리
