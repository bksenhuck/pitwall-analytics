# Pitwall Analytics - Script de Inicializacao
# Execute este script para rodar o backend e frontend automaticamente

Write-Host "[PITWALL] Inicializando sistema..." -ForegroundColor Cyan
Write-Host ""

# Verificar se esta no diretorio correto
$projectPath = Get-Location
if (-not (Test-Path "main.py")) {
    Write-Host "[ERRO] Diretorio do projeto nao encontrado!" -ForegroundColor Red
    Write-Host "Certifique-se de executar no diretorio raiz da aplicacao." -ForegroundColor Yellow
    pause
    exit 1
}

Set-Location $projectPath

# Verificar se o ambiente virtual existe
$venvPath = ".\venv_pitwall_analytics\Scripts\Activate.ps1"
if (-not (Test-Path $venvPath)) {
    # Tenta tambem no diretorio atual por conveniencia
    $venvPath = ".\venv\Scripts\Activate.ps1"
    if (-not (Test-Path $venvPath)) {
        Write-Host "[ERRO] Ambiente virtual nao encontrado!" -ForegroundColor Red
        Write-Host "Crie o ambiente virtual primeiro (ex: python -m venv venv)" -ForegroundColor Yellow
        pause
        exit 1
    }
}

# Ativar ambiente virtual
Write-Host "[CONFIG] Ativando ambiente virtual..." -ForegroundColor Yellow
& $venvPath

# Verificar se requirements estao instalados
Write-Host "[CONFIG] Verificando dependencias..." -ForegroundColor Yellow
if (-not (Test-Path "requirements.txt")) {
    Write-Host "[AVISO] Arquivo requirements.txt nao encontrado!" -ForegroundColor Yellow
} else {
    Write-Host "Instalando/Atualizando dependencias..." -ForegroundColor Gray
    pip install -r requirements.txt -q
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Iniciar Backend em nova janela
Write-Host "[START] Iniciando Backend (FastAPI)..." -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$projectPath'; & '$projectPath\.\venv_pitwall_analytics\Scripts\Activate.ps1'; Write-Host '[BACKEND] FastAPI rodando...' -ForegroundColor Green; Write-Host 'API: http://127.0.0.1:5000' -ForegroundColor Cyan; Write-Host 'Docs: http://127.0.0.1:5000/docs' -ForegroundColor Cyan; Write-Host ''; python -m backend.app"
)

# Aguardar 3 segundos antes de iniciar o frontend
Start-Sleep -Seconds 3

# Iniciar Frontend em nova janela
Write-Host "[START] Iniciando Frontend (Dash)..." -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$projectPath'; & '$projectPath\.\venv_pitwall_analytics\Scripts\Activate.ps1'; Write-Host '[FRONTEND] Dash rodando...' -ForegroundColor Green; Write-Host 'Interface: http://127.0.0.1:8050' -ForegroundColor Cyan; Write-Host ''; python app.py"
)

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[OK] Servicos iniciados!" -ForegroundColor Green
Write-Host ""
Write-Host "URLs Disponiveis:" -ForegroundColor Yellow
Write-Host "   Backend API: " -NoNewline -ForegroundColor White
Write-Host "http://127.0.0.1:5000" -ForegroundColor Cyan
Write-Host "   API Docs:    " -NoNewline -ForegroundColor White
Write-Host "http://127.0.0.1:5000/docs" -ForegroundColor Cyan
Write-Host "   Frontend UI: " -NoNewline -ForegroundColor White
Write-Host "http://127.0.0.1:8050" -ForegroundColor Cyan
Write-Host ""
Write-Host "DICA: Duas janelas PowerShell foram abertas (Backend + Frontend)" -ForegroundColor Gray
Write-Host "      Para parar, feche as janelas ou pressione Ctrl+C em cada uma." -ForegroundColor Gray
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Pressione qualquer tecla para fechar esta janela..." -ForegroundColor DarkGray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
