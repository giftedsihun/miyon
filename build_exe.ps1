$ErrorActionPreference = "Stop"

function Invoke-CheckedNative {
    param(
        [Parameter(Mandatory)][string]$FilePath,
        [Parameter(ValueFromRemainingArguments)][string[]]$Arguments
    )
    $ErrorActionPreference = "Continue"
    try { & $FilePath @Arguments } finally { $ErrorActionPreference = "Stop" }
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed (exit $LASTEXITCODE): $FilePath $($Arguments -join ' ')"
    }
}

Invoke-CheckedNative python -m unittest discover -s tests -v
Invoke-CheckedNative python -m pip install -r requirements-dev.txt
Invoke-CheckedNative python -m PyInstaller --noconfirm --clean --onefile --windowed --name HaruJapanese --hidden-import content --hidden-import learning_services --hidden-import progress_logic --hidden-import quiz_session --hidden-import storage --hidden-import tts_service --hidden-import study_logic --hidden-import quiz_logic --hidden-import ui_catalog --hidden-import ui_dialogs --hidden-import ui_quiz --hidden-import ui_screens --hidden-import ui_practice --hidden-import app_info japanese_study.py
$exe = Get-Item -LiteralPath "dist\HaruJapanese.exe"
if ($exe.Length -lt 1MB) { throw "EXE build is unexpectedly small: $($exe.Length) bytes" }
Write-Host "EXE verified at $($exe.FullName) ($([math]::Round($exe.Length / 1MB, 2)) MB)"
