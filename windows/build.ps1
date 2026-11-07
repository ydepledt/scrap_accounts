$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
python -m venv .build-venv
if ($LASTEXITCODE -ne 0) { throw 'Cannot create build environment' }
& .\.build-venv\Scripts\python.exe -m pip install -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw 'Cannot install build dependencies' }
& .\.build-venv\Scripts\python.exe -m PyInstaller --noconfirm --onefile --windowed --name ScrapAccounts app.py
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
Write-Output "Executable: $PSScriptRoot\dist\ScrapAccounts.exe"
