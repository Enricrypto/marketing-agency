"""
Marketing OS — Page Registry (Phase 2)
Helper functions for the `pages` table.

Tracks which service × commune combinations have been generated, preventing
duplicate workflow runs and enabling safe batch deployment.

Status flow:
    pending → generated → published
                       ↘ failed
"""

from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from db import fetch_all, db


# ── Table init ────────────────────────────────────────────────────────────────

def create_pages_table() -> None:
    """Ensures the pages table exists. Called automatically by init_db()."""
    # Table is created by db.init_db() via _SCHEMA — this is a no-op guard.
    from db import init_db
    init_db()


# ── Write helpers ─────────────────────────────────────────────────────────────

def register_page(
    service_slug: str,
    service_name: str,
    commune_slug: str,
    commune_name: str,
    keyword: str,
) -> str | None:
    """
    Inserts a new page into the registry with status='pending'.
    Returns the page_id if inserted, None if the page already exists.

    The page_id is deterministic: "{service_slug}__{commune_slug}" so it can
    be computed without a DB lookup.
    """
    page_id = f"{service_slug}__{commune_slug}"
    now = datetime.now(timezone.utc).isoformat()

    with db() as conn:
        existing = conn.execute(
            "SELECT page_id FROM pages WHERE page_id = ?", (page_id,)
        ).fetchone()

        if existing:
            return None  # Already registered

        conn.execute(
            """
            INSERT INTO pages
                (page_id, service_slug, service_name, commune_slug, commune_name,
                 keyword, status, workflow_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', NULL, ?)
            """,
            (page_id, service_slug, service_name, commune_slug, commune_name,
             keyword, now),
        )
    return page_id


def mark_page_generated(page_id: str, workflow_id: str) -> None:
    """Updates a page to status='generated' and stores the workflow_id."""
    with db() as conn:
        conn.execute(
            "UPDATE pages SET status='generated', workflow_id=? WHERE page_id=?",
            (workflow_id, page_id),
        )


def mark_page_failed(page_id: str) -> None:
    """Updates a page to status='failed'."""
    with db() as conn:
        conn.execute(
            "UPDATE pages SET status='failed' WHERE page_id=?",
            (page_id,),
        )


def mark_page_published(page_id: str) -> None:
    """Updates a page to status='published'."""
    with db() as conn:
        conn.execute(
            "UPDATE pages SET status='published' WHERE page_id=?",
            (page_id,),
        )


# ── Read helpers ──────────────────────────────────────────────────────────────

def page_exists(service_slug: str, commune_slug: str) -> bool:
    """Returns True if a page for this service+commune combination exists."""
    page_id = f"{service_slug}__{commune_slug}"
    rows = fetch_all(
        "SELECT 1 FROM pages WHERE page_id = ?",
        (page_id,),
    )
    return len(rows) > 0


def get_pending_pages(limit: int | None = None) -> list[dict]:
    """Returns pages with status='pending', ordered by creation date."""
    query = "SELECT * FROM pages WHERE status = 'pending' ORDER BY created_at ASC"
    if limit:
        query += f" LIMIT {limit}"
    return fetch_all(query)


def get_all_pages() -> list[dict]:
    """Returns all pages ordered by service and commune."""
    return fetch_all(
        "SELECT * FROM pages ORDER BY service_slug, commune_slug"
    )


def get_pages_summary() -> dict:
    """Returns counts per status."""
    rows = fetch_all(
        "SELECT status, COUNT(*) as count FROM pages GROUP BY status"
    )
    return {r["status"]: r["count"] for r in rows}
