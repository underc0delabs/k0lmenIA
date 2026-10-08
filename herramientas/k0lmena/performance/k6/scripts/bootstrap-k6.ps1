$ErrorActionPreference = "Stop"
$Version = "v2.3.0"
$OutDir = "tools/k6"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$A = "amd64"  # k6 publica binarios de Windows solo para amd64

$ZipUrl = "https://github.com/grafana/k6/releases/download/$Version/k6-$Version-windows-$A.zip"
$ZipPath = "$OutDir\k6.zip"

Write-Host "Descargando $ZipUrl ..."
Invoke-WebRequest -Uri $ZipUrl -OutFile $ZipPath

Write-Host "Extrayendo..."
Expand-Archive -Path $ZipPath -DestinationPath $OutDir -Force
Remove-Item $ZipPath

$Folder = Join-Path $OutDir "k6-$Version-windows-$A"
Move-Item (Join-Path $Folder "k6.exe") (Join-Path $OutDir "k6.exe") -Force
Remove-Item $Folder -Recurse -Force

Write-Host "Listo. Binario en tools/k6/k6.exe"