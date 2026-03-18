#!/usr/bin/env python3
"""
Marketing OS — Sync GA4 + Search Console Analytics

Pulls real performance data for WashDog pages and writes to:
  - SQLite: performance_metrics table
  - Google Sheets: "WashDog - Analytics"

Usage:
    python sync_analytics.py --init               # create Analytics sheet with headers
    python sync_analytics.py --days 30            # last 30 days (default)
    python sync_analytics.py --days 7
    python sync_analytics.py --dry-run            # preview without writing
    python sync_analytics.py --ga4-only
    python sync_analytics.py --sc-only

Required env vars (.env):
    GA4_PROPERTY_ID          e.g. 525098054
    SEARCH_CONSOLE_SITE_URL  e.g. https://www.washdog.cl/
"""

import argparse
import os
import sys
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from db import fetch_all, insert_row, db as db_ctx


# ── Config ────────────────────────────────────────────────────────────────────

GA4_PROPERTY_ID    = os.environ.get("GA4_PROPERTY_ID", "").strip()
_SC_SITE_RAW       = os.environ.get("SEARCH_CONSOLE_SITE_URL", "").strip()
# Normalise: strip trailing slash for path building; keep original for SC API calls
SEARCH_CONSOLE_URL = _SC_SITE_RAW.rstrip("/")

# Base URL for building full page URLs (for URL Inspection API).
# If SC property is a domain property (sc-domain:washdog.cl), derive from domain name.
# Override with SITE_BASE_URL env var if needed.
_site_base_env = os.environ.get("SITE_BASE_URL", "").strip().rstrip("/")
if _site_base_env:
    SITE_BASE_URL = _site_base_env
elif _SC_SITE_RAW.startswith("sc-domain:"):
    _domain = _SC_SITE_RAW.replace("sc-domain:", "").strip().rstrip("/")
    SITE_BASE_URL = f"https://www.{_domain}"
else:
    SITE_BASE_URL = SEARCH_CONSOLE_URL

SHEET_ANALYTICS = "WashDog - Analytics"

ANALYTICS_HEADERS = [
    "URL", "Tipo", "Keyword", "Workflow ID",
    "Sessions", "Page Views", "Bounce Rate %", "Avg Duration (s)",
    "Clicks", "Impressions", "CTR %", "Avg Position",
    "Indexed", "Cobertura Google", "Último Crawl",
    "Date Start", "Date End", "Imported At",
]


# ── DB migration ──────────────────────────────────────────────────────────────

def _migrate() -> None:
    """Add analytics columns to performance_metrics if they don't exist (idempotent)."""
    new_cols = [
        ("url",            "TEXT"),
        ("sessions",       "INTEGER DEFAULT 0"),
        ("clicks",         "INTEGER DEFAULT 0"),
        ("impressions",    "INTEGER DEFAULT 0"),
        ("ctr",            "REAL DEFAULT 0.0"),
        ("avg_position",   "REAL DEFAULT 0.0"),
        ("date_start",     "TEXT"),
        ("date_end",       "TEXT"),
        ("indexed",        "INTEGER DEFAULT NULL"),   # 1=yes, 0=no, NULL=unknown
        ("index_status",   "TEXT"),                  # PASS / FAIL / NEUTRAL / ERROR
        ("coverage_state", "TEXT"),                  # human-readable SC coverage reason
        ("last_crawled",   "TEXT"),                  # ISO date of last Google crawl
    ]
    with db_ctx() as conn:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(performance_metrics)").fetchall()}
        for col_name, col_def in new_cols:
            if col_name not in existing:
                conn.execute(f"ALTER TABLE performance_metrics ADD COLUMN {col_name} {col_def}")
                print(f"[db] Added column: performance_metrics.{col_name}")


# ── URL ↔ Workflow mapping ────────────────────────────────────────────────────

def _get_url_workflow_map() -> dict[str, dict]:
    """
    Returns {page_path: {workflow_id, keyword, content_type}} for all completed
    workflows. Landing paths come from _CANONICAL_URLS; blog paths from _blog_slug().
    When multiple workflows share the same path, keeps the highest-scoring one.
    """
    from sync_sheets import _CANONICAL_URLS, _blog_slug

    rows = fetch_all("""
        SELECT w.id, w.topic, w.target_keyword, co.content_type,
               COALESCE(e.overall_score, 0) AS overall_score
        FROM workflows w
        JOIN content_outputs co ON co.workflow_id = w.id
        LEFT JOIN evaluations e  ON e.workflow_id  = w.id
        WHERE w.status = 'completed'
        ORDER BY e.overall_score DESC
    """)

    mapping: dict[str, dict] = {}
    for row in rows:
        ct      = row["content_type"]
        topic   = (row["topic"]   or "").strip()
        keyword = (row["target_keyword"] or "").strip()

        if ct == "landing":
            path = _CANONICAL_URLS.get(topic.lower(), "")
        else:
            path = _blog_slug(keyword or topic)

        if path and path not in mapping:   # first = highest score (ORDER BY DESC)
            mapping[path] = {
                "workflow_id":  row["id"],
                "keyword":      keyword or topic,
                "content_type": ct,
            }

    return mapping


# ── GA4 ───────────────────────────────────────────────────────────────────────

def fetch_ga4(paths: list[str], days: int) -> dict[str, dict]:
    """
    Fetches sessions, page views, bounce rate, avg session duration from GA4
    for the given page paths.

    Returns: {page_path: {sessions, page_views, bounce_rate, avg_duration_s}}
    """
    if not GA4_PROPERTY_ID:
        print("[ga4] GA4_PROPERTY_ID not set — skipping.")
        return {}

    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        DateRange, Dimension, Metric, RunReportRequest,
        FilterExpression, FilterExpressionList, Filter,
    )
    from workspace.api import _get_credentials

    creds  = _get_credentials()
    client = BetaAnalyticsDataClient(credentials=creds)

    end   = date.today() - timedelta(days=1)
    start = end - timedelta(days=days - 1)

    # OR filter across all target paths
    path_filters = FilterExpression(
        or_group=FilterExpressionList(expressions=[
            FilterExpression(filter=Filter(
                field_name="pagePath",
                string_filter=Filter.StringFilter(value=p, match_type="EXACT"),
            ))
            for p in paths
        ])
    )

    request = RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        dimensions=[Dimension(name="pagePath")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="screenPageViews"),
            Metric(name="bounceRate"),
            Metric(name="averageSessionDuration"),
        ],
        date_ranges=[DateRange(start_date=start.isoformat(), end_date=end.isoformat())],
        dimension_filter=path_filters,
    )

    response = client.run_report(request)
    results: dict[str, dict] = {}

    for row in response.rows:
        path = row.dimension_values[0].value
        results[path] = {
            "sessions":       int(float(row.metric_values[0].value or 0)),
            "page_views":     int(float(row.metric_values[1].value or 0)),
            "bounce_rate":    round(float(row.metric_values[2].value or 0) * 100, 1),
            "avg_duration_s": round(float(row.metric_values[3].value or 0), 1),
        }

    print(f"[ga4] {len(results)}/{len(paths)} paths with data (last {days} days: {start} → {end})")
    return results


# ── Search Console ────────────────────────────────────────────────────────────

def fetch_search_console(paths: list[str], days: int) -> dict[str, dict]:
    """
    Fetches clicks, impressions, CTR, avg position from Search Console.
    Note: SC has a ~3-day data lag.

    Returns: {page_path: {clicks, impressions, ctr, avg_position}}
    """
    if not SEARCH_CONSOLE_URL:
        print("[sc] SEARCH_CONSOLE_SITE_URL not set — skipping.")
        return {}

    from googleapiclient.discovery import build
    from workspace.api import _get_credentials

    creds   = _get_credentials()
    service = build("searchconsole", "v1", credentials=creds)

    end   = date.today() - timedelta(days=3)   # SC ~3-day lag
    start = end - timedelta(days=days - 1)

    # Query all pages, filter client-side — simpler and avoids regex escaping
    body = {
        "startDate":  start.isoformat(),
        "endDate":    end.isoformat(),
        "dimensions": ["page"],
        "rowLimit":   1000,
    }

    site_url = _SC_SITE_RAW  # use exact env var value for SC API
    try:
        resp = service.searchanalytics().query(siteUrl=site_url, body=body).execute()
    except Exception as e:
        print(f"[sc] Search Console query failed: {e}")
        print("[sc] Check that the OAuth account has Owner permission in Search Console.")
        return {}
    rows = resp.get("rows", [])

    target_paths = set(paths)
    results: dict[str, dict] = {}

    for row in rows:
        full_url = row["keys"][0]
        path = urlparse(full_url).path.rstrip("/") or "/"
        if not path.startswith("/"):
            path = "/" + path
        if path in target_paths:
            results[path] = {
                "clicks":       int(row.get("clicks", 0)),
                "impressions":  int(row.get("impressions", 0)),
                "ctr":          round(float(row.get("ctr", 0)) * 100, 2),
                "avg_position": round(float(row.get("position", 0)), 1),
            }

    print(f"[sc] {len(results)}/{len(paths)} paths with data (last {days} days: {start} → {end})")
    return results


# ── URL Inspection (indexing status) ─────────────────────────────────────────

def fetch_indexing_status(paths: list[str]) -> dict[str, dict]:
    """
    Checks Google's current indexing status for each page using the
    Search Console URL Inspection API.

    Returns: {page_path: {indexed, verdict, coverage_state, last_crawled}}
    """
    if not SEARCH_CONSOLE_URL:
        print("[index] SEARCH_CONSOLE_SITE_URL not set — skipping.")
        return {}

    import time
    from googleapiclient.discovery import build
    from workspace.api import _get_credentials

    creds   = _get_credentials()
    service = build("searchconsole", "v1", credentials=creds)

    site_url = _SC_SITE_RAW
    results: dict[str, dict] = {}

    print(f"\n[index] Checking indexing status for {len(paths)} URLs...")
    print(f"[index] Base URL: {SITE_BASE_URL}")
    for path in paths:
        full_url = f"{SITE_BASE_URL}{path}"
        try:
            resp = service.urlInspection().index().inspect(body={
                "inspectionUrl": full_url,
                "siteUrl":       site_url,
            }).execute()
            isr          = resp.get("inspectionResult", {}).get("indexStatusResult", {})
            verdict      = isr.get("verdict", "VERDICT_UNSPECIFIED")
            coverage     = isr.get("coverageState", "Unknown")
            last_crawled = (isr.get("lastCrawlTime") or "")[:10]
            results[path] = {
                "indexed":        verdict == "PASS",
                "verdict":        verdict,
                "coverage_state": coverage,
                "last_crawled":   last_crawled,
            }
            icon = "✓" if verdict == "PASS" else ("?" if verdict == "NEUTRAL" else "✗")
            print(f"  {icon} {path:<48} {coverage}")
        except Exception as e:
            print(f"  ? {path:<48} Error: {e}")
            results[path] = {
                "indexed":        False,
                "verdict":        "ERROR",
                "coverage_state": str(e)[:80],
                "last_crawled":   "",
            }
        time.sleep(0.3)   # SC URL Inspection: 600 req/min quota

    indexed_count = sum(1 for r in results.values() if r["indexed"])
    print(f"[index] {indexed_count}/{len(paths)} pages indexed")
    return results


# ── DB write ──────────────────────────────────────────────────────────────────

def write_to_db(
    url_map:      dict[str, dict],
    ga4_data:     dict[str, dict],
    sc_data:      dict[str, dict],
    index_data:   dict[str, dict],
    days:         int,
    dry_run:      bool = False,
) -> list[dict]:
    """Inserts one performance_metrics row per tracked URL. Returns written rows.

    Skips rows where (url, date_start) already exists in the DB to avoid
    duplicate entries on repeated weekly runs.
    """
    end_date   = (date.today() - timedelta(days=1)).isoformat()
    start_date = (date.today() - timedelta(days=days)).isoformat()
    now        = datetime.utcnow().isoformat()

    # Build set of (url, date_start) combos already in DB
    existing = fetch_all(
        "SELECT url, date_start FROM performance_metrics WHERE date_start = ?",
        (start_date,),
    )
    already_recorded = {r["url"] for r in existing}

    written = []
    for path, meta in url_map.items():
        if path in already_recorded:
            print(f"[analytics] Skipping duplicate: {path} (period {start_date} already recorded)")
            continue

        ga4   = ga4_data.get(path, {})
        sc    = sc_data.get(path, {})
        idx   = index_data.get(path, {})

        row = {
            "id":                str(uuid.uuid4()),
            "workflow_id":       meta["workflow_id"],
            "url":               path,
            "page_views":        ga4.get("page_views", 0),
            "avg_time_on_page":  ga4.get("avg_duration_s", 0.0),
            "bounce_rate":       ga4.get("bounce_rate", 0.0),
            "sessions":          ga4.get("sessions", 0),
            "clicks":            sc.get("clicks", 0),
            "impressions":       sc.get("impressions", 0),
            "ctr":               sc.get("ctr", 0.0),
            "avg_position":      sc.get("avg_position", 0.0),
            "indexed":           int(idx["indexed"]) if "indexed" in idx else None,
            "index_status":      idx.get("verdict", ""),
            "coverage_state":    idx.get("coverage_state", ""),
            "last_crawled":      idx.get("last_crawled", ""),
            "conversions":       0,
            "revenue_generated": 0.0,
            "date_start":        start_date,
            "date_end":          end_date,
            "recorded_at":       now,
        }
        written.append(row)
        if not dry_run:
            insert_row("performance_metrics", row)

    return written


# ── Sheet write ───────────────────────────────────────────────────────────────

def write_to_sheet(
    rows:    list[dict],
    url_map: dict[str, dict],
    dry_run: bool = False,
) -> None:
    """Appends analytics rows to 'WashDog - Analytics' sheet."""
    data_rows = []
    for row in rows:
        path = row["url"]
        meta = url_map.get(path, {})
        indexed_val = row.get("indexed")
        data_rows.append([
            path,
            meta.get("content_type", ""),
            meta.get("keyword", ""),
            meta.get("workflow_id", "")[:8],
            row["sessions"],
            row["page_views"],
            row["bounce_rate"],
            row["avg_time_on_page"],
            row["clicks"],
            row["impressions"],
            row["ctr"],
            row["avg_position"],
            "Sí" if indexed_val == 1 else ("No" if indexed_val == 0 else ""),
            row.get("coverage_state", ""),
            row.get("last_crawled", ""),
            row["date_start"],
            row["date_end"],
            row["recorded_at"][:19],
        ])

    print(f"\n[analytics] → '{SHEET_ANALYTICS}' ({len(data_rows)} row(s))")
    for dr in data_rows:
        indexed_label = f"indexed={dr[12]:<3}" if dr[12] else "indexed=?"
        print(f"  {dr[0]:<48} | views={dr[5]:>4}  clicks={dr[8]:>4}  pos={dr[11]}  {indexed_label}")

    if dry_run:
        print("[analytics] --dry-run: skipping write.")
        return

    try:
        from workspace.api import append_to_sheet
        append_to_sheet(SHEET_ANALYTICS, data_rows)
    except Exception as e:
        print(f"[analytics] Error writing to sheet: {e}")
        sys.exit(1)


# ── Init sheet ────────────────────────────────────────────────────────────────

def init_sheet() -> None:
    from workspace.api import append_to_sheet
    print(f"[analytics] Creating sheet: {SHEET_ANALYTICS}")
    append_to_sheet(SHEET_ANALYTICS, [ANALYTICS_HEADERS])
    print("[analytics] Sheet created. Run --days 30 to populate.")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync GA4 + Search Console analytics to DB and Sheets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python sync_analytics.py --init               # first-time sheet setup
  python sync_analytics.py --days 30            # full 30-day import
  python sync_analytics.py --days 7 --dry-run   # preview last 7 days
  python sync_analytics.py --ga4-only           # skip Search Console
  python sync_analytics.py --sc-only            # skip GA4
        """,
    )
    parser.add_argument("--init",           action="store_true", help="Create Analytics sheet with headers")
    parser.add_argument("--days",           type=int, default=30, help="Lookback window in days (default: 30)")
    parser.add_argument("--dry-run",        action="store_true", help="Preview without writing to DB or Sheets")
    parser.add_argument("--ga4-only",       action="store_true", help="Only fetch GA4 data")
    parser.add_argument("--sc-only",        action="store_true", help="Only fetch Search Console data")
    parser.add_argument("--check-indexing", action="store_true", help="Only check indexing status (no GA4/SC metrics)")
    parser.add_argument("--no-indexing",    action="store_true", help="Skip indexing status check")

    args = parser.parse_args()

    if args.init:
        init_sheet()
        return

    _migrate()

    url_map = _get_url_workflow_map()
    if not url_map:
        print("[analytics] No completed workflows found in DB.")
        sys.exit(0)

    paths = list(url_map.keys())
    print(f"[analytics] Tracking {len(paths)} URLs:")
    for p in paths:
        print(f"  {p}")

    if args.check_indexing:
        fetch_indexing_status(paths)
        return

    ga4_data   = {} if args.sc_only   else fetch_ga4(paths, args.days)
    sc_data    = {} if args.ga4_only  else fetch_search_console(paths, args.days)
    index_data = {} if args.no_indexing else fetch_indexing_status(paths)

    written = write_to_db(url_map, ga4_data, sc_data, index_data, args.days, dry_run=args.dry_run)
    write_to_sheet(written, url_map, dry_run=args.dry_run)

    if not args.dry_run:
        print("\n[analytics] Import complete.")


if __name__ == "__main__":
    main()
