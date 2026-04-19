#!/bin/bash
echo ""
echo " 正在啟動 KGI Sprint Reader..."
echo ""

# 切換到腳本所在目錄（確保路徑正確）
cd "$(dirname "$0")"

# 安裝 flask（已裝過會自動跳過）
pip3 install flask -q 2>/dev/null || pip install flask -q

# 背景啟動伺服器
python3 app.py &>/dev/null &
SERVER_PID=$!

# 等待伺服器啟動
sleep 2

# 自動開啟瀏覽器
open http://localhost:5050

echo " 已開啟瀏覽器：http://localhost:5050"
echo " 按下 Enter 可停止伺服器"
echo ""
read

# 關閉伺服器
kill $SERVER_PID 2>/dev/null
echo " 伺服器已停止。"
