$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$productName = "Plotforge"

$flet = Join-Path $PSScriptRoot ".venv\Scripts\flet.exe"
if (-not (Test-Path $flet)) {
    throw "Create .venv and install requirements.txt first."
}

& $flet pack (Join-Path $PSScriptRoot "main.py") `
    --name $productName `
    --icon (Join-Path $PSScriptRoot "assets\plotforge.ico") `
    --onedir `
    --distpath (Join-Path $PSScriptRoot "dist\windows") `
    --add-data "assets:assets" `
    --product-name $productName `
    --file-description "Physics experiment plotting and fitting tool" `
    --company-name "ZZ-520-ZZ" `
    --yes

if ($LASTEXITCODE -ne 0) {
    throw "Windows build failed."
}

$appDirectory = Join-Path $PSScriptRoot "dist\windows\$productName"
$archivePath = Join-Path $PSScriptRoot "dist\$productName-Windows.zip"
if (-not (Test-Path $appDirectory)) {
    throw "Windows build output was not found: $appDirectory"
}
Compress-Archive -Path $appDirectory -DestinationPath $archivePath -CompressionLevel Optimal -Force
Write-Host "Windows release package: $archivePath"
