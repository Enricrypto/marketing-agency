#!/usr/bin/env python3
"""
Marketing OS — Pending Pages Runner (Phase 2)
Programmatic Local SEO Expansion for WashDog.

Fetches pages with status='pending' from the registry and runs landing page
workflows for each, up to --batch N per execution.

Usage:
    python run_pending_pages.py --batch 10          # generate 10 pages
    python run_pending_pages.py --batch 5 --dry-run # preview without running
    python run_pending_pages.py --batch 1           # single page (safe test)
    python run_pending_pages.py --backfill          # deploy all DB-generated pages to website
"""

import argparse
import logging
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from db import init_db, fetch_all
from page_registry import (
    get_pending_pages,
    get_pages_summary,
    mark_page_generated,
    mark_page_failed,
)

BASE_URL      = "https://www.washdog.cl"
_WEBSITE_DIR  = Path(os.environ.get("WASHDOG_WEBSITE_DIR", "/Users/enriqueibarra/washdog-website"))
_CONTENT_DIR  = _WEBSITE_DIR / "content" / "servicios"

# ── Logging ───────────────────────────────────────────────────────────────────

_LOG_DIR = Path(__file__).parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [run_pending] %(message)s",
    handlers=[
        logging.FileHandler(_LOG_DIR / "run_pending_pages.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ── Deploy helpers ────────────────────────────────────────────────────────────

def _extract_description(content: str) -> str:
    """Extract first H2 or first non-heading paragraph as meta description."""
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("## "):
            # Strip markdown and emoji for clean meta description
            desc = re.sub(r"^##\s+", "", line)
            desc = re.sub(r"[*_`]", "", desc)
            return desc[:160]
    # Fallback: first non-empty, non-heading paragraph
    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("---") and not line.startswith("!"):
            desc = re.sub(r"[*_`]", "", line)
            return desc[:160]
    return ""


def _build_md_file(slug: str, title: str, content: str, service_name: str, commune_name: str) -> str:
    """Build a complete .md file with frontmatter for a landing page."""
    description = _extract_description(content)
    keywords    = f"{service_name} {commune_name}, peluquería canina {commune_name}, grooming {commune_name}, WashDog"
    frontmatter = (
        f"---\n"
        f"title: \"{title}\"\n"
        f"description: \"{description}\"\n"
        f"keywords: \"{keywords}\"\n"
        f"date: \"{time.strftime('%Y-%m-%d')}\"\n"
        f"---\n\n"
    )
    return frontmatter + content


def _deploy_page(slug: str, title: str, content: str, service_name: str, commune_name: str) -> Path | None:
    """
    Write a landing page .md file to washdog-website/content/servicios/.
    Returns the path written, or None if already up-to-date.
    """
    _CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    dest = _CONTENT_DIR / f"{slug}.md"

    new_content = _build_md_file(slug, title, content, service_name, commune_name)

    if dest.exists() and dest.read_text(encoding="utf-8") == new_content:
        log.info(f"  [deploy] Unchanged, skipping: {dest.name}")
        return None

    dest.write_text(new_content, encoding="utf-8")
    log.info(f"  [deploy] Written: content/servicios/{dest.name}")
    return dest


def _git_push_pages(paths: list[Path]) -> None:
    """Commit and push new landing page files to trigger Vercel deploy."""
    if not paths:
        return
    try:
        names  = [p.name for p in paths]
        rel    = [str(p.relative_to(_WEBSITE_DIR)) for p in paths]
        n      = len(names)
        msg    = f"chore: add {n} programmatic landing page{'s' if n > 1 else ''} ({', '.join(p.stem for p in paths[:3])}{'...' if n > 3 else ''})"

        subprocess.run(["git", "add"] + rel, cwd=_WEBSITE_DIR, check=True)
        subprocess.run(["git", "commit", "-m", msg], cwd=_WEBSITE_DIR, check=True)
        subprocess.run(["git", "push"], cwd=_WEBSITE_DIR, check=True)
        log.info(f"  [git] Pushed {n} page(s) — Vercel deploy triggered")
    except subprocess.CalledProcessError as e:
        log.warning(f"  [git] Push failed: {e}")


# ── Indexing ──────────────────────────────────────────────────────────────────

def _resubmit_sitemap() -> None:
    """Regenerate sitemap + resubmit to GSC. Fails silently — indexing is best-effort."""
    try:
        from indexing import regenerate_and_resubmit
        ok = regenerate_and_resubmit()
        if ok:
            log.info("  [index] Sitemap resubmitted to GSC — Google will re-crawl all pages")
        else:
            log.warning("  [index] Sitemap resubmission skipped or failed — check logs/indexing_submissions.log")
    except Exception as e:
        log.warning(f"  [index] Could not resubmit sitemap: {e}")


def run_batch(batch: int = 10, dry_run: bool = False, no_index: bool = False) -> None:
    """
    Fetches up to `batch` pending pages and runs a landing page workflow for each.
    On success: writes .md file to washdog-website, commits, pushes to trigger Vercel.
    """
    init_db()

    pending = get_pending_pages(limit=batch)

    if not pending:
        log.info("No pending pages found. Run generate_local_pages.py --init first.")
        return

    # ── Crawl budget governor ─────────────────────────────────────────────────
    # Pause generation if Google has indexed < 60% of already-published pages.
    if not dry_run and not no_index:
        from indexing import check_indexing_health
        deployed_urls = [
            f"{BASE_URL}/servicios/{p.stem}"
            for p in sorted(_CONTENT_DIR.glob("*.md"))
        ]
        health = check_indexing_health(deployed_urls)
        if health["below_threshold"]:
            log.warning(
                f"[governor] Indexing rate {health['rate']:.0%} is below "
                f"{health['threshold']:.0%} threshold "
                f"({health['indexed']}/{health['checked']} sampled pages indexed). "
                f"Pausing batch — Google needs to catch up. "
                f"Will retry in ~6h or run with --no-index to bypass."
            )
            return

    summary = get_pages_summary()
    log.info(
        f"Registry: pending={summary.get('pending', 0)} "
        f"generated={summary.get('generated', 0)} "
        f"failed={summary.get('failed', 0)}"
    )
    log.info(f"Processing {len(pending)} page(s) (batch={batch})")

    succeeded    = 0
    failed       = 0
    deployed_paths: list[Path] = []

    for page in pending:
        page_id      = page["page_id"]
        service_name = page["service_name"]
        commune_name = page["commune_name"]
        service_slug = page["service_slug"]
        commune_slug = page["commune_slug"]
        keyword      = page["keyword"]

        log.info(f"[{page_id}] Starting: '{keyword}'")

        if dry_run:
            log.info(
                f"  [dry-run] Would run: landing --service '{service_name}' "
                f"--location '{commune_name}'"
            )
            succeeded += 1
            continue

        try:
            from workflows.landing_page import run_landing_page

            result = run_landing_page(
                service  = service_name,
                location = commune_name,
            )

            workflow_id = result["workflow_id"]
            overall     = result.get("scores", {}).get("overall_score", 0)

            mark_page_generated(page_id, workflow_id)
            log.info(
                f"  [OK] workflow_id={workflow_id[:8]}  overall={overall}/100  "
                f"title: {result.get('title', '')[:60]}"
            )
            succeeded += 1

            # Deploy: write .md file to washdog-website
            slug = f"{service_slug}-{commune_slug}"
            path = _deploy_page(
                slug         = slug,
                title        = result["title"],
                content      = result["content"],
                service_name = service_name,
                commune_name = commune_name,
            )
            if path:
                deployed_paths.append(path)

            # Small delay between API calls to avoid rate limiting
            time.sleep(2)

        except Exception as e:
            mark_page_failed(page_id)
            log.error(f"  [FAIL] {page_id}: {e}")
            failed += 1

    # Commit + push all new pages in one git operation
    if deployed_paths:
        _git_push_pages(deployed_paths)
        # Regenerate sitemap and resubmit to GSC — one call covers all new pages
        if not no_index:
            _resubmit_sitemap()

    log.info(
        f"Batch complete. Succeeded: {succeeded} | Failed: {failed} | Deployed: {len(deployed_paths)} | "
        f"Remaining pending: {summary.get('pending', 0) - succeeded - failed}"
    )


def run_backfill(no_index: bool = False) -> None:
    """
    Export all DB-generated pages that don't yet have a .md file in washdog-website.
    Safe to run multiple times — skips existing files.
    """
    init_db()

    # Get all generated pages with their workflow_ids
    pages = fetch_all(
        "SELECT page_id, service_name, commune_name, service_slug, commune_slug, workflow_id "
        "FROM pages WHERE status = 'generated' AND workflow_id IS NOT NULL"
    )

    if not pages:
        log.info("[backfill] No generated pages found in DB.")
        return

    log.info(f"[backfill] Found {len(pages)} generated page(s) in DB")
    deployed_paths: list[Path] = []

    for page in pages:
        service_slug = page["service_slug"]
        commune_slug = page["commune_slug"]
        slug         = f"{service_slug}-{commune_slug}"
        dest         = _CONTENT_DIR / f"{slug}.md"

        if dest.exists():
            log.info(f"  [backfill] Already deployed: {slug}.md — skipping")
            continue

        # Fetch the latest content for this workflow from the DB
        rows = fetch_all(
            "SELECT title, content FROM content_outputs "
            "WHERE workflow_id = ? AND content_type = 'landing' "
            "ORDER BY created_at DESC LIMIT 1",
            (page["workflow_id"],),
        )

        if not rows:
            log.warning(f"  [backfill] No content found for workflow {page['workflow_id'][:8]} — skipping")
            continue

        title   = rows[0]["title"]
        content = rows[0]["content"]

        path = _deploy_page(
            slug         = slug,
            title        = title,
            content      = content,
            service_name = page["service_name"],
            commune_name = page["commune_name"],
        )
        if path:
            deployed_paths.append(path)

    if deployed_paths:
        _git_push_pages(deployed_paths)
        if not no_index:
            _resubmit_sitemap()

    log.info(f"[backfill] Done. Deployed {len(deployed_paths)} new page(s).")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog        = "run_pending_pages.py",
        description = "Marketing OS — Run landing page workflows for pending pages",
        formatter_class = argparse.RawDescriptionHelpFormatter,
        epilog = """
Examples:
  python run_pending_pages.py --batch 10          # generate 10 pages
  python run_pending_pages.py --batch 5 --dry-run # preview without running
  python run_pending_pages.py --batch 1           # test with a single page
  python run_pending_pages.py --backfill          # deploy all DB-generated pages to website
        """,
    )
    parser.add_argument(
        "--batch", type=int, default=10,
        help="Maximum pages to generate per run (default: 10)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Log which pages would run without calling Claude",
    )
    parser.add_argument(
        "--no-index", action="store_true",
        help="Skip automatic Search Console indexing submission",
    )
    parser.add_argument(
        "--backfill", action="store_true",
        help="Deploy all DB-generated pages that are missing from washdog-website",
    )

    args = parser.parse_args()

    if args.backfill:
        run_backfill(no_index=args.no_index)
    else:
        run_batch(batch=args.batch, dry_run=args.dry_run, no_index=args.no_index)


if __name__ == "__main__":
    main()
