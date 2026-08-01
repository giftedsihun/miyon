param(
    [string]$CertificatePath = "",
    [string]$CertificatePassword = "",
    [string]$CertificateThumbprint = "",
    [string]$SignToolPath = "",
    [string]$TimestampServer = "http://timestamp.digicert.com",
    [string]$VoiceSource = "",
    [switch]$SkipExeBuild
)


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

function Resolve-SignTool {
    if ($SignToolPath) {
        if (-not (Test-Path -LiteralPath $SignToolPath)) { throw "SignTool was not found: $SignToolPath" }
        return $SignToolPath
    }
    $command = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    $kits = @("${env:ProgramFiles(x86)}\Windows Kits\10\bin", "$env:ProgramFiles\Windows Kits\10\bin")
    foreach ($kit in $kits) {
        if (Test-Path -LiteralPath $kit) {
            $found = Get-ChildItem -LiteralPath $kit -Recurse -Filter signtool.exe -ErrorAction SilentlyContinue |
                Sort-Object FullName -Descending | Select-Object -First 1
            if ($found) { return $found.FullName }
        }
    }
    return ""
}

function Resolve-ISCC {
    $command = Get-Command iscc.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    $pf86 = $env:ProgramFiles + " (x86)"
    foreach ($path in @(
        (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"),
        (Join-Path $pf86 "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
    )) {
        if (Test-Path -LiteralPath $path) { return $path }
    }
    return ""
}

function Invoke-SignFile {
    param(
        [string]$SignTool,
        [string]$FilePath,
        [string]$CertPath,
        [string]$CertPassword,
        [string]$Thumbprint,
        [string]$Timestamp
    )
    $args = @("sign", "/fd", "SHA256")
    if ($Thumbprint) {
        $args += @("/sha1", $Thumbprint)
    } elseif ($CertPath) {
        $args += @("/f", $CertPath)
        if ($CertPassword) { $args += @("/p", $CertPassword) }
    } else {
        throw "No signing identity provided."
    }
    $args += @("/tr", $Timestamp, "/td", "SHA256", $FilePath)
    $ErrorActionPreference = "Continue"
    try { & $SignTool @args } finally { $ErrorActionPreference = "Stop" }
    if ($LASTEXITCODE -ne 0) { throw "signtool failed with exit code ${LASTEXITCODE}: $FilePath" }
}

function Get-AppVersion {
    $infoLine = Select-String -LiteralPath (Join-Path $PSScriptRoot "app_info.py") -Pattern 'APP_VERSION\s*=\s*"([^"]+)"'
    if (-not $infoLine) { throw "APP_VERSION was not found in app_info.py" }
    return $infoLine.Matches[0].Groups[1].Value
}

$dist = Join-Path $PSScriptRoot "dist"
$installerDir = Join-Path $dist "installer"
$exe = Join-Path $dist "HaruJapanese.exe"
$installerScript = Join-Path $PSScriptRoot "packaging\harujapanese_installer.iss"
$version = Get-AppVersion

$wantsSigning = [bool]($CertificatePath -or $CertificateThumbprint)
$signTool = ""
if ($wantsSigning) {
    $signTool = Resolve-SignTool
    if (-not $signTool) {
        throw "Code signing was requested but signtool.exe was not found in PATH or the Windows 10 SDK bin folders."
    }
    if ($CertificateThumbprint) {
        $cert = Get-Item -LiteralPath ("Cert:\CurrentUser\My\" + $CertificateThumbprint) -ErrorAction SilentlyContinue
        if (-not $cert) { $cert = Get-Item -LiteralPath ("Cert:\LocalMachine\My\" + $CertificateThumbprint) -ErrorAction SilentlyContinue }
        if (-not $cert) { throw "Certificate thumbprint was not found in CurrentUser\My or LocalMachine\My: $CertificateThumbprint" }
    } elseif (-not (Test-Path -LiteralPath $CertificatePath)) {
        throw "Certificate file was not found: $CertificatePath"
    }
} else {
    Write-Warning "No certificate provided. The EXE and installer will NOT be code-signed."
}

if (-not $SkipExeBuild) {
    & (Join-Path $PSScriptRoot "build_exe.ps1")
}
if (-not (Test-Path -LiteralPath $exe)) {
    throw "EXE was not found: $exe"
}

if ($wantsSigning) {
    Invoke-SignFile -SignTool $signTool -FilePath $exe -CertPath $CertificatePath -CertPassword $CertificatePassword -Thumbprint $CertificateThumbprint -Timestamp $TimestampServer
    Write-Host "Signed EXE: $exe"
}

$iscc = Resolve-ISCC
if (-not $iscc) {
    throw "Inno Setup 6 (ISCC.exe) was not found. Install Inno Setup 6 and retry, or reuse build_exe.ps1 for a plain EXE."
}

New-Item -ItemType Directory -Path $installerDir -Force | Out-Null
$isccArgs = @("/DMyAppVersion=$version", "/DSourceExe=$exe", "/O$installerDir")
if ($VoiceSource) {
    if (-not (Test-Path -LiteralPath $VoiceSource)) { throw "Voice source directory was not found: $VoiceSource" }
    $isccArgs += "/DVoiceSourceDir=$VoiceSource"
} elseif (Test-Path -LiteralPath (Join-Path $HOME ".haru_japanese\zundamon-gpt-sovits-api\api.py")) {
    $defaultVoice = Join-Path $HOME ".haru_japanese\zundamon-gpt-sovits-api"
    $isccArgs += "/DVoiceSourceDir=$defaultVoice"
    Write-Host "Bundling prepared voice source from: $defaultVoice"
}
$isccArgs += $installerScript
Invoke-CheckedNative $iscc @isccArgs


$setup = Join-Path $installerDir "HaruJapaneseSetup-$version.exe"
if (-not (Test-Path -LiteralPath $setup)) {
    $setup = Get-ChildItem -LiteralPath $installerDir -Filter "HaruJapaneseSetup-*.exe" | Select-Object -First 1
    if (-not $setup) { throw "Installer was not produced in: $installerDir" }
    $setup = $setup.FullName
}

if ($wantsSigning) {
    Invoke-SignFile -SignTool $signTool -FilePath $setup -CertPath $CertificatePath -CertPassword $CertificatePassword -Thumbprint $CertificateThumbprint -Timestamp $TimestampServer
    Write-Host "Signed installer: $setup"
}

foreach ($file in @($exe, $setup)) {
    $sig = Get-AuthenticodeSignature -LiteralPath $file
    $line = "{0}: Status={1}" -f $file, $sig.Status
    if ($wantsSigning) {
        if ($sig.Status -ne "Valid") { throw "Signature verification failed for $file : $($sig.Status)" }
        $line += " Signer=$($sig.SignerCertificate.Subject)"
    }
    Write-Host $line
}

$manifest = Join-Path $installerDir "SHA256SUMS.txt"
Get-ChildItem -LiteralPath $installerDir -File -Filter "HaruJapaneseSetup-*.exe" |
    Get-FileHash -Algorithm SHA256 |
    ForEach-Object { "{0} *{1}" -f $_.Hash, $_.Path.Substring($installerDir.Length + 1) } |
    Set-Content -LiteralPath $manifest -Encoding ascii

$size = (Get-Item -LiteralPath $setup).Length
Write-Host "Installer created: $setup"
Write-Host "Installer size: $([math]::Round($size / 1MB, 2)) MB"
Write-Host "Checksum manifest: $manifest"
