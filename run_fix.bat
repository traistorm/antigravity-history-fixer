@echo off
chcp 65001 > nul
echo ========================================================
echo   ANTIGRAVITY HISTORY FIXER - VA LOI LICH SU CHAT
echo ========================================================
echo.

cd /d "%~dp0"

echo [1/2] Dang va UI (Bo gioi han thu gon 'Show more')...
python patch_ui.py
echo.

echo [2/2] Dang quet va phuc hoi cac cuoc hoi thoai...
python sync_conversations.py
echo.

echo ========================================================
echo   HOAN TAT!
echo   Vui long vao Antigravity IDE bam Ctrl + R (Reload Window)
echo   de ap dung thay doi ngay lap tuc!
echo ========================================================
pause
