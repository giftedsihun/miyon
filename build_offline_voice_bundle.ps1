param(
    [string]$VoiceSource = (Join-Path $HOME ".haru_japanese\zundamon-gpt-sovits-api"),
    [string]$FfmpegDirectory = ""
)

$ErrorActionPreference = "Stop"
$release = Join-Path $PSScriptRoot "dist\HaruJapanese-offline"
$voiceDestination = Join-Path $release "zundamon-gpt-sovits-api"

if (-not (Test-Path -LiteralPath (Join-Path $VoiceSource "api.py"))) {
    throw "Prepared voice API was not found: $VoiceSource\api.py. Start AI voice once in HaruJapanese before packaging."
}
if (-not (Test-Path -LiteralPath (Join-Path $VoiceSource ".haru-runtime\Scripts\python.exe"))) {
    throw "Prepared voice runtime was not found: $VoiceSource\.haru-runtime\Scripts\python.exe."
}

& (Join-Path $PSScriptRoot "build_exe.ps1")
if (-not (Test-Path -LiteralPath (Join-Path $VoiceSource "reference\reference.wav"))) {    throw "Prepared Zundamon reference audio was not found: $VoiceSource\reference\reference.wav."
}
foreach ($relativePath in @(
    "GPT_weights_v2\zudamon_style_1-e15.ckpt",
    "SoVITS_weights_v2\zudamon_style_1_e8_s96.pth",
    "GPT_SoVITS\pretrained_models\chinese-hubert-base\pytorch_model.bin",
    "GPT_SoVITS\pretrained_models\chinese-roberta-wwm-ext-large\pytorch_model.bin"
)) {
    if (-not (Test-Path -LiteralPath (Join-Path $VoiceSource $relativePath))) {
        throw "Prepared voice model is missing: $VoiceSource\$relativePath"
    }
}

Remove-Item -LiteralPath $release -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $release | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "dist\HaruJapanese.exe") -Destination (Join-Path $release "HaruJapanese.exe")
Copy-Item -LiteralPath $VoiceSource -Destination $voiceDestination -Recurse

if ($FfmpegDirectory) {
    if (-not (Test-Path -LiteralPath (Join-Path $FfmpegDirectory "ffmpeg.exe"))) {
        throw "ffmpeg.exe was not found in: $FfmpegDirectory"
    }
    $tools = Join-Path $voiceDestination "tools\ffmpeg"
    New-Item -ItemType Directory -Path $tools -Force | Out-Null
    Copy-Item -Path (Join-Path $FfmpegDirectory "*") -Destination $tools -Recurse
}

# Ship a local manifest so a release maintainer can audit every bundled file.
Get-ChildItem -LiteralPath $voiceDestination -Recurse -File |
    Get-FileHash -Algorithm SHA256 |
    ForEach-Object { "{0} *{1}" -f $_.Hash, $_.Path.Substring($voiceDestination.Length + 1) } |
    Set-Content -LiteralPath (Join-Path $release "VOICE-SHA256SUMS.txt") -Encoding ascii

$exe = Get-Item -LiteralPath (Join-Path $release "HaruJapanese.exe")
$voiceSize = (Get-ChildItem -LiteralPath $voiceDestination -Recurse -File | Measure-Object -Property Length -Sum).Sum
Write-Host "Offline bundle created: $release"
Write-Host "App: $([math]::Round($exe.Length / 1MB, 2)) MB; voice files: $([math]::Round($voiceSize / 1GB, 2)) GB"
Write-Host "Voice manifest: $(Join-Path $release 'VOICE-SHA256SUMS.txt')"
