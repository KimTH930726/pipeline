#!/bin/bash
# ============================================================
# Agentic Deployment 폐쇄망 자동 배포
#
# 사전 조건:
#   - Docker + Docker Compose 설치됨
#   - pipeline-images.tar.gz 전달됨
#   - SMAgentLab 소스 코드 전달됨
#
# 사용법:
#   cd pipeline
#   bash scripts/import-and-run.sh [옵션]
#
# 옵션:
#   --images <파일>       이미지 tar 파일 (기본: pipeline-images.tar.gz)
#   --project-path <경로> SMAgentLab 소스 경로 (기본: ../SMAgentLab)
#   --repo-path <경로>    bare repo 경로 (기본: /srv/repos/SMAgentLab.git)
#   --server-ip <IP>      서버 IP (기본: 자동 감지)
#   --ssh-user <유저>     SSH 사용자명 (기본: 현재 사용자)
# ============================================================
set -e

# === 기본값 ===
IMPORT_FILE="pipeline-images.tar.gz"
PROJECT_PATH="../SMAgentLab"
REPO_PATH="/srv/repos/SMAgentLab.git"
SERVER_IP=""
SSH_USER=$(whoami)

# === 인자 파싱 ===
while [[ $# -gt 0 ]]; do
  case $1 in
    --images) IMPORT_FILE="$2"; shift 2 ;;
    --project-path) PROJECT_PATH="$2"; shift 2 ;;
    --repo-path) REPO_PATH="$2"; shift 2 ;;
    --server-ip) SERVER_IP="$2"; shift 2 ;;
    --ssh-user) SSH_USER="$2"; shift 2 ;;
    *) IMPORT_FILE="$1"; shift ;;
  esac
done

# 서버 IP 자동 감지
if [ -z "$SERVER_IP" ]; then
  SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")
fi

# 절대 경로 변환
PROJECT_PATH=$(cd "$PROJECT_PATH" 2>/dev/null && pwd || echo "$PROJECT_PATH")

echo "=========================================="
echo " Agentic Deployment 폐쇄망 자동 배포"
echo "=========================================="
echo "  이미지:       $IMPORT_FILE"
echo "  프로젝트 경로: $PROJECT_PATH"
echo "  bare repo:    $REPO_PATH"
echo "  서버 IP:      $SERVER_IP"
echo "  SSH 유저:     $SSH_USER"
echo "=========================================="

# ─── 1. 이미지 로드 ───
echo ""
echo "[1/5] 이미지 로드 중..."
if [ -f "$IMPORT_FILE" ]; then
  docker load -i "$IMPORT_FILE"
else
  echo "  이미지 파일 없음 — 로컬 빌드 모드"
  docker compose build
fi

# ─── 2. bare repo 생성 (없으면) ───
echo ""
echo "[2/5] Git bare repo 확인..."
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
echo "[3/5] .env 파일 확인..."
if [ -f ".env" ]; then
  echo "  이미 존재 — 기존 설정 유지"
else
  echo "  .env 파일 자동 생성 중..."

  # FERNET_SECRET_KEY 자동 생성
  FERNET_KEY=$(docker run --rm python:3.11-slim python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || echo "")

  # JWT_SECRET_KEY 자동 생성
  JWT_KEY=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || echo "change-this-in-production")

  cat > .env << ENVEOF
# ─── 자동 생성됨 ($(date)) ───

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
ENVEOF

  echo "  .env 생성 완료"
  echo "  FERNET_SECRET_KEY: ${FERNET_KEY:0:10}..."
  echo "  JWT_SECRET_KEY: ${JWT_KEY:0:10}..."
fi

# ─── 4. 서비스 시작 ───
echo ""
echo "[4/5] 서비스 시작 중..."
docker compose up -d

# ─── 5. 상태 확인 ───
echo ""
echo "[5/5] 기동 확인 중..."
docker compose ps

PORTAL_PORT=$(grep PORTAL_PORT .env 2>/dev/null | cut -d= -f2 || echo "8080")
PORTAL_PORT=${PORTAL_PORT:-8080}
FRONTEND_PORT=$(grep FRONTEND_PORT .env 2>/dev/null | cut -d= -f2 || echo "3000")
FRONTEND_PORT=${FRONTEND_PORT:-3000}

for i in $(seq 1 30); do
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
echo "[경고] 60초 내 응답 없음."
echo "  docker compose logs backend 로 확인하세요."
