"""
KGI Sprint Reader — Project 3
7-Minute Sprint Reader & Contextual Transition
"""

import sqlite3, uuid, json
from datetime import datetime, timezone, timedelta
from flask import Flask, g, jsonify, request, render_template

app = Flask(__name__)

# 台灣時間 UTC+8
TW = timezone(timedelta(hours=8))
def now_tw():
    return datetime.now(TW).strftime('%Y-%m-%dT%H:%M:%S')
DB_PATH = "db/sprint.db"

# ── DB CONNECTION ────────────────────────────────────────────
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop("db", None)
    if db:
        db.close()

# ── SCHEMA INIT ──────────────────────────────────────────────
def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript("""
        -- P1 stub: MicroModules (parent of FlashcardPages)
        CREATE TABLE IF NOT EXISTS MicroModules (
            module_id       TEXT PRIMARY KEY,
            title           TEXT NOT NULL,
            source_document TEXT NOT NULL,
            domain_tags     TEXT NOT NULL,   -- JSON array stored as text
            total_cards     INTEGER NOT NULL,
            created_at      TEXT NOT NULL
        );

        -- P3: Flashcard content segments
        CREATE TABLE IF NOT EXISTS FlashcardPages (
            page_id          TEXT PRIMARY KEY,
            module_id        TEXT NOT NULL REFERENCES MicroModules(module_id),
            sequence_number  INTEGER NOT NULL,
            page_content_json TEXT NOT NULL   -- {title, body, image_url?}
        );

        -- P3: Reading behavior per session
        CREATE TABLE IF NOT EXISTS SprintSessions (
            sprint_id         TEXT PRIMARY KEY,
            agent_id          TEXT NOT NULL,
            module_id         TEXT NOT NULL REFERENCES MicroModules(module_id),
            start_timestamp   TEXT NOT NULL,
            end_timestamp     TEXT,
            tab_switch_count  INTEGER NOT NULL DEFAULT 0,
            completion_status TEXT NOT NULL DEFAULT 'in_progress',
            -- Aditional telemetry (our differentiator)
            card_dwell_json   TEXT            -- [{page_id, dwell_ms, fast_skim}]
        );

        -- P3<->P2 bridge: links reading session to quiz session
        CREATE TABLE IF NOT EXISTS LearningJourney_Map (
            journey_id      TEXT PRIMARY KEY,
            sprint_id       TEXT NOT NULL REFERENCES SprintSessions(sprint_id),
            quiz_session_id TEXT            -- FK to P2; nullable until quiz starts
        );
    """)
    db.commit()
    _seed(db)
    db.close()

# ── SEED DATA ────────────────────────────────────────────────
def _seed(db):
    exists = db.execute("SELECT 1 FROM MicroModules LIMIT 1").fetchone()
    if exists:
        return

    modules = [
        {
            "module_id": "mod-001",
            "title": "2026 FSC 旅遊保險交叉銷售指引",
            "source_document": "2026 FSC Travel Insurance Cross-Selling Guidelines",
            "domain_tags": json.dumps(["#合規", "#旅遊保險", "#交叉銷售"]),
            "total_cards": 5,
            "cards": [
                {
                    "title": "適用範圍與從業資格",
                    "body": "<b>適用對象</b>：銀行理財專員、壽險業務員、產險代理人、證券商財富管理人員。\n\n<b>資格維持要求</b>\n・每 <b>2 年</b>須完成 FSC 認可旅遊保險課程 <b>至少 12 小時</b>\n・逾期未更新者，停止銷售資格\n・所屬機構須於 <b>5 個工作日內</b>向 FSC 申報\n\n<b>數位銷售新規（2026 新增）</b>\n透過 App、官網、LINE 完成的銷售，同樣須符合本指引所有要求，<b>不得以「系統自動化」為由規避人工審核</b>。"
                },
                {
                    "title": "KYC 兩階段評估與 DRQ 六項目",
                    "body": "<b>第一階段</b>：標準 KYC（身份、財務狀況、投保目的）\n<b>第二階段</b>：目的地風險問卷（DRQ）\n\n<b>DRQ 六項必填</b>\n① 目的地 FSC 風險等級（低／中／高／極高）\n② 旅遊天數與行程\n③ 活動類型（觀光／冒險運動／商務）\n④ 既有疾病與用藥\n⑤ 同行人員（含未成年或長者須加填附表）\n⑥ 已投保之其他保障\n\n<b>留存要求</b>：客戶親簽或電子簽章，保存 <b>至少 7 年</b>。\n⚠️ 2025 年裁罰案例中，<b>31%</b> 違規源於 DRQ 填寫不完整。"
                },
                {
                    "title": "費用揭露義務（EDS）與違規罰則",
                    "body": "<b>費用說明書（EDS）四大必揭露項目</b>\n① 保費明細（基本保費＋附加費用＋附約費率）\n② 理賠條件摘要（觸發條件與排除條款）\n③ 不保事項完整列舉\n④ 爭議申訴管道與時限\n\n<b>注意事項</b>\n・須使用 <b>FSC 核定標準格式</b>，不得自行刪改欄位\n・<b>不得</b>以口頭說明取代書面揭露\n・<b>不得</b>以「客戶表示已了解」省略 EDS 交付\n\n<b>違規罰則</b>\n・業務員：罰款 <b>30 萬～150 萬元</b>，停權 3～12 個月\n・機構：最高罰款 <b>500 萬元</b>"
                },
                {
                    "title": "理賠 SLA 時限一覽",
                    "body": "<b>旅遊不便險</b>（航班延誤、行李遺失）\n・受理後 <b>3 個工作日</b>內完成初審\n・核付或拒賠通知：<b>10 個工作日</b>內發出\n\n<b>旅遊醫療險</b>\n・一般門診：<b>15 個工作日</b>內給付或出具說明\n・住院／手術：<b>30 個工作日</b>\n・重大傷病／境外複雜案件：得申請延期，但<b>須主動通知客戶</b>\n\n<b>緊急救援險</b>\n・24 小時專線：<b>30 分鐘內</b>接通並啟動救援\n・後續行政程序：每週主動更新進度\n\n⚠️ 超出時限未告知客戶者，須加計<b>利息補償</b>（依郵政一年期定存利率）。"
                },
                {
                    "title": "2025 年三大違規態樣與裁罰案例",
                    "body": "<b>① 未充分說明不保事項（42%）</b>\n案例：未告知「既往症」排除條款 → 客戶出險遭拒賠\n裁罰：業務員<b>停權 6 個月</b>，機構罰款 <b>80 萬元</b>\n\n<b>② DRQ 填寫不完整（31%）</b>\n案例：同行長者未填高齡附表、未評估心臟病史\n裁罰：業務員罰款 <b>30 萬元</b>，須重修 12 小時訓練\n\n<b>③ 數位銷售規避審核（27%）</b>\n案例：App 無人工複核機制；EDS 以彈窗呈現不符書面要求\n裁罰：機構罰款 <b>350 萬元</b>，App 銷售功能<b>暫停 3 個月</b>"
                }
            ]
        },
        {
            "module_id": "mod-002",
            "title": "投資型保單銷售合規要點",
            "source_document": "Investment-Linked Insurance Compliance Manual Q1 2026",
            "domain_tags": json.dumps(["#合規", "#投資型保單", "#財富管理"]),
            "total_cards": 5,
            "cards": [
                {
                    "title": "投資型保單三大類型",
                    "body": "<b>① 全委型 ILP</b>\n・資金全權委託<b>投信機構</b>操作\n・客戶無需自選標的，依風險等級配置\n・適合：投資知識薄弱或偏好省力管理的客戶\n\n<b>② 自選型 ILP</b>\n・保戶<b>自行選擇</b>連結基金，可自由切換\n・基金清單每季至少公告更新一次\n・業務員<b>不得</b>推薦具體標的，僅可說明風險特性\n\n<b>③ 類全委型 ILP（2024 新增）</b>\n・「核心（全委）＋衛星（自選）」架構\n・須額外揭露：核心／衛星<b>配置比例</b>及<b>再平衡機制</b>"
                },
                {
                    "title": "KYP/KYC 雙軌評估與五級風險對應",
                    "body": "<b>五大評估項目</b>\n① 年齡與投資年限　② 財務狀況與流動資金\n③ 投資經驗與知識　④ 風險承受意願（問卷）\n⑤ 家庭責任與保障需求\n\n<b>風險等級對照</b>\n・RR1 保守型　・RR2 穩健保守型　・RR3 穩健型\n・RR4 積極型　・RR5 高積極型\n\n<b>核心規則</b>：客戶風險等級須 <b>≥ 產品風險等級</b>\n若客戶堅持購買較高風險產品，須填寫<b>「客戶自主聲明書」</b>，業務員不得主動勸誘。\n\n⚠️ 評估<b>每年重新進行一次</b>；市場單日跌幅超 5% 時，須主動聯繫客戶確認。"
                },
                {
                    "title": "四大費用結構完整揭露",
                    "body": "<b>① 前置費用（Front-end Load）</b>\n・年繳保費的 0%～150%，依繳費年度<b>逐年遞減</b>\n・第 1 年最高，第 6 年起通常降至 0%\n\n<b>② 保單維持費（Policy Fee）</b>\n・每月固定收取，約 <b>100～300 元</b>，與帳戶價值無關\n\n<b>③ 解約費用（Surrender Charge）</b>\n・前五年解約收取，第 1 年最高（<b>5%～8%</b>）\n・逐年遞減，第 6 年後歸零\n・須以<b>逐年表格</b>方式列示\n\n<b>④ 投資管理費（Fund Management Fee）</b>\n・年化 <b>0.5%～2.5%</b>，每日從基金淨值中扣除\n・客戶感受不直接，但<b>長期影響顯著</b>"
                },
                {
                    "title": "冷靜期規定與退費計算",
                    "body": "<b>冷靜期時限</b>：收到保單正本後 <b>10 個日曆日</b>（非工作日）\n\n<b>退費規定</b>\n・冷靜期內撤銷：<b>全額退還</b>已繳保費\n・不得扣除任何費用（含前置費、保單費、印花稅）\n・⚠️ 例外：若帳戶價值因市場波動<b>低於</b>已繳保費，退款以<b>當時帳戶價值</b>為準，差額由保戶自行承擔\n\n<b>業務員義務（遞送保單時）</b>\n① 書面告知冷靜期權利\n② 請客戶於「<b>收件確認書</b>」上簽名並填寫日期\n\n⚠️ 未履行告知義務者，冷靜期自<b>客戶實際知悉之日</b>起算。"
                },
                {
                    "title": "售後服務最低標準",
                    "body": "<b>NAV 更新頻率</b>\n・每個交易日收盤後 <b>2 小時內</b>更新至查詢平台\n・技術故障時：標示延遲說明，並於 <b>24 小時內</b>補更新\n\n<b>重大事件通知（1 個工作日內）</b>\n・基金淨值單日波動超 <b>5%</b>\n・基金清算或合併\n・投資策略重大調整\n・連結標的遭主管機關限制交易\n\n<b>年度對帳單（每年寄發）</b>\n帳戶總價值、各標的單位數及現值、年度損益、累計費用、保障金額變化\n\n<b>年度保單健診</b>\n・每年主動聯繫客戶，評估配置是否符合當前風險屬性\n・須留存<b>通聯記錄</b>備查"
                }
            ]
        }
    ]

    for m in modules:
        db.execute(
            "INSERT INTO MicroModules VALUES (?,?,?,?,?,?)",
            (m["module_id"], m["title"], m["source_document"],
             m["domain_tags"], m["total_cards"], now_tw())
        )
        for i, c in enumerate(m["cards"], 1):
            db.execute(
                "INSERT INTO FlashcardPages VALUES (?,?,?,?)",
                (f"{m['module_id']}-p{i}", m["module_id"], i,
                 json.dumps({"title": c["title"], "body": c["body"]}, ensure_ascii=False))
            )
    db.commit()

# ════════════════════════════════════════════════════════════
#  API ROUTES
# ════════════════════════════════════════════════════════════

@app.get("/")
def index():
    return render_template("index.html")

# -- List available modules
@app.get("/api/modules")
def list_modules():
    db = get_db()
    rows = db.execute("SELECT * FROM MicroModules ORDER BY created_at DESC").fetchall()
    return jsonify([dict(r) for r in rows])

# -- Module metadata + cards (Requirement 1: Metadata Fetching)
@app.get("/api/modules/<module_id>")
def get_module(module_id):
    db = get_db()
    mod = db.execute("SELECT * FROM MicroModules WHERE module_id=?", (module_id,)).fetchone()
    if not mod:
        return jsonify({"error": "not found"}), 404
    cards = db.execute(
        "SELECT * FROM FlashcardPages WHERE module_id=? ORDER BY sequence_number",
        (module_id,)
    ).fetchall()
    result = dict(mod)
    result["domain_tags"] = json.loads(result["domain_tags"])
    result["cards"] = [
        {**dict(c), "page_content_json": json.loads(c["page_content_json"])}
        for c in cards
    ]
    return jsonify(result)

# -- Start a sprint session
@app.post("/api/sessions/start")
def start_session():
    data = request.json
    db = get_db()
    sprint_id = str(uuid.uuid4())
    db.execute(
        """INSERT INTO SprintSessions
           (sprint_id, agent_id, module_id, start_timestamp, completion_status)
           VALUES (?,?,?,?,?)""",
        (sprint_id, data.get("agent_id","agent-demo"),
         data["module_id"], now_tw(), "in_progress")
    )
    db.commit()
    return jsonify({"sprint_id": sprint_id})

# -- Update tab switch count (Requirement 2: Visibility API integration)
@app.patch("/api/sessions/<sprint_id>/tab-switch")
def tab_switch(sprint_id):
    db = get_db()
    db.execute(
        "UPDATE SprintSessions SET tab_switch_count = tab_switch_count + 1 WHERE sprint_id=?",
        (sprint_id,)
    )
    db.commit()
    return jsonify({"ok": True})

# -- Complete a sprint session (Requirement 3: Seamless Handoff)
@app.post("/api/sessions/<sprint_id>/complete")
def complete_session(sprint_id):
    data = request.json
    db = get_db()

    card_dwell = data.get("card_dwell", [])
    completion_status = data.get("completion_status", "finished_early")

    db.execute(
        """UPDATE SprintSessions SET
            end_timestamp=?, completion_status=?, card_dwell_json=?
           WHERE sprint_id=?""",
        (now_tw(),
         completion_status,
         json.dumps(card_dwell, ensure_ascii=False),
         sprint_id)
    )

    # abandoned 不產生 LearningJourney_Map，因為測驗從未開始
    if completion_status == "abandoned":
        db.commit()
        return jsonify({"sprint_id": sprint_id, "completion_status": "abandoned"})

    # Generate journey_id + stub quiz_session_id (Handoff to P2)
    journey_id = str(uuid.uuid4())
    quiz_session_id = "quiz-" + str(uuid.uuid4())
    db.execute(
        "INSERT INTO LearningJourney_Map VALUES (?,?,?)",
        (journey_id, sprint_id, quiz_session_id)
    )
    db.commit()

    return jsonify({
        "journey_id": journey_id,
        "sprint_id": sprint_id,
        "quiz_session_id": quiz_session_id,
        "tab_switch_count": db.execute(
            "SELECT tab_switch_count FROM SprintSessions WHERE sprint_id=?", (sprint_id,)
        ).fetchone()[0]
    })

# -- Telemetry dashboard (bonus: shows all sessions)
@app.get("/api/telemetry")
def telemetry():
    db = get_db()
    rows = db.execute("""
        SELECT s.sprint_id, s.agent_id, m.title, s.start_timestamp,
               s.end_timestamp, s.tab_switch_count, s.completion_status,
               s.card_dwell_json, l.quiz_session_id
        FROM SprintSessions s
        JOIN MicroModules m ON s.module_id = m.module_id
        LEFT JOIN LearningJourney_Map l ON s.sprint_id = l.sprint_id
        ORDER BY s.start_timestamp DESC
        LIMIT 50
    """).fetchall()
    results = []
    for r in rows:
        row = dict(r)
        row["card_dwell_json"] = json.loads(row["card_dwell_json"] or "[]")
        results.append(row)
    return jsonify(results)


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5050)
