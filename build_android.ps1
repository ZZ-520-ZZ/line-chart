$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$productName = -join (0x7ED8, 0x56FE, 0x5DE5, 0x5177 | ForEach-Object { [char]$_ })

$flet = Join-Path $PSScriptRoot ".venv\Scripts\flet.exe"
if (-not (Test-Path $flet)) {
    throw "Create .venv and install requirements.txt first."
}

& $flet build apk $PSScriptRoot `
    --yes `
    --project line_chart `
    --artifact line_chart `
    --product $productName `
    --org com.zz520zz `
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
