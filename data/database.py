import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "teleassist.db")
RETENTION_STATUSES = {"retained", "not_retained", "not_applicable"}


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
            resultado   TEXT DEFAULT 'sin_contacto',
            notas       TEXT,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sesion_id) REFERENCES sesiones(id)
        )
    """)
    _migrate_llamadas_schema(c)

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

    conn.commit()
    conn.close()


def _migrate_llamadas_schema(cursor):
    cursor.execute("PRAGMA table_info(llamadas)")
    columns = {row["name"] for row in cursor.fetchall()}
    if "retention_status" not in columns:
        cursor.execute(
            "ALTER TABLE llamadas ADD COLUMN retention_status TEXT DEFAULT 'not_applicable'"
        )
    cursor.execute("""
        UPDATE llamadas
        SET retention_status = 'not_applicable'
        WHERE retention_status IS NULL OR retention_status = ''
    """)


def normalize_retention_status(data: dict) -> str:
    esta_activo = data.get("esta_activo", "na")
    contesto = data.get("contesto", "no")
    requested = data.get("retention_status")

    if esta_activo != "activo" or contesto != "si":
        return "not_applicable"
    if requested in ("retained", "not_retained"):
        return requested
    return "not_retained"


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
        args_lead = (sid,)
    else:
        today = datetime.now().strftime("%Y-%m-%d")
        where = "AND ll.fecha = ?"
        args_ll = (today,)
        args_lead = (today,)

    c.execute(f"SELECT COUNT(*) as t FROM llamadas ll WHERE 1=1 {where}", args_ll)
    marcadas = c.fetchone()["t"]

    c.execute(f"SELECT COUNT(*) as t FROM llamadas ll WHERE esta_activo='activo' {where}", args_ll)
    activos = c.fetchone()["t"]

    c.execute(f"SELECT COUNT(*) as t FROM llamadas ll WHERE contesto='si' {where}", args_ll)
    contestaron = c.fetchone()["t"]

    c.execute(f"SELECT COUNT(*) as t FROM llamadas ll WHERE retention_status='retained' {where}", args_ll)
    retained = c.fetchone()["t"]

    if sid:
        c.execute("SELECT COUNT(*) as t FROM leads WHERE sesion_id = ?", args_lead)
    else:
        c.execute("SELECT COUNT(*) as t FROM leads l JOIN llamadas ll ON l.llamada_id=ll.id WHERE ll.fecha=?", args_lead)
    leads_count = c.fetchone()["t"]

    conn.close()
    conv = round(leads_count / contestaron * 100) if contestaron else 0
    retention_rate = round(retained / contestaron * 100) if contestaron else 0
    retained_conversion = round(leads_count / retained * 100) if retained else 0
    return {
        "marcadas": marcadas,
        "activos": activos,
        "contestaron": contestaron,
        "retained": retained,
        "leads": leads_count,
        "conversion": conv,
        "retention_rate": retention_rate,
        "retained_conversion": retained_conversion,
    }


# ── Llamadas ───────────────────────────────────────────────────────────────────

def guardar_llamada(data: dict, sesion_id: int | None = None) -> int:
    now = datetime.now()
    retention_status = normalize_retention_status(data)
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO llamadas (
            sesion_id, numero, fecha, hora, tuvo_tono, esta_activo, contesto,
            retention_status, resultado, notas
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        sesion_id,
        data.get("numero"),
        now.strftime("%Y-%m-%d"),
        now.strftime("%H:%M:%S"),
        1 if data.get("tuvo_tono") else 0,
        data.get("esta_activo", "na"),
        data.get("contesto", "no"),
        retention_status,
        data.get("resultado", "sin_contacto"),
        data.get("notas", ""),
    ))
    lid = c.lastrowid
    conn.commit()
    conn.close()
    return lid


def update_llamada(llamada_id: int, data: dict):
    retention_status = normalize_retention_status(data)
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE llamadas SET
            tuvo_tono=?, esta_activo=?, contesto=?, retention_status=?,
            resultado=?, notas=?
        WHERE id=?
    """, (
        1 if data.get("tuvo_tono") else 0,
        data.get("esta_activo", "na"),
        data.get("contesto", "no"),
        retention_status,
        data.get("resultado", "sin_contacto"),
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
               retention_status, resultado, notas
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
    c.execute("DELETE FROM leads WHERE id=?", (lead_id,))
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
