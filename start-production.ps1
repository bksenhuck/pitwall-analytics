# Script para testar o modo de produção localmente
# Simula como o app rodará no Render/Heroku

Write-Host "[PRODUCTION TEST] Iniciando modo de producao..." -ForegroundColor Cyan
Write-Host ""

# Verificar se esta no diretorio correto
$projectPath = Get-Location
if (-not (Test-Path "main.py")) {
    Write-Host "[ERRO] Diretorio do projeto nao encontrado!" -ForegroundColor Red
    exit 1
}

Set-Location $projectPath

# Ativar ambiente virtual
$venvPaths = @(".\venv_pitwall_analytics\Scripts\Activate.ps1", ".\venv\Scripts\Activate.ps1")
foreach ($venvPath in $venvPaths) {
    if (Test-Path $venvPath) {
        & $venvPath
        break
    }
}

Write-Host "[INFO] Modo: PRODUCAO (servidor unificado)" -ForegroundColor Yellow
Write-Host ""
Write-Host "Estrutura de rotas:" -ForegroundColor White
Write-Host "  /                    -> Frontend Dash" -ForegroundColor Gray
Write-Host "  /api/*               -> Backend FastAPI" -ForegroundColor Gray
Write-Host "  /api/docs            -> API Documentation" -ForegroundColor Gray
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Executar o servidor unificado
python main.py
