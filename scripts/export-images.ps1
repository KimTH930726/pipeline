# ============================================================
# Agentic Deployment Portal 이미지 빌드 + 내보내기 (Windows PowerShell)
#
# 사용법:
#   cd D:\personalPJT\pipeline
#   powershell -ExecutionPolicy Bypass -File scripts\export-images.ps1 [-Tag v1.0]
#
# 결과물: pipeline-images-{태그}.tar.gz
# ============================================================
param(
    [string]$Tag = ""
)

$ErrorActionPreference = "Stop"

# .env에서 IMAGE_TAG 읽기 (인자 미지정 시)
if ([string]::IsNullOrEmpty($Tag) -and (Test-Path ".env")) {
    $envLine = Get-Content ".env" | Where-Object { $_ -match "^IMAGE_TAG=" } | Select-Object -First 1
    if ($envLine) {
        $Tag = ($envLine -split "=", 2)[1].Trim('"').Trim("'")
    }
}
if ([string]::IsNullOrEmpty($Tag)) { $Tag = "latest" }

$ExportFile  = "pipeline-images-$Tag.tar.gz"
$BackendImg  = "pipeline-backend:$Tag"
$FrontendImg = "pipeline-frontend:$Tag"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " Pipeline 이미지 빌드 + 내보내기" -ForegroundColor Cyan
Write-Host " 태그: $Tag" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 1. 빌드 (IMAGE_TAG 환경변수로 주입)
Write-Host "`n[1/3] 이미지 빌드 중..." -ForegroundColor Yellow
$env:IMAGE_TAG = $Tag
docker compose build --no-cache
if ($LASTEXITCODE -ne 0) { throw "빌드 실패" }

# base compose는 pipeline-backend:latest로 빌드되므로 명시 태그로 재태그
if ($Tag -ne "latest") {
    docker tag pipeline-backend:latest $BackendImg
    docker tag pipeline-frontend:latest $FrontendImg
}

# 2. 외부 의존 이미지 (실패 무시)
Write-Host "`n[2/3] 의존 이미지 pull (실패 무시)..." -ForegroundColor Yellow
docker pull node:20-alpine 2>$null
docker pull nginx:alpine 2>$null

# 3. tar로 저장 + gzip 압축
Write-Host "`n[3/3] 이미지 내보내기 → $ExportFile" -ForegroundColor Yellow
$Images = @($BackendImg, $FrontendImg, "node:20-alpine", "nginx:alpine")
$Existing = @()
foreach ($img in $Images) {
    docker image inspect $img > $null 2>&1
    if ($LASTEXITCODE -eq 0) {
        $Existing += $img
    } else {
        Write-Host "  [스킵] $img (로컬에 없음)" -ForegroundColor DarkGray
    }
}
Write-Host "  내보내는 이미지: $($Existing.Count)개"

$TempTar = "pipeline-images-$Tag.tar"
docker save -o $TempTar @Existing
if ($LASTEXITCODE -ne 0) { throw "docker save 실패" }

# PowerShell 5.1 호환 gzip 압축
$inStream  = [IO.File]::OpenRead($TempTar)
$outStream = [IO.File]::Create($ExportFile)
$gzip      = New-Object IO.Compression.GZipStream($outStream, [IO.Compression.CompressionMode]::Compress)
$inStream.CopyTo($gzip)
$gzip.Close(); $outStream.Close(); $inStream.Close()
Remove-Item $TempTar

# 결과
$SizeMB = [math]::Round((Get-Item $ExportFile).Length / 1MB, 1)
Write-Host "`n완료!" -ForegroundColor Green
Write-Host "  파일: $ExportFile"
Write-Host "  크기: ${SizeMB} MB"
Write-Host "`n다음 단계:" -ForegroundColor Cyan
Write-Host "  1) $ExportFile 를 폐쇄망 서버로 전송"
Write-Host "  2) docker-compose.yml, docker-compose.prod.yml, scripts/, .env 도 함께 전송"
Write-Host "  3) 서버에서: bash scripts/import-and-run.sh $ExportFile"
