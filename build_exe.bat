@echo off
REM Builds PresenceCustomiser.exe (no console) into the dist\ folder
python -m pip install -r requirements.txt pyinstaller
python -m PyInstaller --noconsole --onefile --name PresenceCustomiser ^
  --collect-all customtkinter --collect-all pypresence ^
  --hidden-import pystray._win32 main.py
echo.
echo Done: dist\PresenceCustomiser.exe
pause
