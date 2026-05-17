# Job Application Bot — Windows Installer
# Run as Administrator in PowerShell:
#   irm https://raw.githubusercontent.com/bilalaslam1244-stack/job-application-bot/main/install.ps1 | iex

$ErrorActionPreference = "Stop"
$REPO_URL = "https://github.com/bilalaslam1244-stack/job-application-bot"
$INSTALL_DIR = "$env:USERPROFILE\job-application-bot"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Job Application Bot Installer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "Installing Python 3.11..." -ForegroundColor Yellow
    winget install Python.Python.3.11 --silent --accept-source-agreements --accept-package-agreements
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User")
}
Write-Host "Python: $(python --version)" -ForegroundColor Green

# 2. Git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Git..." -ForegroundColor Yellow
    winget install Git.Git --silent --accept-source-agreements --accept-package-agreements
}

# 3. Clone or update
if (Test-Path $INSTALL_DIR) {
    Write-Host "Updating existing installation..." -ForegroundColor Yellow
    Set-Location $INSTALL_DIR
    git pull
} else {
    Write-Host "Downloading bot..." -ForegroundColor Yellow
    git clone $REPO_URL $INSTALL_DIR
    Set-Location $INSTALL_DIR
}

# 4. Virtual environment + dependencies
Write-Host "Installing Python packages..." -ForegroundColor Yellow
python -m venv .venv
& .venv\Scripts\Activate.ps1
pip install -r requirements.txt --quiet

# 5. Playwright browser
Write-Host "Downloading browser (~150MB, one time only)..." -ForegroundColor Yellow
playwright install chromium

# 6. Config file
if (-not (Test-Path "config.yaml")) {
    Copy-Item config.template.yaml config.yaml
    Write-Host ""
    Write-Host "IMPORTANT: config.yaml created. You must fill it in before running." -ForegroundColor Yellow
} else {
    Write-Host "config.yaml already exists - keeping your settings." -ForegroundColor Green
}

# 7. Windows Task Scheduler - run at 8am, 1pm, 6pm
Write-Host "Setting up automatic daily schedule..." -ForegroundColor Yellow
foreach ($time in @("08:00", "13:00", "18:00")) {
    $name = "JobBot-$($time.Replace(':',''))"
    Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false
    $action   = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$INSTALL_DIR\run.bat`""
    $trigger  = New-ScheduledTaskTrigger -Daily -At $time
    $settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 2)
    Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest | Out-Null
    Write-Host "  Scheduled: $name at $time" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Installation Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Open this file in Notepad:" -ForegroundColor White
Write-Host "   $INSTALL_DIR\config.yaml" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Fill in ALL the REPLACE_ME values:" -ForegroundColor White
Write-Host "   - anthropic_api_key   (from console.anthropic.com)" -ForegroundColor Gray
Write-Host "   - telegram_bot_token  (from @BotFather on Telegram)" -ForegroundColor Gray
Write-Host "   - telegram_chat_id    (your Telegram user ID)" -ForegroundColor Gray
Write-Host "   - Portal emails and passwords for each job site" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Test your config:" -ForegroundColor White
Write-Host "   cd $INSTALL_DIR" -ForegroundColor Cyan
Write-Host "   .venv\Scripts\activate" -ForegroundColor Cyan
Write-Host "   python main.py config" -ForegroundColor Cyan
Write-Host ""
Write-Host "4. First run (search only, no applications yet):" -ForegroundColor White
Write-Host "   python main.py search" -ForegroundColor Cyan
Write-Host ""
Write-Host "5. Full run:" -ForegroundColor White
Write-Host "   python main.py run" -ForegroundColor Cyan
Write-Host "   OR double-click run.bat" -ForegroundColor Cyan
Write-Host ""
Write-Host "Bot will run automatically at 8am, 1pm, 6pm every day." -ForegroundColor Green
Write-Host ""
