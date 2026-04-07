# Autojobcard deploy script for Windows PowerShell
# Usage: .\deploy\deploy.ps1

$ErrorActionPreference = "Stop"

$SERVER_IP = "45.152.66.70"
$SERVER_USER = "root"
$SSH_PORT = "9296"
$REMOTE_DIR = "/opt/autojobcard"

$SSH_ARGS = @("-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10", "-p", $SSH_PORT)
$SCP_ARGS = @("-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10", "-P", $SSH_PORT)

Write-Host "=========================================="
Write-Host "  Deploy to server: $SERVER_USER@${SERVER_IP}:${SSH_PORT}"
Write-Host "=========================================="

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = Split-Path -Parent $SCRIPT_DIR
Set-Location $PROJECT_ROOT

Write-Host ""
Write-Host "[1/6] Checking SSH connection..."
& ssh @SSH_ARGS "${SERVER_USER}@${SERVER_IP}" "echo OK"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Cannot connect to server"
    exit 1
}
Write-Host "  OK"

Write-Host ""
Write-Host "[2/6] Creating remote directory..."
& ssh @SSH_ARGS "${SERVER_USER}@${SERVER_IP}" "mkdir -p $REMOTE_DIR"

Write-Host ""
Write-Host "[3/6] Uploading files (tar+scp)..."
$PKG = Join-Path $env:TEMP "autojobcard_deploy_$(Get-Random).tgz"
$tarArgs = @("-czf", $PKG, "--exclude=node_modules", "--exclude=backend/venv", "--exclude=backend/__pycache__", "--exclude=.git", "--exclude=frontend/dist", "--exclude=.env", "-C", $PROJECT_ROOT, ".")
& tar @tarArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] tar failed"
    exit 1
}

& scp @SCP_ARGS $PKG "${SERVER_USER}@${SERVER_IP}:${REMOTE_DIR}/.deploy_package.tgz"
if ($LASTEXITCODE -ne 0) {
    Remove-Item $PKG -ErrorAction SilentlyContinue
    Write-Host "[ERROR] scp failed"
    exit 1
}

$extractCmd = "cd $REMOTE_DIR; tar -xzf .deploy_package.tgz; rm -f .deploy_package.tgz"
& ssh @SSH_ARGS "${SERVER_USER}@${SERVER_IP}" $extractCmd
Remove-Item $PKG -ErrorAction SilentlyContinue

if (Test-Path "$PROJECT_ROOT/backend/.env") {
    Write-Host "  Uploading .env..."
    & scp @SCP_ARGS "$PROJECT_ROOT/backend/.env" "${SERVER_USER}@${SERVER_IP}:${REMOTE_DIR}/backend/"
}

Write-Host ""
Write-Host "[4/6] Stopping old containers and cleaning Docker images..."
$cleanupCmd = "cd $REMOTE_DIR; if docker compose version >/dev/null 2>&1; then echo '[remote] docker compose down + prune'; docker compose down --remove-orphans || true; docker image prune -af || true; docker builder prune -af || true; elif command -v docker-compose >/dev/null 2>&1; then echo '[remote] docker-compose down + prune'; docker-compose down --remove-orphans || true; docker image prune -af || true; docker builder prune -af || true; else echo '[remote][ERROR] docker compose not found'; exit 1; fi"
& ssh @SSH_ARGS "${SERVER_USER}@${SERVER_IP}" $cleanupCmd

Write-Host ""
Write-Host "[5/6] Building and starting services on server..."
$dockerCmd = "cd $REMOTE_DIR; if docker compose version >/dev/null 2>&1; then docker compose up -d --build; elif command -v docker-compose >/dev/null 2>&1; then docker-compose up -d --build; else echo '[remote][ERROR] docker compose not found'; exit 1; fi"
& ssh @SSH_ARGS "${SERVER_USER}@${SERVER_IP}" $dockerCmd

Write-Host ""
Write-Host "[6/6] Waiting for services..."
Start-Sleep -Seconds 5

Write-Host ""
Write-Host "=========================================="
Write-Host "  Deploy completed!"
Write-Host "=========================================="
Write-Host "  URL: http://$SERVER_IP"
Write-Host "  API docs: http://$SERVER_IP/api/v1/docs"
Write-Host ""
Write-Host "  Useful commands:"
Write-Host "    Logs:    ssh -p $SSH_PORT ${SERVER_USER}@${SERVER_IP} `"cd $REMOTE_DIR; docker compose logs -f`""
Write-Host "    Stop:    ssh -p $SSH_PORT ${SERVER_USER}@${SERVER_IP} `"cd $REMOTE_DIR; docker compose down`""
Write-Host "    Restart: ssh -p $SSH_PORT ${SERVER_USER}@${SERVER_IP} `"cd $REMOTE_DIR; docker compose restart`""
Write-Host ""
