#!/bin/bash
# ============================================================
# Agentic Deployment Portal 폐쇄망 자동 배포
#
# 사전 조건:
#   - Docker + Docker Compose 설치됨
#   - pipeline-images-<tag>.tar.gz 반입됨
#   - SMAgentLab 소스 디렉토리 반입됨 (backend/ 포함)
#   - SMAgentLab 이미지 묶음(smagentlab-images-*.tar.gz)도 별도 반입 (선택)
#   - .env 작성됨 (IMAGE_TAG 명시 권장)
#
# 사용법:
#   cd /opt/pipeline
#   bash scripts/import-and-run.sh [pipeline-images-<tag>.tar.gz] [옵션]
#
# 옵션:
#   --project-path <경로>      SMAgentLab 소스 경로 (기본: ../SMAgentLab)
#   --repo-path <경로>         bare repo 경로 (기본: /srv/repos/SMAgentLab.git)
#   --server-ip <IP>           서버 IP (기본: 자동 감지)
#   --ssh-user <유저>          SSH 사용자명 (기본: 현재 사용자)
#   --smagent-images <파일>    SMAgentLab 이미지 tar.gz (반입 시 함께 로드)
# ============================================================
set -e

# === 기본값 ===
IMPORT_FILE=""
PROJECT_PATH="../SMAgentLab"
REPO_PATH="/srv/repos/SMAgentLab.git"
SERVER_IP=""
SSH_USER=$(whoami)
SMAGENT_IMAGES=""

# === 인자 파싱 ===
while [[ $# -gt 0 ]]; do
  case $1 in
    --project-path) PROJECT_PATH="$2"; shift 2 ;;
    --repo-path) REPO_PATH="$2"; shift 2 ;;
    --server-ip) SERVER_IP="$2"; shift 2 ;;
    --ssh-user) SSH_USER="$2"; shift 2 ;;
    --smagent-images) SMAGENT_IMAGES="$2"; shift 2 ;;
    *) IMPORT_FILE="$1"; shift ;;
  esac
done

# 첫 인자 미지정 시: 디렉토리에서 pipeline-images-*.tar.gz 자동 탐색
if [ -z "${IMPORT_FILE}" ]; then
  IMPORT_FILE=$(ls -t pipeline-images-*.tar.gz 2>/dev/null | head -1)
fi

# 서버 IP 자동 감지
if [ -z "$SERVER_IP" ]; then
  SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")
fi

# 절대 경로 변환
PROJECT_PATH=$(cd "$PROJECT_PATH" 2>/dev/null && pwd || echo "$PROJECT_PATH")

# IMAGE_TAG 읽기 (.env 또는 latest)
IMAGE_TAG=""
if [ -f ".env" ]; then
  IMAGE_TAG=$(grep -E "^IMAGE_TAG=" .env | cut -d= -f2 | tr -d '"' | tr -d "'")
fi
IMAGE_TAG=${IMAGE_TAG:-latest}

COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"

echo "=========================================="
echo " Agentic Deployment Portal 폐쇄망 자동 배포"
echo "=========================================="
echo "  pipeline 이미지:   ${IMPORT_FILE:-(없음 — 로컬 빌드)}"
echo "  smagent 이미지:    ${SMAGENT_IMAGES:-(없음)}"
echo "  IMAGE_TAG:         ${IMAGE_TAG}"
echo "  SMAgentLab 경로:   ${PROJECT_PATH}"
echo "  bare repo:         ${REPO_PATH}"
echo "  서버 IP:           ${SERVER_IP}"
echo "  SSH 유저:          ${SSH_USER}"
echo "=========================================="

# ─── 1. 이미지 로드 ───
echo ""
echo "[1/6] 이미지 로드 중..."
if [ -n "${IMPORT_FILE}" ] && [ -f "${IMPORT_FILE}" ]; then
  docker load -i "${IMPORT_FILE}"
else
  echo "  pipeline 이미지 파일 없음 — 로컬 빌드 모드"
  IMAGE_TAG="${IMAGE_TAG}" docker compose build
fi

if [ -n "${SMAGENT_IMAGES}" ] && [ -f "${SMAGENT_IMAGES}" ]; then
  echo "  SMAgentLab 이미지도 로드 중..."
  docker load -i "${SMAGENT_IMAGES}"
fi

# ─── 2. bare repo 생성 (없으면) ───
echo ""
echo "[2/6] Git bare repo 확인..."
if [ -d "$REPO_PATH" ]; then
  echo "  이미 존재: $REPO_PATH"
else
  echo "  bare repo 생성 중..."
  mkdir -p "$(dirname "$REPO_PATH")"
  git clone --bare "$PROJECT_PATH" "$REPO_PATH"
  cd "$REPO_PATH"
  git config receive.denyCurrentBranch updateInstead
  cd - > /dev/null
  echo "  생성 완료: $REPO_PATH"
fi

# ─── 3. .env 자동 생성 (없으면) ───
echo ""
echo "[3/6] .env 파일 확인..."
if [ -f ".env" ]; then
  echo "  이미 존재 — 기존 설정 유지"
else
  echo "  .env 파일 자동 생성 중..."

  FERNET_KEY=$(docker run --rm pipeline-backend:${IMAGE_TAG} python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || echo "")
  JWT_KEY=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || echo "change-this-in-production")

  cat > .env << ENVEOF
# ─── 자동 생성됨 ($(date)) ───

# 이미지 태그 (운영 PC와 동일하게 유지)
IMAGE_TAG=${IMAGE_TAG}

# Git 레포 호스트 경로
REPO_HOST_PATH=$REPO_PATH

# 배포 대상 프로젝트 호스트 경로 (호스트 절대 경로 필수)
DEPLOY_TARGET_PATH=$PROJECT_PATH

# 암호화 키 (자동 생성됨 — 변경 시 기존 API Key 복호화 불가)
FERNET_SECRET_KEY=$FERNET_KEY

# JWT 서명 키 (자동 생성됨)
JWT_SECRET_KEY=$JWT_KEY

# 초기 관리자 비밀번호
ADMIN_DEFAULT_PASSWORD=admin1234

# 팀원용 Git clone URL
GIT_CLONE_URL=ssh://$SSH_USER@$SERVER_IP$REPO_PATH

# LLM 설정
LLM_ENDPOINT=https://devx-mcp-api.shinsegae-inc.com/api/v1/mcp-command/chat

# 배포 모드 (restart: 폐쇄망 / build: 인터넷)
DEPLOY_MODE=restart
DEPLOY_SERVICE_NAME=backend frontend

# Docker Compose 프로젝트명 (배포 대상)
DEPLOY_COMPOSE_PROJECT=smagentlab

# 폐쇄망 prod 모드: SMAgentLab에 prod.yml(pull 차단) + dev.yml(소스 마운트) 함께 적용
# - dev.yml: pipeline /deploy 동작이 호스트 ./backend를 컨테이너로 반영하기 위함
DEPLOY_COMPOSE_OVERRIDES=docker-compose.prod.yml,docker-compose.dev.yml

# 샌드박스 호스트 경로
SANDBOX_HOST_PATH=/tmp/pipeline-sandboxes
ENVEOF

  echo "  .env 생성 완료"
  echo "  FERNET_SECRET_KEY: ${FERNET_KEY:0:10}..."
  echo "  JWT_SECRET_KEY: ${JWT_KEY:0:10}..."
fi

# ─── 4. SMAgentLab 서비스 기동 (배포 대상) ───
# prod.yml(외부 pull 차단) + dev.yml(./backend:/app 마운트) 함께 적용.
# pipeline의 /deploy 동작이 호스트 ./backend 갱신 → 컨테이너 마운트 반영
# 구조에 의존하므로 dev.yml의 소스 마운트는 필수.
echo ""
echo "[4/6] SMAgentLab 서비스 확인..."
SMAGENT_COMPOSE_ARGS="-f $PROJECT_PATH/docker-compose.yml"
[ -f "$PROJECT_PATH/docker-compose.prod.yml" ] && SMAGENT_COMPOSE_ARGS="$SMAGENT_COMPOSE_ARGS -f $PROJECT_PATH/docker-compose.prod.yml"
[ -f "$PROJECT_PATH/docker-compose.dev.yml" ]  && SMAGENT_COMPOSE_ARGS="$SMAGENT_COMPOSE_ARGS -f $PROJECT_PATH/docker-compose.dev.yml"

if [ -f "$PROJECT_PATH/docker-compose.yml" ]; then
  RUNNING=$(docker compose ${SMAGENT_COMPOSE_ARGS} -p smagentlab ps -q 2>/dev/null | wc -l)
  if [ "$RUNNING" -eq 0 ]; then
    echo "  SMAgentLab 서비스 기동 중..."
    echo "  compose: ${SMAGENT_COMPOSE_ARGS}"
    docker compose ${SMAGENT_COMPOSE_ARGS} -p smagentlab up -d --no-build
  else
    echo "  이미 실행 중 ($RUNNING개 컨테이너)"
  fi
else
  echo "  [경고] $PROJECT_PATH/docker-compose.yml 없음 — SMAgentLab 별도 기동 필요"
fi

# ─── 5. Pipeline 포탈 시작 ───
echo ""
echo "[5/6] Pipeline 포탈 시작 중 (prod 모드)..."
docker compose ${COMPOSE_FILES} up -d --no-build

# ─── 6. 상태 확인 (헬스체크 폴링 120초) ───
echo ""
echo "[6/6] 기동 확인 중..."
docker compose ${COMPOSE_FILES} ps

PORTAL_PORT=$(grep PORTAL_PORT .env 2>/dev/null | cut -d= -f2 || echo "8080")
PORTAL_PORT=${PORTAL_PORT:-8080}
FRONTEND_PORT=$(grep FRONTEND_PORT .env 2>/dev/null | cut -d= -f2 || echo "3000")
FRONTEND_PORT=${FRONTEND_PORT:-3000}

for i in $(seq 1 60); do
  if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$PORTAL_PORT/api/health" 2>/dev/null | grep -q "200"; then
    echo ""
    echo "=========================================="
    echo " 배포 완료!"
    echo ""
    echo "  포탈:        http://$SERVER_IP:$FRONTEND_PORT"
    echo "  백엔드 API:  http://$SERVER_IP:$PORTAL_PORT"
    echo "  초기 관리자:  admin / admin1234"
    echo ""
    echo "  Git clone:   ssh://$SSH_USER@$SERVER_IP$REPO_PATH"
    echo ""
    echo "  다음 단계:"
    echo "    1. 브라우저에서 http://$SERVER_IP:$FRONTEND_PORT 접속"
    echo "    2. admin / admin1234 로그인"
    echo "    3. 설정 → 비밀번호 변경 + LLM API Key 등록"
    echo "    4. 팀원에게 회원가입 안내"
    echo "=========================================="
    exit 0
  fi
  sleep 2
  printf "."
done

echo ""
echo "[경고] 120초 내 응답 없음."
echo "  docker compose ${COMPOSE_FILES} logs backend 로 확인하세요."
