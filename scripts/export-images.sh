#!/bin/bash
# ============================================================
# Agentic Deployment Portal 이미지 빌드 + 내보내기 (Linux/macOS)
#
# 사용법:
#   cd pipeline
#   bash scripts/export-images.sh [태그]
#
#   예) bash scripts/export-images.sh v1.0
#       → pipeline-images-v1.0.tar.gz
#
# 인자 미지정 시 .env의 IMAGE_TAG 또는 latest 사용.
# SMAgentLab 이미지는 SMAgentLab 리포에서 별도 빌드:
#   bash ../SMAgentLab/scripts/export-images.sh v2.16
# ============================================================
set -e

TAG=${1:-}

# .env에서 IMAGE_TAG 읽기 (인자 미지정 시)
if [ -z "${TAG}" ] && [ -f ".env" ]; then
  TAG=$(grep -E "^IMAGE_TAG=" .env | cut -d= -f2 | tr -d '"' | tr -d "'")
fi
TAG=${TAG:-latest}

EXPORT_FILE="pipeline-images-${TAG}.tar.gz"
BACKEND_IMG="pipeline-backend:${TAG}"
FRONTEND_IMG="pipeline-frontend:${TAG}"

echo "=========================================="
echo " Pipeline 이미지 빌드 + 내보내기"
echo " 태그: ${TAG}"
echo "=========================================="

# ─── 1. 빌드 ───
echo ""
echo "[1/3] Pipeline 이미지 빌드 중..."
IMAGE_TAG="${TAG}" docker compose build --no-cache

# 빌드 결과는 base compose 정의상 pipeline-backend:latest, pipeline-frontend:latest로 떨어짐
# → 명시 태그로 다시 tag 부여
if [ "${TAG}" != "latest" ]; then
  docker tag pipeline-backend:latest "${BACKEND_IMG}"
  docker tag pipeline-frontend:latest "${FRONTEND_IMG}"
fi

# ─── 2. 외부 의존 이미지 (네트워크 가능할 때만) ───
echo ""
echo "[2/3] 의존 이미지 pull (실패 무시)..."
docker pull node:20-alpine 2>/dev/null || true
docker pull nginx:alpine 2>/dev/null || true

# ─── 3. 내보내기 ───
echo ""
echo "[3/3] 이미지 내보내기 → ${EXPORT_FILE}"
IMAGES=(
  "${BACKEND_IMG}"
  "${FRONTEND_IMG}"
  node:20-alpine
  nginx:alpine
)

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

SIZE=$(du -h "${EXPORT_FILE}" | cut -f1)
echo ""
echo "완료!"
echo "  파일: ${EXPORT_FILE}"
echo "  크기: ${SIZE}"
echo ""
echo "다음 단계:"
echo "  1) ${EXPORT_FILE} 를 폐쇄망 서버로 전송"
echo "  2) docker-compose.yml, docker-compose.prod.yml, scripts/, .env 도 함께 전송"
echo "  3) 서버에서: bash scripts/import-and-run.sh ${EXPORT_FILE}"
