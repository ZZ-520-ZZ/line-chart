$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$productName = "Plotforge"

$flet = Join-Path $PSScriptRoot ".venv\Scripts\flet.exe"
if (-not (Test-Path $flet)) {
    throw "Create .venv and install requirements.txt first."
}

$localJdk = Join-Path $PSScriptRoot ".toolchain\jdk17\jdk-17.0.13+11"
if (-not $env:JAVA_HOME -and (Test-Path (Join-Path $localJdk "bin\javac.exe"))) {
    $env:JAVA_HOME = $localJdk
}

& $flet build apk $PSScriptRoot `
    --yes `
    --project plotforge `
    --artifact plotforge `
    --product $productName `
    --org com.zz520zz `
    --android-adaptive-icon-background "#081D34" `
    --arch arm64-v8a `
    --android-extract-packages matplotlib `
    --android-legacy-packaging `
    --exclude .flet .venv .git build dist tests docs __pycache__ `
        gui_smoke_test.py test_regressions.py cross_platform_smoke_test.py run_tests.py `
    --no-compile-app `
    --no-rich-output

if ($LASTEXITCODE -ne 0) {
    throw "Android build failed."
}

$builtApk = Join-Path $PSScriptRoot "build\apk\plotforge.apk"
$releaseDirectory = Join-Path $PSScriptRoot "dist"
$releaseApk = Join-Path $releaseDirectory "$productName-Android-arm64.apk"
if (-not (Test-Path $builtApk)) {
    throw "Android build output was not found: $builtApk"
}
New-Item -ItemType Directory -Path $releaseDirectory -Force | Out-Null
Copy-Item -LiteralPath $builtApk -Destination $releaseApk -Force
Write-Host "Android release package: $releaseApk"
