#!/bin/bash
# ============================================================
# Agentic Deployment 포탈 이미지 내보내기 (인터넷 PC에서 실행)
#
# 사용법:
#   cd pipeline
#   bash scripts/export-images.sh
#
# 결과물: pipeline-images.tar.gz
# USB/SCP로 폐쇄망 서버에 전달
# ============================================================
set -e

EXPORT_FILE="pipeline-images.tar.gz"

echo "=========================================="
echo " Agentic Deployment 이미지 빌드 + 내보내기"
echo "=========================================="

SMAGENT_PATH="${SMAGENT_PATH:-../SMAgentLab}"

echo ""
echo "[1/4] Pipeline 이미지 빌드 중..."
docker compose build --no-cache

echo ""
echo "[2/4] SMAgentLab 이미지 빌드 중..."
if [ -f "$SMAGENT_PATH/docker-compose.yml" ]; then
  docker compose -f "$SMAGENT_PATH/docker-compose.yml" build --no-cache
else
  echo "  [경고] $SMAGENT_PATH/docker-compose.yml 없음 — SMAgentLab 이미지는 별도 빌드 필요"
fi

echo ""
echo "[3/4] 의존 이미지 pull..."
docker pull node:20-alpine 2>/dev/null || true
docker pull nginx:alpine 2>/dev/null || true
docker pull pgvector/pgvector:pg16 2>/dev/null || true
docker pull redis:7-alpine 2>/dev/null || true

echo ""
echo "[4/4] 이미지 내보내기 → ${EXPORT_FILE}"
IMAGES=(
  pipeline-backend:latest
  pipeline-frontend:latest
  smagentlab-backend:latest
  smagentlab-frontend:latest
  node:20-alpine
  nginx:alpine
  pgvector/pgvector:pg16
  redis:7-alpine
)
# 존재하는 이미지만 내보내기
EXISTING_IMAGES=()
for img in "${IMAGES[@]}"; do
  if docker image inspect "$img" > /dev/null 2>&1; then
    EXISTING_IMAGES+=("$img")
  else
    echo "  [스킵] $img (로컬에 없음)"
  fi
done
echo "  내보내는 이미지: ${#EXISTING_IMAGES[@]}개"
docker save "${EXISTING_IMAGES[@]}" | gzip > "${EXPORT_FILE}"

echo ""
echo "완료!"
SIZE=$(du -h "${EXPORT_FILE}" | cut -f1)
echo "  파일: ${EXPORT_FILE}"
echo "  크기: ${SIZE}"
echo ""
echo "폐쇄망 서버에 전달 후:"
echo "  bash scripts/import-and-run.sh"
