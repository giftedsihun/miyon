$ErrorActionPreference = "Stop"
python -m pip install pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --windowed --name HaruJapanese --hidden-import content japanese_study.py
Write-Host "EXE created at dist\HaruJapanese.exe"
