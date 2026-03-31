#!/bin/bash
# ============================================================
# Agentic Deployment 폐쇄망 배포 (폐쇄망 서버에서 실행)
#
# 사전 조건:
#   - Docker + Docker Compose 설치됨
#   - pipeline-images.tar.gz 전달됨
#   - pipeline 소스 코드 전달됨
#   - .env 파일 생성됨 (FERNET_SECRET_KEY 등)
#
# 사용법:
#   cd pipeline
#   bash scripts/import-and-run.sh
# ============================================================
set -e

IMPORT_FILE=${1:-pipeline-images.tar.gz}

if [ ! -f "${IMPORT_FILE}" ]; then
  echo "오류: ${IMPORT_FILE} 파일을 찾을 수 없습니다."
  exit 1
fi

echo "=========================================="
echo " Agentic Deployment 폐쇄망 배포"
echo "=========================================="

# 1. 이미지 로드
echo ""
echo "[1/4] 이미지 로드 중..."
docker load -i "${IMPORT_FILE}"

# 2. .env 확인
echo ""
if [ ! -f ".env" ]; then
  echo "[주의] .env 파일이 없습니다."
  echo "  cp backend/.env.example .env 후 값을 채워주세요."
  echo "  필수: FERNET_SECRET_KEY, JWT_SECRET_KEY"
  exit 1
fi
echo "[확인] .env 파일 감지됨"

# 3. 서비스 시작
echo ""
echo "[2/4] 서비스 시작 중..."
docker compose up -d

# 4. 상태 확인
echo ""
echo "[3/4] 서비스 상태"
docker compose ps

echo ""
echo "[4/4] 기동 확인 중..."
for i in $(seq 1 30); do
  if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/health 2>/dev/null | grep -q "200"; then
    echo ""
    echo "=========================================="
    echo " 배포 완료!"
    echo "  포탈:      http://localhost:3000"
    echo "  백엔드:    http://localhost:8080"
    echo "  초기 관리자: admin / admin1234"
    echo "=========================================="
    exit 0
  fi
  sleep 2
  printf "."
done

echo ""
echo "[경고] 60초 내 응답 없음. docker compose logs backend 확인"
