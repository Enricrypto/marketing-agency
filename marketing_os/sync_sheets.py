#!/usr/bin/env python3
"""
Marketing OS — Sync Workflow Results to Google Sheets

Reads completed workflows from SQLite and pushes them to two tracking spreadsheets:
  - "WashDog - Landing Pages"  → all landing_page workflows
  - "WashDog - Blog Posts"     → all blog_post workflows

Usage:
    python sync_sheets.py --init              # create both sheets with headers (run once)
    python sync_sheets.py --all               # sync all completed workflows
    python sync_sheets.py --all --type landing
    python sync_sheets.py --all --type blog
    python sync_sheets.py --workflow-id <uuid>
    python sync_sheets.py --all --dry-run     # preview without writing to Sheets
"""

import argparse
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from db import fetch_all, mark_synced, already_synced_ids


# ── Sheet names (one spreadsheet per content type) ────────────────────────────

SHEET_LANDINGS = "WashDog - Landing Pages"
SHEET_BLOGS    = "WashDog - Blog Posts"

# ── Column headers ─────────────────────────────────────────────────────────────

LANDING_HEADERS = [
    "Servicio", "Comuna", "URL Canónica", "Keyword",
    "Workflow ID", "SEO", "Conversión", "Legibilidad", "Local", "Overall",
    "Timestamp",
]

BLOG_HEADERS = [
    "Tema", "Ciudad", "URL", "Keyword",
    "Workflow ID", "SEO", "Legibilidad", "Conversión", "Local", "Overall",
    "Timestamp",
]

# ── Canonical URL map ─────────────────────────────────────────────────────────

_CANONICAL_URLS: dict[str, str] = {
    "baño completo":                  "/servicios/bano-completo",
    "corte de pelo canino":           "/servicios/corte-pelo-canino",
    "tratamiento antipulgas":         "/servicios/antipulgas",
    "antipulgas":                     "/servicios/antipulgas",
    "deslanado":                      "/servicios/deslanado",
    "corte y lima de uñas":           "/servicios/corte-unas",
    "corte de uñas":                  "/servicios/corte-unas",
    "peluquería canina ñuñoa":        "/servicios/peluqueria-canina-nunoa",
    "auto lavado perros ñuñoa":       "/servicios/auto-lavado-perros-nunoa",
    "peluquería gatos ñuñoa":         "/servicios/peluqueria-gatos-nunoa",
    "precio peluquería ñuñoa":        "/servicios/precio-peluqueria-nunoa",
}


def _canonical_url(topic: str, city: str = "") -> str:
    """Returns the canonical URL for a landing page.

    Checks the static map first; if not found, derives the slug programmatically
    from 'topic + city' (for Phase 2 programmatic pages).

    Example: topic="peluquería canina", city="Providencia"
             → "/servicios/peluqueria-canina-providencia"
    """
    key = topic.lower().strip()
    if key in _CANONICAL_URLS:
        return _CANONICAL_URLS[key]

    if city:
        normalized_topic = unicodedata.normalize("NFD", topic)
        ascii_topic = normalized_topic.encode("ascii", "ignore").decode("ascii")
        slug_topic = re.sub(r"\s+", "-", ascii_topic.lower().strip())
        slug_topic = re.sub(r"[^a-z0-9\-]", "", slug_topic).strip("-")

        normalized_city = unicodedata.normalize("NFD", city)
        ascii_city = normalized_city.encode("ascii", "ignore").decode("ascii")
        slug_city = re.sub(r"\s+", "-", ascii_city.lower().strip())
        slug_city = re.sub(r"[^a-z0-9\-]", "", slug_city).strip("-")

        return f"/servicios/{slug_topic}-{slug_city}"

    return ""


def _blog_slug(keyword: str) -> str:
    """Derives a /blog/<slug> URL from a keyword string.

    Steps: normalize accents → lowercase → strip → spaces to hyphens → drop
    non-alphanumeric chars.

    Example: "Peluquería canina Ñuñoa" → "/blog/peluqueria-canina-nunoa"
    """
    normalized = unicodedata.normalize("NFD", keyword)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    slug = ascii_only.lower().strip()
    slug = re.sub(r"[\s]+", "-", slug)
    slug = re.sub(r"[^a-z0-9\-]", "", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return f"/blog/{slug}"


# ── SQLite queries ─────────────────────────────────────────────────────────────

def fetch_rows(
    workflow_id:  str | None = None,
    content_type: str | None = None,
    best_only:    bool       = False,
) -> list[dict]:
    """
    Fetches completed workflows joined with their evaluation scores.

    Args:
        workflow_id:   Filter to a single workflow UUID (optional).
        content_type:  "landing" or "blog" — maps to co.content_type (optional).
        best_only:     When True, returns only the highest-scoring workflow per
                       keyword (deduplicates runs of the same service/topic).

    Returns:
        List of dicts with all fields needed to build sheet rows.
    """
    filters: list[str] = ["w.status = 'completed'"]
    params:  list      = []

    if workflow_id:
        filters.append("w.id = ?")
        params.append(workflow_id)

    if content_type:
        filters.append("co.content_type = ?")
        params.append(content_type)

    where = " AND ".join(filters)

    all_rows = fetch_all(f"""
        SELECT
            w.id                  AS workflow_id,
            w.type                AS workflow_type,
            w.topic               AS topic,
            w.target_keyword      AS keyword,
            w.city                AS city,
            w.started_at          AS timestamp,
            co.content_type       AS content_type,
            co.title              AS title,
            COALESCE(e.seo_score,             "") AS seo_score,
            COALESCE(e.readability_score,     "") AS readability_score,
            COALESCE(e.conversion_score,      "") AS conversion_score,
            COALESCE(e.local_relevance_score, "") AS local_relevance_score,
            COALESCE(e.overall_score,         "") AS overall_score
        FROM workflows w
        LEFT JOIN content_outputs co ON co.workflow_id = w.id
        LEFT JOIN evaluations     e  ON e.workflow_id  = w.id
        WHERE {where}
        ORDER BY w.started_at DESC
    """, tuple(params))

    if not best_only:
        return all_rows

    # Keep only the highest overall_score per (topic, city) — deduplicates re-runs
    # of the same page without collapsing different communes into one row.
    seen: dict[tuple, dict] = {}
    for row in all_rows:
        topic = (row.get("keyword") or row.get("topic") or "").lower().strip()
        city  = (row.get("city") or "").lower().strip()
        key   = (topic, city)
        score = float(row.get("overall_score") or 0)
        if key not in seen or score > float(seen[key].get("overall_score") or 0):
            seen[key] = row
    return list(seen.values())


# ── Row builders ──────────────────────────────────────────────────────────────

def _build_landing_row(row: dict) -> list:
    topic = row.get("topic", "")
    city  = row.get("city", "Santiago")
    return [
        topic,
        city,
        _canonical_url(topic, city),
        row.get("keyword",             ""),
        row.get("workflow_id",         "")[:8],
        row.get("seo_score",           ""),
        row.get("conversion_score",    ""),
        row.get("readability_score",   ""),
        row.get("local_relevance_score", ""),
        row.get("overall_score",       ""),
        row.get("timestamp",           ""),
    ]


def _build_blog_row(row: dict) -> list:
    return [
        row.get("topic",               ""),
        row.get("city",                "Santiago"),
        _blog_slug(row.get("keyword", "") or row.get("topic", "")),
        row.get("keyword",             ""),
        row.get("workflow_id",         "")[:8],
        row.get("seo_score",           ""),
        row.get("readability_score",   ""),
        row.get("conversion_score",    ""),
        row.get("local_relevance_score", ""),
        row.get("overall_score",       ""),
        row.get("timestamp",           ""),
    ]


# ── Sheets helpers ────────────────────────────────────────────────────────────

def _get_append_to_sheet():
    """Import append_to_sheet lazily so the script works without credentials for --dry-run."""
    try:
        from workspace.api import append_to_sheet
        return append_to_sheet
    except Exception as e:
        print(f"[sync] Cannot import workspace.api: {e}")
        print("[sync] Make sure workspace/credentials.json exists and dependencies are installed.")
        sys.exit(1)


def init_sheets() -> None:
    """
    Creates both tracking spreadsheets with header rows.
    Run this once before first sync. Safe to re-run (appends a duplicate header row).
    """
    append_to_sheet = _get_append_to_sheet()

    print(f"[sync] Initialising sheet: {SHEET_LANDINGS}")
    append_to_sheet(SHEET_LANDINGS, [LANDING_HEADERS])

    print(f"[sync] Initialising sheet: {SHEET_BLOGS}")
    append_to_sheet(SHEET_BLOGS, [BLOG_HEADERS])

    print("[sync] Both sheets created. Run --all to populate with existing data.")


# ── Main sync ─────────────────────────────────────────────────────────────────

def sync(
    workflow_id:  str | None = None,
    content_type: str | None = None,
    dry_run:      bool       = False,
    best_only:    bool       = False,
    force:        bool       = False,
) -> None:
    """
    Fetches rows from SQLite and appends them to the appropriate Google Sheet.

    Args:
        workflow_id:   Single workflow to sync (optional).
        content_type:  "landing" or "blog" (optional — both if None).
        dry_run:       Print rows without writing to Sheets.
        best_only:     Only sync the highest-scoring run per keyword (no duplicates).
        force:         Skip deduplication — re-sync all rows regardless of prior syncs.
    """
    types_to_sync = [content_type] if content_type else ["landing", "blog"]

    for ct in types_to_sync:
        rows = fetch_rows(workflow_id=workflow_id, content_type=ct, best_only=best_only)

        if not rows:
            print(f"[sync] No completed {ct} workflows found.")
            continue

        sheet_name = SHEET_LANDINGS if ct == "landing" else SHEET_BLOGS

        # Filter out already-synced workflow IDs unless --force is set
        if not force:
            synced = already_synced_ids(sheet_name)
            new_rows = [r for r in rows if r["workflow_id"] not in synced]
            skipped  = len(rows) - len(new_rows)
            if skipped:
                print(f"[sync] Skipping {skipped} already-synced row(s) for '{sheet_name}' (use --force to re-sync)")
            rows = new_rows

        if not rows:
            print(f"[sync] Nothing new to sync for '{sheet_name}'.")
            continue

        build_row = _build_landing_row if ct == "landing" else _build_blog_row
        data_rows = [build_row(r) for r in rows]

        print(f"\n[sync] {ct.upper()} → '{sheet_name}' ({len(data_rows)} row(s))")
        for dr in data_rows:
            url_col = dr[2] if dr[2] else "(no url)"
            print(f"  {dr[0]:<40} | {url_col:<45} | overall={dr[9]}")

        if dry_run:
            print("[sync] --dry-run: skipping write.")
            continue

        append_to_sheet = _get_append_to_sheet()
        try:
            append_to_sheet(sheet_name, data_rows)
            if not force:
                mark_synced([r["workflow_id"] for r in rows], sheet_name)
        except Exception as e:
            print(f"[sync] Error writing to '{sheet_name}': {e}")
            sys.exit(1)

    if not dry_run:
        print("\n[sync] Sync complete.")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync Marketing OS workflow results to Google Sheets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python sync_sheets.py --init                     # first-time setup
  python sync_sheets.py --all                      # sync all completed workflows
  python sync_sheets.py --all --type landing       # landing pages only
  python sync_sheets.py --all --type blog          # blog posts only
  python sync_sheets.py --workflow-id abc12345     # single workflow
  python sync_sheets.py --all --dry-run            # preview without writing
        """,
    )

    parser.add_argument(
        "--init", action="store_true",
        help="Create both sheets with header rows (run once before first sync)",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Sync all completed workflows in the DB",
    )
    parser.add_argument(
        "--workflow-id",
        help="Sync a single workflow by ID (or ID prefix)",
    )
    parser.add_argument(
        "--type", choices=["landing", "blog"],
        help="Limit sync to one content type (default: both)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview rows without writing to Google Sheets",
    )
    parser.add_argument(
        "--best-only", action="store_true",
        help="Only sync the highest-scoring run per keyword (deduplicates multiple runs)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-sync all rows, ignoring the already-synced registry",
    )

    args = parser.parse_args()

    if args.init:
        init_sheets()
        return

    if not args.all and not args.workflow_id:
        parser.error("Provide --all or --workflow-id <id>")

    sync(
        workflow_id  = args.workflow_id,
        content_type = args.type,
        dry_run      = args.dry_run,
        best_only    = args.best_only,
        force        = args.force,
    )


if __name__ == "__main__":
    main()
