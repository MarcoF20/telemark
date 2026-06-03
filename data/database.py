import sqlite3
import os
import shutil
import sys
from datetime import datetime

APP_NAME = "TeleAssist"


def _source_db_path():
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "data", "teleassist.db")
    return os.path.join(os.path.dirname(__file__), "teleassist.db")


def _user_data_dir():
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, APP_NAME)
    if sys.platform == "darwin":
        return os.path.join(
            os.path.expanduser("~"), "Library", "Application Support", APP_NAME
        )
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(
        os.path.expanduser("~"), ".local", "share"
    )
    return os.path.join(base, APP_NAME.lower())


def _database_path():
    if not getattr(sys, "frozen", False):
        return _source_db_path()

    data_dir = _user_data_dir()
    os.makedirs(data_dir, exist_ok=True)
    db_path = os.path.join(data_dir, "teleassist.db")
    source_path = _source_db_path()
    if not os.path.exists(db_path) and os.path.exists(source_path):
        shutil.copy2(source_path, db_path)
    return db_path


DB_PATH = _database_path()
LINE_STATUSES = {"alive", "dead"}
ANSWER_STATUSES = {"answered", "not_answered", "voicemail", "not_applicable"}
RETENTION_STATUSES = {"retained", "not_retained", "not_applicable"}
LEAD_STATUSES = {"lead", "not_lead", "not_applicable"}
CALLBACK_TAGS = {"none", "voicemail_retry", "call_later", "follow_up"}


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS sesiones (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            inicio      TEXT NOT NULL,
            fin         TEXT,
            marcadas    INTEGER DEFAULT 0,
            activos     INTEGER DEFAULT 0,
            contestaron INTEGER DEFAULT 0,
            leads       INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS llamadas (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            sesion_id   INTEGER,
            numero      TEXT NOT NULL,
            fecha       TEXT NOT NULL,
            hora        TEXT NOT NULL,
            tuvo_tono   INTEGER DEFAULT 0,
            esta_activo TEXT,
            contesto    TEXT,
            retention_status TEXT DEFAULT 'not_applicable',
            line_status TEXT DEFAULT 'dead',
            answer_status TEXT DEFAULT 'not_applicable',
            lead_status TEXT DEFAULT 'not_applicable',
            callback_tag TEXT DEFAULT 'none',
            resultado   TEXT DEFAULT 'sin_contacto',
            notas       TEXT,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sesion_id) REFERENCES sesiones(id)
        )
    """)
    _migrate_llamadas_schema(c)
    _create_llamadas_indexes(c)

    c.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            llamada_id          INTEGER,
            sesion_id           INTEGER,
            numero              TEXT NOT NULL,
            nombre              TEXT,
            empresa             TEXT,
            email               TEXT,
            interes             TEXT DEFAULT 'medio',
            es_decisor          TEXT,
            notas               TEXT,
            fecha               TEXT,
            hora                TEXT,
            -- Perfilación funeraria
            miembros_familia    INTEGER,
            a_proteger          INTEGER,
            decide_solo         TEXT,
            forma_pago          TEXT,
            producto_interes    TEXT,
            cementerio_nicho    TEXT,
            -- Seguimiento
            agendar_llamada     INTEGER DEFAULT 0,
            fecha_seguimiento   TEXT,
            hora_seguimiento    TEXT,
            seguimiento_notas   TEXT,
            perfilado           INTEGER DEFAULT 0,
            created_at          TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at          TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (llamada_id) REFERENCES llamadas(id),
            FOREIGN KEY (sesion_id) REFERENCES sesiones(id)
        )
    """)
    _create_leads_indexes(c)
    _sync_call_lead_status(c)

    conn.commit()
    conn.close()


def _migrate_llamadas_schema(cursor):
    cursor.execute("PRAGMA table_info(llamadas)")
    columns = {row["name"] for row in cursor.fetchall()}
    if "retention_status" not in columns:
        cursor.execute(
            "ALTER TABLE llamadas ADD COLUMN retention_status TEXT DEFAULT 'not_applicable'"
        )
    if "line_status" not in columns:
        cursor.execute(
            "ALTER TABLE llamadas ADD COLUMN line_status TEXT DEFAULT 'dead'"
        )
    if "answer_status" not in columns:
        cursor.execute(
            "ALTER TABLE llamadas ADD COLUMN answer_status TEXT DEFAULT 'not_applicable'"
        )
    if "lead_status" not in columns:
        cursor.execute(
            "ALTER TABLE llamadas ADD COLUMN lead_status TEXT DEFAULT 'not_applicable'"
        )
    if "callback_tag" not in columns:
        cursor.execute(
            "ALTER TABLE llamadas ADD COLUMN callback_tag TEXT DEFAULT 'none'"
        )
    cursor.execute("""
        UPDATE llamadas
        SET retention_status = 'not_applicable'
        WHERE retention_status IS NULL OR retention_status = ''
    """)
    cursor.execute("""
        UPDATE llamadas
        SET line_status = CASE
            WHEN esta_activo = 'activo' THEN 'alive'
            WHEN tuvo_tono = 1 THEN 'alive'
            WHEN contesto IN ('si', 'buzon') THEN 'alive'
            ELSE 'dead'
        END
    """)
    cursor.execute("""
        UPDATE llamadas
        SET answer_status = CASE
            WHEN line_status = 'dead' THEN 'not_applicable'
            WHEN contesto = 'si' THEN 'answered'
            WHEN contesto = 'buzon' THEN 'voicemail'
            ELSE 'not_answered'
        END
    """)
    cursor.execute("""
        UPDATE llamadas
        SET retention_status = CASE
            WHEN resultado = 'lead_capturado' THEN 'retained'
            WHEN answer_status = 'answered' AND retention_status = 'retained'
                THEN 'retained'
            WHEN answer_status = 'answered' AND retention_status = 'not_retained'
                THEN 'not_retained'
            WHEN answer_status = 'answered'
                THEN 'not_retained'
            ELSE 'not_applicable'
        END
    """)
    cursor.execute("""
        UPDATE llamadas
        SET lead_status = CASE
            WHEN resultado = 'lead_capturado' THEN 'lead'
            WHEN retention_status = 'retained' THEN 'not_lead'
            ELSE 'not_applicable'
        END
    """)
    cursor.execute("""
        UPDATE llamadas
        SET callback_tag = CASE
            WHEN answer_status = 'voicemail' THEN 'voicemail_retry'
            WHEN callback_tag IN ('call_later', 'follow_up') THEN callback_tag
            ELSE 'none'
        END
    """)


def _create_llamadas_indexes(cursor):
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_llamadas_sesion_id ON llamadas(sesion_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_llamadas_numero ON llamadas(numero)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_llamadas_created_at ON llamadas(created_at)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_llamadas_fecha ON llamadas(fecha)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_llamadas_line_status ON llamadas(line_status)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_llamadas_answer_status ON llamadas(answer_status)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_llamadas_retention_status ON llamadas(retention_status)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_llamadas_lead_status ON llamadas(lead_status)"
    )


def _create_leads_indexes(cursor):
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_leads_sesion_id ON leads(sesion_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_leads_llamada_id ON leads(llamada_id)"
    )


def _sync_call_lead_status(cursor):
    cursor.execute("""
        UPDATE llamadas
        SET lead_status = 'lead', resultado = 'lead_capturado'
        WHERE id IN (SELECT llamada_id FROM leads WHERE llamada_id IS NOT NULL)
    """)


def normalize_call_state(data: dict) -> dict:
    line_status = data.get("line_status")
    answer_status = data.get("answer_status")

    if line_status not in LINE_STATUSES:
        esta_activo = data.get("esta_activo")
        if esta_activo == "activo" or data.get("tuvo_tono") or data.get("contesto") in ("si", "buzon"):
            line_status = "alive"
        else:
            line_status = "dead"

    if line_status == "dead":
        answer_status = "not_applicable"
    elif answer_status not in ANSWER_STATUSES or answer_status == "not_applicable":
        contesto = data.get("contesto")
        if contesto == "si":
            answer_status = "answered"
        elif contesto == "buzon":
            answer_status = "voicemail"
        else:
            answer_status = "not_answered"

    retention_status = data.get("retention_status")
    if answer_status == "answered":
        if retention_status not in ("retained", "not_retained"):
            retention_status = "not_retained"
    else:
        retention_status = "not_applicable"

    lead_status = data.get("lead_status")
    if retention_status == "retained":
        if lead_status not in ("lead", "not_lead"):
            lead_status = "not_lead"
    else:
        lead_status = "not_applicable"

    callback_tag = data.get("callback_tag")
    if callback_tag not in CALLBACK_TAGS:
        callback_tag = "voicemail_retry" if answer_status == "voicemail" else "none"

    return {
        "line_status": line_status,
        "answer_status": answer_status,
        "retention_status": retention_status,
        "lead_status": lead_status,
        "callback_tag": callback_tag,
        "tuvo_tono": line_status == "alive",
        "esta_activo": "activo" if line_status == "alive" else "fuera_servicio",
        "contesto": {
            "answered": "si",
            "voicemail": "buzon",
            "not_answered": "no",
            "not_applicable": "no",
        }[answer_status],
        "resultado": "lead_capturado" if lead_status == "lead" else "sin_contacto",
    }


def normalize_retention_status(data: dict) -> str:
    return normalize_call_state(data)["retention_status"]


# ── Config ─────────────────────────────────────────────────────────────────────

def get_config(key: str, default=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM config WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    return row["value"] if row else default


def set_config(key: str, value: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


# ── Sesiones ───────────────────────────────────────────────────────────────────

def iniciar_sesion() -> int:
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO sesiones (inicio) VALUES (?)", (now,))
    sid = c.lastrowid
    conn.commit()
    conn.close()
    set_config("sesion_activa", str(sid))
    return sid


def get_sesion_activa() -> int | None:
    val = get_config("sesion_activa")
    return int(val) if val else None


def cerrar_sesion(sid: int):
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("UPDATE sesiones SET fin = ? WHERE id = ?", (now, sid))
    conn.commit()
    conn.close()
    set_config("sesion_activa", "")


def get_stats_sesion(sid: int | None = None) -> dict:
    conn = get_connection()
    c = conn.cursor()

    if sid:
        where = "AND ll.sesion_id = ?"
        args_ll = (sid,)
    else:
        today = datetime.now().strftime("%Y-%m-%d")
        where = "AND ll.fecha = ?"
        args_ll = (today,)

    c.execute(f"SELECT COUNT(*) as t FROM llamadas ll WHERE 1=1 {where}", args_ll)
    marcadas = c.fetchone()["t"]

    c.execute(f"SELECT COUNT(*) as t FROM llamadas ll WHERE line_status='alive' {where}", args_ll)
    alive = c.fetchone()["t"]

    c.execute(f"SELECT COUNT(*) as t FROM llamadas ll WHERE line_status='dead' {where}", args_ll)
    dead = c.fetchone()["t"]

    c.execute(f"SELECT COUNT(*) as t FROM llamadas ll WHERE answer_status='answered' {where}", args_ll)
    answered = c.fetchone()["t"]

    c.execute(f"SELECT COUNT(*) as t FROM llamadas ll WHERE retention_status='retained' {where}", args_ll)
    retained = c.fetchone()["t"]

    c.execute(f"SELECT COUNT(*) as t FROM llamadas ll WHERE lead_status='lead' {where}", args_ll)
    leads_count = c.fetchone()["t"]

    conn.close()
    alive_rate = round(alive / marcadas * 100) if marcadas else 0
    answered_rate = round(answered / alive * 100) if alive else 0
    retention_rate = round(retained / answered * 100) if answered else 0
    retained_conversion = round(leads_count / retained * 100) if retained else 0
    return {
        "marcadas": marcadas,
        "activos": alive,
        "alive": alive,
        "dead": dead,
        "contestaron": answered,
        "answered": answered,
        "retained": retained,
        "leads": leads_count,
        "conversion": retained_conversion,
        "alive_rate": alive_rate,
        "answered_rate": answered_rate,
        "retention_rate": retention_rate,
        "lead_conversion_rate": retained_conversion,
        "retained_conversion": retained_conversion,
    }


# ── Llamadas ───────────────────────────────────────────────────────────────────

def guardar_llamada(data: dict, sesion_id: int | None = None) -> int:
    now = datetime.now()
    state = normalize_call_state(data)
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO llamadas (
            sesion_id, numero, fecha, hora, tuvo_tono, esta_activo, contesto,
            retention_status, line_status, answer_status, lead_status,
            callback_tag, resultado, notas
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        sesion_id,
        data.get("numero"),
        now.strftime("%Y-%m-%d"),
        now.strftime("%H:%M:%S"),
        1 if state["tuvo_tono"] else 0,
        state["esta_activo"],
        state["contesto"],
        state["retention_status"],
        state["line_status"],
        state["answer_status"],
        state["lead_status"],
        state["callback_tag"],
        state["resultado"],
        data.get("notas", ""),
    ))
    lid = c.lastrowid
    conn.commit()
    conn.close()
    return lid


def update_llamada(llamada_id: int, data: dict):
    state = normalize_call_state(data)
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE llamadas SET
            tuvo_tono=?, esta_activo=?, contesto=?, retention_status=?,
            line_status=?, answer_status=?, lead_status=?, callback_tag=?,
            resultado=?, notas=?
        WHERE id=?
    """, (
        1 if state["tuvo_tono"] else 0,
        state["esta_activo"],
        state["contesto"],
        state["retention_status"],
        state["line_status"],
        state["answer_status"],
        state["lead_status"],
        state["callback_tag"],
        state["resultado"],
        data.get("notas", ""),
        llamada_id,
    ))
    conn.commit()
    conn.close()


def delete_llamada(llamada_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM leads WHERE llamada_id=?", (llamada_id,))
    c.execute("DELETE FROM llamadas WHERE id=?", (llamada_id,))
    conn.commit()
    conn.close()


def get_all_llamadas():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT id, numero, fecha, hora, tuvo_tono, esta_activo, contesto,
               line_status, answer_status, retention_status, lead_status,
               callback_tag, resultado, notas
        FROM llamadas ORDER BY created_at DESC
    """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


# ── Leads ──────────────────────────────────────────────────────────────────────

def guardar_lead(data: dict, llamada_id: int, sesion_id: int | None = None) -> int:
    now = datetime.now()
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO leads (
            llamada_id, sesion_id, numero, nombre, empresa, email,
            interes, es_decisor, notas, fecha, hora,
            miembros_familia, a_proteger, decide_solo, forma_pago,
            producto_interes, cementerio_nicho,
            agendar_llamada, fecha_seguimiento, hora_seguimiento, seguimiento_notas,
            perfilado
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        llamada_id, sesion_id,
        data.get("numero"), data.get("nombre"), data.get("empresa"), data.get("email"),
        data.get("interes", "medio"), data.get("es_decisor"), data.get("notas"),
        now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"),
        data.get("miembros_familia"), data.get("a_proteger"),
        data.get("decide_solo"), data.get("forma_pago"),
        data.get("producto_interes"), data.get("cementerio_nicho"),
        1 if data.get("agendar_llamada") else 0,
        data.get("fecha_seguimiento"), data.get("hora_seguimiento"),
        data.get("seguimiento_notas"),
        1 if data.get("perfilado") else 0,
    ))
    lead_id = c.lastrowid
    c.execute("""
        UPDATE llamadas
        SET lead_status='lead', resultado='lead_capturado'
        WHERE id=?
    """, (llamada_id,))
    conn.commit()
    conn.close()
    return lead_id


def update_lead(lead_id: int, data: dict):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE leads SET
            numero=?, nombre=?, empresa=?, email=?,
            interes=?, es_decisor=?, notas=?,
            miembros_familia=?, a_proteger=?, decide_solo=?, forma_pago=?,
            producto_interes=?, cementerio_nicho=?,
            agendar_llamada=?, fecha_seguimiento=?, hora_seguimiento=?,
            seguimiento_notas=?, perfilado=?, updated_at=?
        WHERE id=?
    """, (
        data.get("numero"), data.get("nombre"), data.get("empresa"), data.get("email"),
        data.get("interes", "medio"), data.get("es_decisor"), data.get("notas"),
        data.get("miembros_familia"), data.get("a_proteger"),
        data.get("decide_solo"), data.get("forma_pago"),
        data.get("producto_interes"), data.get("cementerio_nicho"),
        1 if data.get("agendar_llamada") else 0,
        data.get("fecha_seguimiento"), data.get("hora_seguimiento"),
        data.get("seguimiento_notas"),
        1 if data.get("perfilado") else 0,
        now, lead_id,
    ))
    conn.commit()
    conn.close()


def delete_lead(lead_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT llamada_id FROM leads WHERE id=?", (lead_id,))
    row = c.fetchone()
    c.execute("DELETE FROM leads WHERE id=?", (lead_id,))
    if row and row["llamada_id"]:
        c.execute("""
            UPDATE llamadas
            SET lead_status = CASE
                    WHEN retention_status = 'retained' THEN 'not_lead'
                    ELSE 'not_applicable'
                END,
                resultado = 'sin_contacto'
            WHERE id=?
        """, (row["llamada_id"],))
    conn.commit()
    conn.close()


def get_lead_by_id(lead_id: int) -> dict | None:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM leads WHERE id=?", (lead_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_leads():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT id, nombre, numero, empresa, email, interes, es_decisor,
               fecha, hora, perfilado, agendar_llamada, fecha_seguimiento,
               hora_seguimiento, producto_interes, notas
        FROM leads ORDER BY created_at DESC
    """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_leads_recientes(limit=8):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT id, nombre, numero, interes, fecha, hora, perfilado, fecha_seguimiento
        FROM leads ORDER BY created_at DESC LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_leads_con_seguimiento():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT id, nombre, numero, interes, fecha_seguimiento, hora_seguimiento,
               seguimiento_notas, perfilado
        FROM leads
        WHERE agendar_llamada=1 AND fecha_seguimiento IS NOT NULL AND fecha_seguimiento != ''
        ORDER BY fecha_seguimiento ASC, hora_seguimiento ASC
    """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows
