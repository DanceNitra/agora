@echo off
set "LOCALAPPDATA=C:\Users\Danculus\AppData\Local"
set "USERPROFILE=C:\Users\Danculus"
cd /d "C:\Users\Danculus\agora\dictate"
start "" "C:\Users\Danculus\agora\dictate\.venv\Scripts\pythonw.exe" -m dictate --config "C:\Users\Danculus\AppData\Local\Dictate\config.json"
