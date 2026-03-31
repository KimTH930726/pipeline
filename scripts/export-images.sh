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

echo ""
echo "[1/3] 이미지 빌드 중..."
docker compose build --no-cache

echo ""
echo "[2/3] 이미지 내보내기 → ${EXPORT_FILE}"
docker save \
  pipeline-backend:latest \
  pipeline-frontend:latest \
| gzip > "${EXPORT_FILE}"

echo ""
echo "[3/3] 완료!"
SIZE=$(du -h "${EXPORT_FILE}" | cut -f1)
echo "  파일: ${EXPORT_FILE}"
echo "  크기: ${SIZE}"
echo ""
echo "폐쇄망 서버에 전달 후:"
echo "  bash scripts/import-and-run.sh"
