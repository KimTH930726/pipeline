#!/bin/bash
# ============================================================
# Pipeline DB 복원 (SQLite)
#
# 주의: 복원은 기존 audit.db를 덮어씁니다.
#
# 사용법:
#   bash scripts/restore-db.sh <백업파일.db.gz>
# ============================================================
set -e

BACKUP_FILE=${1:-}

if [ -z "${BACKUP_FILE}" ] || [ ! -f "${BACKUP_FILE}" ]; then
  echo "사용법: bash scripts/restore-db.sh <백업파일.db.gz>"
  echo ""
  echo "사용 가능한 백업:"
  ls -lh backups/pipeline-audit-*.db.gz 2>/dev/null || echo "  (backups/ 디렉토리에 백업 없음)"
  exit 1
fi

CONTAINER=$(docker ps --filter "ancestor=pipeline-backend" --format '{{.Names}}' | head -1)
if [ -z "${CONTAINER}" ]; then
  CONTAINER=$(docker ps --format '{{.Names}}' | grep -E '(pipeline.*backend|backend.*pipeline)' | head -1)
fi

if [ -z "${CONTAINER}" ]; then
  echo "오류: pipeline backend 컨테이너를 찾을 수 없습니다."
  exit 1
fi

COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"

echo "=========================================="
echo " Pipeline DB 복원"
echo " 컨테이너: ${CONTAINER}"
echo " 백업파일: ${BACKUP_FILE}"
echo "=========================================="
echo ""
echo "주의: 기존 /data/audit.db 가 덮어씌워집니다."
read -p "계속하시겠습니까? (yes/no): " confirm
if [ "${confirm}" != "yes" ]; then
  echo "취소됨."
  exit 0
fi

echo ""
echo "[1/3] backend 컨테이너 정지 중..."
docker compose ${COMPOSE_FILES} stop backend

echo ""
echo "[2/3] DB 파일 복원 중..."
# db-data 볼륨에 직접 쓰기 위해 helper 컨테이너 사용
gunzip -c "${BACKUP_FILE}" | docker run --rm -i \
  -v "$(docker volume ls --format '{{.Name}}' | grep -E 'db-data' | head -1):/data" \
  alpine:latest sh -c 'cat > /data/audit.db'

echo ""
echo "[3/3] backend 재시작 중..."
docker compose ${COMPOSE_FILES} up -d backend

echo ""
echo "복원 완료."
