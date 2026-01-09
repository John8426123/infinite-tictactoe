# Project Context: Infinite Tic-Tac-Toe (Flask + Socket.io)

## 1. 專案技術棧 (Tech Stack)

### Backend (Server-Side)
- **Language:** Python 3.x
- **Web Framework:** Flask
- **Real-time Communication:** Flask-SocketIO
- **Concurrency:** Threading (用於背景 Timeout 監控)
- **Data Structures:** Python Dataclasses (用於強型別狀態管理)
- **Standard Libraries:** `time`, `os`, `random`, `typing`

### Frontend (Client-Side)
- **Structure:** HTML5
- **Styling:** CSS3 (Flexbox, Grid Layout, CSS Variables, Animations, RWD)
- **Scripting:** Vanilla JavaScript (ES6+)
- **Library:** Socket.IO Client (`socket.io.js` v4.0.1 via CDN)

---

## 2. 檔案結構與功能職責

### 📂 `app.py` (Backend Entry Point)
負責伺服器端的遊戲邏輯核心、狀態管理與與 WebSocket 事件處理。
- **GameState Class:** 單例模式 (Singleton) 的遊戲狀態機。管理棋盤陣列、玩家連線資訊 (SID)、排隊隊列 (Queue)、分數與 AI 設定。
- **Game Logic:**
  - 實作「無限井字遊戲」規則 (第 4 顆棋子落下時，第 1 顆消失)。
  - 實作 Minimax 演算法 (含 Alpha-Beta 剪枝) 供 AI 對戰使用 (Easy/Medium/Hard)。
- **Socket Events:** 處理 `join_game`, `make_move`, `toggle_pause`, `reset_game`, `kick_opponent` 等即時指令。
- **Background Worker:** `timeout_monitor` 執行緒，負責監控回合時間與 AI 自動下棋。
- **HTTP Routes:** 提供首頁渲染與 Log 匯出功能。

### 📂 `templates/index.html` (Frontend UI)
負責使用者介面呈現與客戶端邏輯。
- **UI Components:**
  - 登入 Modal。
  - 3x3 棋盤 (動態渲染 CSS Class 處理棋子顏色與淡出特效)。
  - 狀態列 (顯示當前玩家、分數、倒數計時)。
  - 側邊欄 (戰績、聊天室、排隊清單)。
  - 控制面板 (AI 難度調整、暫停、換人)。
- **Client Logic (`game` object):**
  - 封裝 Socket.IO 的 `emit` 與 `on` 事件。
  - 處理 DOM 操作與視覺回饋 (如：獲勝彈窗動畫)。

---

## 3. 關鍵邏輯說明

### 🔄 無限井字規則 (Infinite Logic)
- **FIFO 機制:** 當某一方的棋子數量達到 `MAX_PIECES` (3) 時，系統會在放置新棋子前，移除該玩家 `moves` 列表中的第一個索引位置 (最早下的棋)。
- **視覺提示:** 後端會計算下一顆即將消失的棋子，前端透過 `.fading` class 加上閃爍動畫提示玩家。

### 🤖 AI 決策系統 (Minimax)
- **難度分級:**
  - **Easy:** 50% 隨機 + 50% 基礎策略。
  - **Medium:** 20% 隨機 + 80% 進階策略 (尋找 Fork 雙重威脅)。
  - **Hard:** 100% Minimax 演算法 (深度遞迴搜尋最佳解，考慮棋子消失規則)。
- **觸發時機:** 透過 `timeout_monitor` 監控，輪到 AI 回合時自動計算並執行 `ai_make_move`。

### 🔌 Socket 連線與狀態同步
1. **Join:** 玩家連線後，系統優先填補 X 或 O 的空缺；若滿員則進入 `Observer` 模式並加入 Queue。
2. **Move:** 玩家點擊 -> 前端 Emit `make_move` -> 後端驗證並更新 State -> Broadcast `update_board` -> 所有前端重繪。
3. **Reconnect/Disconnect:** 斷線時自動移除玩家並從 Queue 中遞補下一位，保持遊戲流暢。

---

## 4. 開發規範 (Development Standards)

### Naming Conventions
- **Python (Backend):** 採用 **snake_case** (如 `game_active`, `check_winner`, `current_turn`)。
- **JavaScript (Frontend):** 採用 **camelCase** (如 `game.init()`, `updateBoard`, `sendChat`)。
- **CSS Classes:** 採用 **kebab-case** 且具語意化 (如 `.game-container`, `.player-card`, `.active-X`)。

### Type Safety
- Python 端使用 `typing` (`List`, `Tuple`, `Optional`) 與 `@dataclass` 來確保資料結構的清晰度與型別提示。

### Code Organization
- 邏輯分離：AI 演算法 (`minimax_infinite`, `simulate_move`) 與 Socket 事件處理函式分離，維持程式碼可讀性。

---

## 5. 待開發功能清單 (To-Do List)

以下列出專案接下來的重點開發項目：

### 📝 系統維運與記錄
- [ ] **實作後台 Log 系統 (Game Result Logging)**
  - *目標:* 目前僅記錄聊天內容 (`chat_records.log`)。需新增記錄每局遊戲的「勝負結果」、「使用的總回合數」與「對戰時間」。
  - *檔案:* 預計新增 `game_history.log` 或擴充現有 Log 格式。
- [ ] **優化 /admin 路由以匯出 Log 檔**
  - *目標:* 將目前硬編碼的 `/admin/export10380045_logs` 路由標準化。
  - *需求:* 增加簡單的驗證機制 (Basic Auth) 或整理為標準的 Admin Dashboard，支援選擇下載不同日期的 Log。

### 📱 使用者體驗優化
- [ ] **優化手機版 UI (Mobile Responsive)**
  - *目標:* 改善 `max-width: 850px` 下的佈局。
  - *細節:*
    - 調整棋盤在直立螢幕下的比例，避免過小。
    - 將側邊欄 (聊天室/排隊) 改為手機版的「抽屜式 (Drawer)」或「頁籤切換 (Tabs)」顯示，避免頁面過長。
    - 放大觸控按鈕區域，防止誤觸。

### 🛠 其他潛在優化
- [ ] **重構全域變數:** 考慮將 `game` 物件移至獨立的 `game_engine.py` 檔案，避免 `app.py` 過於肥大。