@echo off
REM Construit Presence Customiser.exe (sans console) dans le dossier dist\
python -m pip install -r requirements.txt pyinstaller
python -m PyInstaller --noconsole --onefile --name PresenceCustomiser ^
  --collect-all customtkinter --collect-all pypresence ^
  --hidden-import pystray._win32 main.py
echo.
echo Termine : dist\PresenceCustomiser.exe
pause
