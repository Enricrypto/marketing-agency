"""
Marketing OS — Database Layer (Phase 4)
SQLite connection manager y migraciones para marketing_os.db.

Tablas:
    workflows         — Ejecuciones de marketing (blog, landing, campaign)
    steps             — Cada llamada AI dentro de un workflow
    content_outputs   — Contenido generado y guardado
    evaluations       — Scores de calidad automáticos
    performance_metrics — Métricas importadas desde analytics (futuro)
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

-- Índices para queries de analytics
CREATE INDEX IF NOT EXISTS idx_steps_workflow     ON steps(workflow_id);
CREATE INDEX IF NOT EXISTS idx_outputs_workflow   ON content_outputs(workflow_id);
CREATE INDEX IF NOT EXISTS idx_evals_workflow     ON evaluations(workflow_id);
CREATE INDEX IF NOT EXISTS idx_metrics_workflow   ON performance_metrics(workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflows_status   ON workflows(status, started_at);
CREATE INDEX IF NOT EXISTS idx_outputs_type       ON content_outputs(content_type, created_at);
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


# ── CLI básico ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    print("[db] Tablas creadas:")
    rows = fetch_all("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    for r in rows:
        print(f"  • {r['name']}")
