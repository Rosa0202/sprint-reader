# Project 3 — The 7-Minute Sprint Reader
## 凱基金控 · 金融數位科技儲備幹部 Mini Project

---

## 快速啟動

```bash
# 1. 安裝依賴
pip install flask

# 2. 執行
python app.py

# 3. 開啟瀏覽器
http://localhost:5050
```

---

## 技術架構

| 層次 | 技術選擇 | 原因 |
|------|----------|------|
| Backend | Python + Flask | 輕量、快速啟動、適合 demo |
| Database | SQLite | 無需安裝 server；Schema 設計與 PostgreSQL 相容，可零改動遷移 |
| Frontend | Vanilla HTML/CSS/JS | 無 build step，面試環境直接運行 |

---

## 資料庫設計說明

```
MicroModules (P1 stub)
    │
    ├──▶ FlashcardPages     ← 卡片內容，sequence_number 確保順序
    │
    └──▶ SprintSessions     ← 每次閱讀行為記錄
              │
              └──▶ LearningJourney_Map  ← 串接 P2 Quiz Session
```

**Foreign Key 完整性**：所有 FK 均啟用 `PRAGMA foreign_keys=ON`

**LearningJourney_Map 設計邏輯**：
這張 bridge table 讓閱讀（P3）與測驗（P2）可以獨立擴展。
未來 AI 分析只需 JOIN 這一張表，即可關聯「閱讀行為 → 測驗表現」。

---

## 規格對應

| 需求 | 實作方式 |
|------|----------|
| Req 1: Metadata Fetching | `GET /api/modules/:id` 一次回傳 module 元數據 + 所有卡片 |
| Req 2: Visibility API | `document.visibilitychange` 事件 → 暫停計時 + 呼叫 `PATCH /tab-switch` 寫入 DB |
| Req 3: Seamless Handoff | `POST /complete` 同步產生 `sprint_id` + `journey_id` + `quiz_session_id` |

---

## 差異化功能一：主動回憶機制（Active Recall）

**設計動機**：直接呼應 Forgetting Curve 文件的核心目標——將被動瀏覽轉為主動確認。

每張卡片底部提供兩個選項：
- **需要再看** → 卡片會在同一 Session 內重複出現
- **記住了 ✓** → 對應小點變為黃色，進度推進

標記「需要再看」的卡片在同一 7 分鐘內無限輪次重複，直到使用者確認全部記住，「完成閱讀」按鈕才會出現。此設計基於主動回憶（Active Recall）的心理學原理，強迫學習者自我評估理解程度，而非被動滑過。

---

## 差異化功能二：Per-Card Dwell Time（累加邏輯）

**設計動機**：`tab_switch_count` 只能判斷「有沒有分心」，dwell time 可以判斷「在哪張卡片花了多少時間」。

**累加邏輯**：使用者若翻回已讀過的卡片，停留時間累加而非重複記錄，確保數據真實反映總閱讀時間。

**`card_dwell_json` 格式**：

```json
[
  {"page_id": "mod-001-p1", "dwell_ms": 73000, "review_rounds": 2, "card_status": "remembered"},
  {"page_id": "mod-001-p2", "dwell_ms": 50000, "review_rounds": 3, "card_status": "review"}
]
```

| 欄位 | 說明 |
|------|------|
| `dwell_ms` | 這張卡片的總停留時間（毫秒，累加） |
| `review_rounds` | 這張卡片被離開幾次（含第一次） |
| `card_status` | 最終標記狀態：`remembered` / `review` / `pending` |

**業務價值**：閱讀完但測驗答錯 → 可回溯是「根本沒讀到那張」還是「讀了但沒理解」，為 P2 Quiz Engine 個人化推薦提供關鍵信號。

---

## API 端點

```
GET   /api/modules                     → 模組列表
GET   /api/modules/:id                 → 模組詳情 + 卡片內容
POST  /api/sessions/start              → 開始 Sprint Session
PATCH /api/sessions/:id/tab-switch     → 分頁切換 +1
POST  /api/sessions/:id/complete       → 完成 + 產生 journey_id
GET   /api/telemetry                   → 所有 Session 記錄（Telemetry Dashboard）
```

---

## completion_status 說明

| 狀態 | 觸發時機 | 產生 LearningJourney_Map |
|------|----------|--------------------------|
| `in_progress` | Session 建立時的初始值 | — |
| `finished_early` | 使用者在時間到前按完成閱讀 | ✅ |
| `timed_out` | 七分鐘倒數歸零 | ✅ |
| `abandoned` | 使用者關閉或重新整理頁面 | ❌ |

---

## Telemetry Dashboard

點擊右下角 📊 按鈕，可即時查看所有 SprintSessions 記錄，
包含：completion_status / tab_switch_count / 閱讀開始時間。
