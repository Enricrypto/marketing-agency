"""
Marketing OS — Database Layer (Phase 4)
SQLite connection manager y migraciones para marketing_os.db.

Tablas:
    workflows         — Ejecuciones de marketing (blog, landing, campaign)
    steps             — Cada llamada AI dentro de un workflow
    content_outputs   — Contenido generado y guardado
    evaluations       — Scores de calidad automáticos
    performance_metrics — Métricas importadas desde analytics (futuro)
    pages               — Registro de páginas locales SEO (Phase 2)
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

# ── Ubicación de la base de datos ─────────────────────────────────────────────
_BASE_DIR = Path(__file__).parent
DB_PATH   = _BASE_DIR / "state" / "marketing_os.db"


# ── Conexión ──────────────────────────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    """Abre una conexión SQLite con row_factory y foreign keys activados."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")  # mejor concurrencia
    return conn


@contextmanager
def db():
    """
    Context manager que provee una conexión SQLite con auto-commit y rollback.

    Uso:
        with db() as conn:
            conn.execute("INSERT INTO ...")
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Migraciones / Init ────────────────────────────────────────────────────────

_SCHEMA = """
-- Ejecuciones de workflows de marketing
CREATE TABLE IF NOT EXISTS workflows (
    id               TEXT PRIMARY KEY,
    type             TEXT NOT NULL,         -- blog_post | landing_page | seasonal_campaign
    topic            TEXT,                  -- Tema o nombre de campaña
    target_keyword   TEXT,                  -- Keyword SEO objetivo
    city             TEXT DEFAULT 'Santiago',
    status           TEXT DEFAULT 'running',-- running | completed | failed
    started_at       DATETIME NOT NULL,
    finished_at      DATETIME
);

-- Pasos individuales de AI dentro de un workflow
CREATE TABLE IF NOT EXISTS steps (
    id           TEXT PRIMARY KEY,
    workflow_id  TEXT NOT NULL,
    step_name    TEXT NOT NULL,             -- keyword_research | outline | writing | evaluation
    agent_name   TEXT,                      -- Nombre del agente de marketing
    status       TEXT DEFAULT 'running',    -- running | completed | failed
    duration_ms  INTEGER,
    token_input  INTEGER DEFAULT 0,
    token_output INTEGER DEFAULT 0,
    cost_usd     REAL    DEFAULT 0.0,
    created_at   DATETIME NOT NULL,
    FOREIGN KEY (workflow_id) REFERENCES workflows(id)
);

-- Contenido generado y almacenado
CREATE TABLE IF NOT EXISTS content_outputs (
    id               TEXT PRIMARY KEY,
    workflow_id      TEXT NOT NULL,
    content_type     TEXT NOT NULL,         -- blog | landing | campaign | ad_copy
    title            TEXT,
    meta_description TEXT,
    content          TEXT,
    word_count       INTEGER DEFAULT 0,
    created_at       DATETIME NOT NULL
);

-- Evaluaciones automáticas de calidad (AI scoring)
CREATE TABLE IF NOT EXISTS evaluations (
    id                    TEXT PRIMARY KEY,
    workflow_id           TEXT NOT NULL,
    seo_score             INTEGER DEFAULT 0,
    readability_score     INTEGER DEFAULT 0,
    conversion_score      INTEGER DEFAULT 0,
    local_relevance_score INTEGER DEFAULT 0,
    overall_score         REAL    DEFAULT 0.0,
    notes                 TEXT,
    created_at            DATETIME NOT NULL
);

-- Métricas de performance reales (importadas desde GA4, Search Console, etc.)
CREATE TABLE IF NOT EXISTS performance_metrics (
    id                 TEXT PRIMARY KEY,
    workflow_id        TEXT NOT NULL,
    page_views         INTEGER DEFAULT 0,
    avg_time_on_page   REAL    DEFAULT 0.0,
    bounce_rate        REAL    DEFAULT 0.0,
    conversions        INTEGER DEFAULT 0,
    revenue_generated  REAL    DEFAULT 0.0,
    recorded_at        DATETIME NOT NULL
);

-- Páginas locales SEO (Phase 2 — Programmatic Local SEO Expansion)
CREATE TABLE IF NOT EXISTS pages (
    page_id       TEXT PRIMARY KEY,
    service_slug  TEXT NOT NULL,
    service_name  TEXT NOT NULL,
    commune_slug  TEXT NOT NULL,
    commune_name  TEXT NOT NULL,
    keyword       TEXT NOT NULL,
    status        TEXT DEFAULT 'pending',  -- pending | generated | published | failed
    workflow_id   TEXT,
    created_at    TEXT NOT NULL
);

-- Registro de workflows ya enviados a Google Sheets (evita duplicados)
CREATE TABLE IF NOT EXISTS sheet_syncs (
    workflow_id  TEXT NOT NULL,
    sheet_name   TEXT NOT NULL,
    synced_at    DATETIME NOT NULL,
    PRIMARY KEY (workflow_id, sheet_name)
);

-- Newsletter issues (cada envío semanal)
CREATE TABLE IF NOT EXISTS newsletter_issues (
    id              TEXT PRIMARY KEY,
    issue_number    INTEGER NOT NULL UNIQUE,
    focus_commune   TEXT NOT NULL,
    subject_line    TEXT,
    preview_text    TEXT,
    status          TEXT DEFAULT 'draft',  -- draft | sent | failed
    recipient_count INTEGER DEFAULT 0,
    workflow_id     TEXT,
    sent_at         DATETIME,
    created_at      DATETIME NOT NULL
);

-- Índices para queries de analytics
CREATE INDEX IF NOT EXISTS idx_steps_workflow       ON steps(workflow_id);
CREATE INDEX IF NOT EXISTS idx_outputs_workflow     ON content_outputs(workflow_id);
CREATE INDEX IF NOT EXISTS idx_evals_workflow       ON evaluations(workflow_id);
CREATE INDEX IF NOT EXISTS idx_metrics_workflow     ON performance_metrics(workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflows_status     ON workflows(status, started_at);
CREATE INDEX IF NOT EXISTS idx_outputs_type         ON content_outputs(content_type, created_at);
CREATE INDEX IF NOT EXISTS idx_sheet_syncs          ON sheet_syncs(sheet_name, synced_at);
CREATE INDEX IF NOT EXISTS idx_pages_status         ON pages(status, created_at);
CREATE INDEX IF NOT EXISTS idx_pages_service        ON pages(service_slug, commune_slug);
CREATE INDEX IF NOT EXISTS idx_newsletter_issues    ON newsletter_issues(status, created_at);
"""


def init_db() -> None:
    """
    Crea todas las tablas e índices si no existen.
    Seguro para llamar múltiples veces (idempotente).
    """
    with db() as conn:
        conn.executescript(_SCHEMA)
    print(f"[db] Database ready: {DB_PATH}")


# ── Helpers de inserción ──────────────────────────────────────────────────────

def insert_row(table: str, row: dict) -> None:
    """
    Inserta una fila en la tabla indicada.
    Las claves del dict corresponden a columnas.
    """
    cols        = ", ".join(row.keys())
    placeholders = ", ".join("?" * len(row))
    with db() as conn:
        conn.execute(
            f"INSERT INTO {table} ({cols}) VALUES ({placeholders})",
            list(row.values()),
        )


def update_row(table: str, row_id: str, updates: dict) -> None:
    """
    Actualiza columnas de una fila identificada por id.
    """
    set_clause = ", ".join(f"{k}=?" for k in updates.keys())
    with db() as conn:
        conn.execute(
            f"UPDATE {table} SET {set_clause} WHERE id=?",
            [*updates.values(), row_id],
        )


def fetch_all(query: str, params: tuple = ()) -> list[dict]:
    """Ejecuta una SELECT y retorna lista de dicts."""
    with db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


# ── Sheet sync tracking ───────────────────────────────────────────────────────

def mark_synced(workflow_ids: list[str], sheet_name: str) -> None:
    """Records workflow IDs as synced to a given sheet. Safe to call multiple times."""
    from datetime import datetime
    now = datetime.utcnow().isoformat()
    with db() as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO sheet_syncs (workflow_id, sheet_name, synced_at) VALUES (?, ?, ?)",
            [(wid, sheet_name, now) for wid in workflow_ids],
        )


def already_synced_ids(sheet_name: str) -> set[str]:
    """Returns the set of workflow IDs already synced to a given sheet."""
    rows = fetch_all(
        "SELECT workflow_id FROM sheet_syncs WHERE sheet_name = ?",
        (sheet_name,),
    )
    return {r["workflow_id"] for r in rows}


# ── CLI básico ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    print("[db] Tablas creadas:")
    rows = fetch_all("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    for r in rows:
        print(f"  • {r['name']}")
