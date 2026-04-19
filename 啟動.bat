@echo off
title KGI Sprint Reader
echo.
echo  正在啟動 KGI Sprint Reader...
echo.

:: 安裝 flask（已裝過會自動跳過）
pip install flask -q

:: 啟動伺服器（背景執行）
start /b python app.py

:: 等待伺服器啟動
timeout /t 2 /nobreak > nul

:: 自動開啟瀏覽器
start http://localhost:5050

echo  已開啟瀏覽器，請查看 http://localhost:5050
echo  關閉此視窗即可停止伺服器。
echo.
pause
