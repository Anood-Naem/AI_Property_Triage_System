param(
    [string]$RepoRoot = (Get-Location).Path,
    [switch]$StartN8N = $true,
    [switch]$SkipWebUI = $false
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot

Write-Host "[1/7] Preparing env files..."
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}
if (-not (Test-Path "webui/.env") -and (Test-Path "webui/.env.example")) {
    Copy-Item "webui/.env.example" "webui/.env"
}

Write-Host "[2/7] Downloading trained image model release..."
$ckptDir = "services/image_analyser_service/checkpoints"
$zipPath = Join-Path $ckptDir "property_room_model.zip"
$ptPath = Join-Path $ckptDir "property_room_model.pt"
New-Item -ItemType Directory -Force -Path $ckptDir | Out-Null
if (-not (Test-Path $ptPath)) {
    Invoke-WebRequest -Uri "https://github.com/Anood-Naem/AI_Property_Triage_System/releases/download/image-model-v1/property_room_model.zip" -OutFile $zipPath
    Expand-Archive -Path $zipPath -DestinationPath $ckptDir -Force
    Remove-Item $zipPath -Force
}

Write-Host "[3/7] Starting backend services (8001-8004)..."
docker compose -f docker-compose.backend.yml up --build -d

Write-Host "[4/7] Populating RAG vector DB..."
docker compose -f docker-compose.backend.yml exec rag_service python populate_chroma.py

if ($StartN8N) {
    Write-Host "[5/7] Starting n8n on :5678 if not running..."
    $existing = docker ps -a --format "{{.Names}}" | Select-String -SimpleMatch "n8n"
    if (-not $existing) {
        docker run -d --name n8n -p 5678:5678 n8nio/n8n:latest | Out-Null
    } else {
        docker start n8n | Out-Null
    }
    Write-Host "Import workflow in n8n once: n8n_workflows/ai_property_triage_workflow.json"
}

if (-not $SkipWebUI) {
    Write-Host "[6/7] Installing WebUI dependencies..."
    python -m pip install -r webui/requirements.txt

    Write-Host "[7/7] Starting WebUI..."
    Set-Location "webui"
    streamlit run app.py
} else {
    Write-Host "[6/7] WebUI skipped."
    Write-Host "Run manually: cd webui; streamlit run app.py"
}
