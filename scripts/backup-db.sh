#!/bin/bash
# ============================================================
# Pipeline DB 백업 (SQLite)
#
# pipeline의 audit.db를 컨테이너 내부에서 sqlite3 .backup으로 일관성 있게
# 복사한 뒤 호스트 backups/ 디렉토리에 gzip으로 압축 저장.
#
# 사용법:
#   bash scripts/backup-db.sh [출력파일명]
#
#   예) bash scripts/backup-db.sh
#       → backups/pipeline-audit-20260508-153012.db.gz
# ============================================================
set -e

BACKUP_DIR="backups"
mkdir -p "${BACKUP_DIR}"

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
DEFAULT_FILE="${BACKUP_DIR}/pipeline-audit-${TIMESTAMP}.db.gz"
OUTPUT_FILE=${1:-${DEFAULT_FILE}}

# pipeline backend 컨테이너 식별 (compose 프로젝트명 = pipeline 또는 폴더명)
CONTAINER=$(docker ps --filter "ancestor=pipeline-backend" --format '{{.Names}}' | head -1)
if [ -z "${CONTAINER}" ]; then
  # ancestor 매칭 안 되면 latest 태그까지 체크
  CONTAINER=$(docker ps --format '{{.Names}}' | grep -E '(pipeline.*backend|backend.*pipeline)' | head -1)
fi

if [ -z "${CONTAINER}" ]; then
  echo "오류: pipeline backend 컨테이너를 찾을 수 없습니다."
  echo "      docker ps 로 확인하세요."
  exit 1
fi

echo "=========================================="
echo " Pipeline DB 백업"
echo " 컨테이너: ${CONTAINER}"
echo " 출력:     ${OUTPUT_FILE}"
echo "=========================================="

echo ""
echo "백업 진행 중..."

# 컨테이너 내부에서 sqlite3 .backup 실행 (일관성 보장)
# audit.db 경로는 /data/audit.db (db-data 볼륨)
docker exec "${CONTAINER}" sh -c '
  if command -v sqlite3 > /dev/null 2>&1; then
    sqlite3 /data/audit.db ".backup /tmp/audit-backup.db" && cat /tmp/audit-backup.db && rm -f /tmp/audit-backup.db
  else
    # sqlite3 미설치 시 단순 복사 (쓰기 잠깐 멈출 위험 있음)
    cat /data/audit.db
  fi
' | gzip > "${OUTPUT_FILE}"

SIZE=$(du -h "${OUTPUT_FILE}" | cut -f1)
echo ""
echo "완료: ${OUTPUT_FILE} (${SIZE})"
echo ""
echo "복원: bash scripts/restore-db.sh ${OUTPUT_FILE}"
