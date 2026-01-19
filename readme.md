♾️ 無限圈圈叉叉：職業對戰平台 (Infinity Tic-Tac-Toe: Pro Arena)

一個基於 Python Flask 與 WebSocket (Socket.IO) 的即時多人連線對戰系統。結合「先進先出 (FIFO)」的無限棋步機制與電競級的視覺介面。

在render上試玩版：https://quan-quan-cha-cha.onrender.com 

但在render上ai下棋跑不動，我是用免費版。

📖 專案簡介 (Introduction)

本專案不僅是一個井字遊戲，而是一個模擬高併發、即時互動的分散式系統原型。透過 WebSocket 實現毫秒級的狀態同步，並導入了「排隊系統」、「觀察者模式」以及「後端狀態監控」，旨在解決傳統網頁遊戲在即時性與狀態管理上的挑戰。

核心玩法採用 "Three Men's Morris" (三子棋) 變體規則：每位玩家場上最多保留 3 顆棋子，第 4 顆棋子落下時，最早的那顆將自動消失，徹底消除了平局的可能性，大幅提升策略深度。

🚀 核心功能 (Key Features)

🎮 遊戲機制

無限模式 (Infinite Loop)：採用 FIFO (First-In, First-Out) 佇列管理棋子，場上永遠只有 3 顆棋子，動態博弈。

即時排隊系統 (Queue System)：支援多人同時連線，除了兩位玩家 (X/O) 外，其餘連線者自動進入排隊佇列，並以觀察者身份觀戰。

自動遞補 (Auto-Promotion)：當場上玩家斷線或被踢出時，系統自動從佇列中提拔第一順位補位，無縫接軌。

🛠️ 系統架構

WebSocket 通訊：使用 Flask-SocketIO 建立全雙工通訊，實現廣播 (Broadcast) 與單播 (Unicast) 的精準控制。

狀態持久化 (Persistence)：伺服器端即時寫入聊天紀錄 (.log) 與訪客地理位置，確保數據不因重啟而遺失。

系統監控 (Observability)：

內建 /health API 端點，供外部監控系統確認服務狀態。

具備心跳包 (Heartbeat) 機制，前端即時顯示與後端的連線延遲與剩餘時間。

管理員權限：具備暫停遊戲、強制換人 (Kick)、匯出日誌等管理功能。

🎨 使用者介面 (UI/UX)

Cyberpunk 電競風格：深色模式、霓虹光暈特效、玻璃擬態 (Glassmorphism)。

RWD 響應式設計：完美支援桌機、平板與手機瀏覽器。

友善輸入：針對 Mac/iOS 輸入法優化。

⚙️ 技術堆疊 (Tech Stack)

Backend: Python 3.9+, Flask, Flask-SocketIO, Gevent (Production WSGI)

Frontend: HTML5, CSS3 (Flexbox/Grid), JavaScript (Socket.IO Client)

Tools: Threading (背景計時任務), Requests (IP Geolocation)

📦 安裝與執行 (Installation)

1. 複製專案

git clone [https://github.com/your-username/infinity-tic-tac-toe.git](https://github.com/your-username/infinity-tic-tac-toe.git)
cd infinity-tic-tac-toe


2. 安裝依賴套件

建議使用虛擬環境 (Virtual Environment)。

# 建立虛擬環境
python -m venv venv

# 啟動虛擬環境 (Windows)
venv\Scripts\activate
# 啟動虛擬環境 (Mac/Linux)
source venv/bin/activate

# 安裝套件
pip install flask flask-socketio requests gevent


3. 啟動伺服器

python app.py


終端機顯示 Running on http://0.0.0.0:8080 即代表啟動成功。

4. 開始遊戲

打開瀏覽器訪問 http://localhost:8080 (本機) 或 http://<你的內網IP>:8080 (區域網路對戰)。

📂 專案結構 (Project Structure)

infinity-tic-tac-toe/
├── app.py                 # 後端核心邏輯 (FSM, Socket Events, API)
├── templates/
│   └── index.html         # 前端介面 (UI, Socket Client Logic)
├── chat_records.log       # [自動生成] 聊天室歷史紀錄
└── README.md              # 專案說明文件


🔧 管理員指令與 API

匯出聊天紀錄: 訪問 /admin/export_logs 可下載伺服器端保存的所有對話。

系統健康檢查: 訪問 /health 獲取 JSON 格式的系統狀態 (Queue 長度、玩家狀態)。

加入 AI 對戰模式 (Minimax Algorithm)。

