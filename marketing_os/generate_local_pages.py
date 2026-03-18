#!/usr/bin/env python3
"""
Marketing OS — Keyword Generator (Phase 2)
Programmatic Local SEO Expansion for WashDog.

Reads services.csv × communes.csv and registers all service+commune
combinations in the `pages` table. Skips pages that already exist.

Usage:
    python generate_local_pages.py --init       # populate DB with all combinations
    python generate_local_pages.py --status     # show current registry summary
    python generate_local_pages.py --list       # list all registered pages
"""

import argparse
import csv
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from db import init_db
from page_registry import (
    register_page,
    get_all_pages,
    get_pages_summary,
)

# ── Logging ───────────────────────────────────────────────────────────────────

_LOG_DIR = Path(__file__).parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [generate_pages] %(message)s",
    handlers=[
        logging.FileHandler(_LOG_DIR / "generate_pages.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# ── CSV paths ─────────────────────────────────────────────────────────────────

_KEYWORDS_DIR = Path(__file__).parent / "keywords"
SERVICES_CSV  = _KEYWORDS_DIR / "services.csv"
COMMUNES_CSV  = _KEYWORDS_DIR / "communes.csv"


# ── Loaders ───────────────────────────────────────────────────────────────────

def load_services() -> list[dict]:
    with open(SERVICES_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_communes() -> list[dict]:
    with open(COMMUNES_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ── Generator ─────────────────────────────────────────────────────────────────

def generate_all(dry_run: bool = False) -> None:
    """
    Creates a page registry entry for every service × commune combination.
    Skips combinations that already exist.

    Args:
        dry_run: Print what would be registered without writing to DB.
    """
    services = load_services()
    communes = load_communes()

    total     = len(services) * len(communes)
    inserted  = 0
    skipped   = 0

    log.info(f"Generating {len(services)} services × {len(communes)} communes = {total} combinations")

    for svc in services:
        for com in communes:
            keyword  = f"{svc['service']} {com['name']}"
            page_id  = f"{svc['slug']}__{com['slug']}"

            if dry_run:
                print(f"  [dry-run] {page_id:<50}  keyword: {keyword}")
                inserted += 1
                continue

            result = register_page(
                service_slug = svc["slug"],
                service_name = svc["service"],
                commune_slug = com["slug"],
                commune_name = com["name"],
                keyword      = keyword,
            )

            if result:
                log.info(f"  + Registered: {page_id}  ({keyword})")
                inserted += 1
            else:
                skipped += 1

    if dry_run:
        log.info(f"[dry-run] Would register {inserted} pages (0 written)")
    else:
        log.info(f"Done. Inserted: {inserted} | Skipped (already exist): {skipped} | Total: {total}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def cmd_init(args) -> None:
    init_db()
    generate_all(dry_run=args.dry_run)


def cmd_status(args) -> None:
    summary = get_pages_summary()
    total = sum(summary.values())
    print("\n[pages] Registry summary:")
    for status, count in sorted(summary.items()):
        bar = "█" * min(count, 40)
        print(f"  {status:<12} {count:>4}  {bar}")
    print(f"  {'TOTAL':<12} {total:>4}")


def cmd_list(args) -> None:
    pages = get_all_pages()
    if not pages:
        print("[pages] No pages registered yet. Run --init first.")
        return
    print(f"\n{'page_id':<45} {'status':<12} {'keyword'}")
    print("-" * 100)
    for p in pages:
        wid = f"  wf:{p['workflow_id'][:8]}" if p.get("workflow_id") else ""
        print(f"  {p['page_id']:<43} {p['status']:<12} {p['keyword']}{wid}")
    print(f"\n  Total: {len(pages)} pages")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog        = "generate_local_pages.py",
        description = "Marketing OS — Programmatic Local SEO keyword registry",
        formatter_class = argparse.RawDescriptionHelpFormatter,
        epilog = """
Examples:
  python generate_local_pages.py --init           # register all 168 combinations
  python generate_local_pages.py --init --dry-run # preview without writing
  python generate_local_pages.py --status         # show status breakdown
  python generate_local_pages.py --list           # list all pages
        """,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("--init", help="Populate DB with all service×commune combinations")
    p_init.add_argument("--dry-run", action="store_true", help="Preview without writing to DB")

    sub.add_parser("--status", help="Show page registry summary by status")
    sub.add_parser("--list",   help="List all registered pages")

    return parser


def main() -> None:
    # Support both subcommand and flag style (--init, --status, --list)
    parser = argparse.ArgumentParser(
        prog        = "generate_local_pages.py",
        description = "Marketing OS — Programmatic Local SEO keyword registry",
    )
    parser.add_argument("--init",    action="store_true", help="Populate DB with all service×commune combinations")
    parser.add_argument("--status",  action="store_true", help="Show page registry summary")
    parser.add_argument("--list",    action="store_true", help="List all registered pages")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing (use with --init)")

    args = parser.parse_args()

    if args.init:
        cmd_init(args)
    elif args.status:
        cmd_status(args)
    elif args.list:
        cmd_list(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
