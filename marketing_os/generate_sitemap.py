#!/usr/bin/env python3
"""
Marketing OS — Sitemap Generator (Phase 3)
WashDog Local SEO Distribution Engine.

Generates two outputs:
  1. washdog-website/data/local-pages.json  — slug list consumed by Next.js sitemap.ts
  2. washdog-website/public/sitemap-local.xml — XML sitemap for manual SC submission

Pages included:
  - Static core pages (hardcoded)
  - Blog posts (scanned from content/blog/*.md)
  - Phase 1 Ñuñoa service pages (scanned from app/servicios/)
  - Phase 2 programmatic pages (pages table: status=generated or published)

Usage:
    python generate_sitemap.py              # generate both outputs
    python generate_sitemap.py --dry-run    # print sitemap without writing
    python generate_sitemap.py --check      # show what's in DB vs what's deployed
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from db import fetch_all, init_db

# ── Paths ──────────────────────────────────────────────────────────────────────

_MOS_DIR      = Path(__file__).parent
_NEXTJS_DIR        = Path("/Users/enriqueibarra/washdog-website")
_BLOG_DIR          = _NEXTJS_DIR / "content" / "blog"
_CONTENT_SERV_DIR  = _NEXTJS_DIR / "content" / "servicios"   # source of truth for all service pages
_SERVICES_DIR      = _NEXTJS_DIR / "src" / "app" / "servicios"  # legacy static dirs (kept for reference)
_DATA_DIR          = _NEXTJS_DIR / "data"
_PUBLIC_DIR        = _NEXTJS_DIR / "public"

BASE_URL = "https://www.washdog.cl"

# ── Logging ───────────────────────────────────────────────────────────────────

_LOG_DIR = _MOS_DIR / "logs"
_LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [sitemap] %(message)s",
    handlers=[
        logging.FileHandler(_LOG_DIR / "generate_sitemap.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ── Page collectors ───────────────────────────────────────────────────────────

def _collect_static_pages() -> list[dict]:
    return [
        {"url": BASE_URL,                                                    "priority": "1.0", "changefreq": "weekly"},
        {"url": f"{BASE_URL}/blog",                                          "priority": "0.8", "changefreq": "weekly"},
        # Hardcoded Next.js app routes (not markdown-driven)
        {"url": f"{BASE_URL}/servicios/auto-lavado-perros-nunoa",            "priority": "0.9", "changefreq": "monthly"},
        {"url": f"{BASE_URL}/servicios/bano",                                "priority": "0.9", "changefreq": "monthly"},
        {"url": f"{BASE_URL}/servicios/corte",                               "priority": "0.9", "changefreq": "monthly"},
        {"url": f"{BASE_URL}/servicios/peluqueria-canina-nunoa",             "priority": "0.9", "changefreq": "monthly"},
        {"url": f"{BASE_URL}/servicios/peluqueria-gatos-nunoa",              "priority": "0.9", "changefreq": "monthly"},
        {"url": f"{BASE_URL}/servicios/precio-peluqueria-nunoa",             "priority": "0.9", "changefreq": "monthly"},
        {"url": f"{BASE_URL}/privacy",                                       "priority": "0.3", "changefreq": "yearly"},
        {"url": f"{BASE_URL}/terms",                                         "priority": "0.3", "changefreq": "yearly"},
    ]


def _collect_blog_pages() -> list[dict]:
    """Scans content/blog/*.md and returns one entry per post."""
    if not _BLOG_DIR.exists():
        log.warning(f"Blog directory not found: {_BLOG_DIR}")
        return []

    pages = []
    for md_file in sorted(_BLOG_DIR.glob("*.md")):
        slug = md_file.stem
        pages.append({
            "url":        f"{BASE_URL}/blog/{slug}",
            "priority":   "0.6",   # lower than service pages — blog is supporting content
            "changefreq": "never", # once published, blog posts rarely change
            "lastmod":    datetime.fromtimestamp(
                md_file.stat().st_mtime, tz=timezone.utc
            ).strftime("%Y-%m-%d"),
        })
    return pages


def _collect_service_pages() -> list[dict]:
    """Scans content/servicios/*.md — source of truth for all live service pages."""
    if not _CONTENT_SERV_DIR.exists():
        log.warning(f"Services directory not found: {_CONTENT_SERV_DIR}")
        return []

    pages = []
    for md_file in sorted(_CONTENT_SERV_DIR.glob("*.md")):
        slug = md_file.stem
        pages.append({
            "url":        f"{BASE_URL}/servicios/{slug}",
            "priority":   "0.9",
            "changefreq": "monthly",
            "lastmod":    datetime.fromtimestamp(
                md_file.stat().st_mtime, tz=timezone.utc
            ).strftime("%Y-%m-%d"),
        })
    return pages


def _collect_programmatic_pages() -> tuple[list[dict], list[dict]]:
    """
    Reads pages table for generated/published pages.

    Returns:
        (deployed, pending_deploy)
        deployed      — pages that also exist as Next.js directories
        pending_deploy — pages in DB but NOT yet deployed to Next.js
    """
    rows = fetch_all(
        "SELECT * FROM pages WHERE status IN ('generated', 'published') ORDER BY service_slug, commune_slug"
    )

    deployed      = []
    pending_deploy = []

    for row in rows:
        service_slug = row["service_slug"]
        commune_slug = row["commune_slug"]
        slug         = f"{service_slug}-{commune_slug}"
        nextjs_path  = _SERVICES_DIR / slug

        entry = {
            "url":        f"{BASE_URL}/servicios/{slug}",
            "priority":   "0.9",
            "changefreq": "monthly",
            "slug":       slug,
        }

        content_path = _CONTENT_SERV_DIR / f"{slug}.md"
        if content_path.exists():
            deployed.append(entry)
        else:
            pending_deploy.append({**entry, "keyword": row.get("keyword", "")})

    return deployed, pending_deploy


# ── JSON output (consumed by Next.js sitemap.ts) ──────────────────────────────

def write_local_pages_json(service_slugs: list[str], dry_run: bool = False) -> None:
    """
    Writes washdog-website/data/local-pages.json with slugs of live
    programmatic service pages. Next.js sitemap.ts reads this at build time.
    """
    data = {"slugs": service_slugs, "generated_at": datetime.utcnow().isoformat()}

    if dry_run:
        log.info(f"[dry-run] Would write {len(service_slugs)} slugs to local-pages.json")
        return

    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _DATA_DIR / "local-pages.json"
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    log.info(f"Written: {out_path}  ({len(service_slugs)} slugs)")


# ── XML sitemap output ────────────────────────────────────────────────────────

def _build_xml(pages: list[dict]) -> str:
    urlset = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")

    for p in pages:
        url_el = SubElement(urlset, "url")
        SubElement(url_el, "loc").text = p["url"]
        if p.get("lastmod"):
            SubElement(url_el, "lastmod").text = p["lastmod"]
        SubElement(url_el, "changefreq").text = p.get("changefreq", "monthly")
        SubElement(url_el, "priority").text   = p.get("priority", "0.7")

    raw = tostring(urlset, encoding="unicode")
    return minidom.parseString(raw).toprettyxml(indent="  ", encoding=None)


def write_xml_sitemap(pages: list[dict], dry_run: bool = False) -> None:
    xml = _build_xml(pages)

    if dry_run:
        log.info(f"[dry-run] XML sitemap would contain {len(pages)} URLs")
        return

    _PUBLIC_DIR.mkdir(exist_ok=True)
    out_path = _PUBLIC_DIR / "sitemap-local.xml"
    out_path.write_text(xml, encoding="utf-8")
    log.info(f"Written: {out_path}  ({len(pages)} URLs)")


# ── Main ──────────────────────────────────────────────────────────────────────

def generate(dry_run: bool = False) -> None:
    init_db()

    static_pages  = _collect_static_pages()
    blog_pages    = _collect_blog_pages()
    service_pages = _collect_service_pages()
    prog_deployed, prog_pending = _collect_programmatic_pages()

    # Service pages from filesystem already includes the Ñuñoa + any programmatic ones.
    # prog_deployed adds DB-generated pages that have corresponding Next.js dirs.
    # Merge and deduplicate by URL.
    all_service_pages = {p["url"]: p for p in service_pages}
    for p in prog_deployed:
        all_service_pages[p["url"]] = p

    all_pages = (
        static_pages
        + list(all_service_pages.values())
        + blog_pages
    )

    log.info(
        f"Sitemap: {len(static_pages)} static | "
        f"{len(all_service_pages)} service | "
        f"{len(blog_pages)} blog | "
        f"Total: {len(all_pages)} URLs"
    )

    # Slugs for JSON (programmatic service pages not already hardcoded in sitemap.ts)
    # We write ALL service slugs so sitemap.ts can merge cleanly
    service_slugs = [
        p["url"].replace(f"{BASE_URL}/servicios/", "")
        for p in all_service_pages.values()
    ]

    write_local_pages_json(service_slugs, dry_run=dry_run)
    write_xml_sitemap(all_pages, dry_run=dry_run)

    if prog_pending:
        log.warning(
            f"\n  {len(prog_pending)} page(s) generated in DB but NOT deployed to Next.js:"
        )
        for p in prog_pending[:10]:
            log.warning(f"    - /servicios/{p['slug']}  ({p['keyword']})")
        if len(prog_pending) > 10:
            log.warning(f"    ... and {len(prog_pending) - 10} more")
        log.warning("  Run the Next.js publish step to deploy these pages.")
    else:
        log.info("All generated pages are deployed.")

    # Resubmit sitemap to GSC so Google always sees the latest version
    if not dry_run:
        try:
            from indexing import resubmit_sitemap
            resubmit_sitemap()
        except Exception as e:
            log.warning(f"[sitemap] GSC resubmission failed: {e}")


def check(args) -> None:
    """Shows what's in the DB vs what's deployed in Next.js."""
    init_db()

    from page_registry import get_pages_summary
    summary = get_pages_summary()

    service_dirs = [
        d.name for d in _SERVICES_DIR.iterdir()
        if d.is_dir() and not d.name.startswith("_")
    ] if _SERVICES_DIR.exists() else []

    blog_files = [f.stem for f in _BLOG_DIR.glob("*.md")] if _BLOG_DIR.exists() else []

    _, prog_pending = _collect_programmatic_pages()

    print(f"\n{'─'*60}")
    print(f"  SITEMAP STATUS CHECK")
    print(f"{'─'*60}")
    print(f"  Live service pages (Next.js): {len(service_dirs)}")
    for s in service_dirs:
        print(f"    ✓ /servicios/{s}")
    print(f"\n  Live blog posts:              {len(blog_files)}")
    print(f"\n  DB registry:")
    for status, count in sorted(summary.items()):
        print(f"    {status:<12} {count}")
    print(f"\n  Generated (DB) but not live:  {len(prog_pending)}")
    for p in prog_pending[:5]:
        print(f"    ✗ /servicios/{p['slug']}")
    if len(prog_pending) > 5:
        print(f"    ... and {len(prog_pending) - 5} more")
    print(f"{'─'*60}\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog        = "generate_sitemap.py",
        description = "Marketing OS — Sitemap generator for WashDog",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print without writing files")
    parser.add_argument("--check",   action="store_true", help="Show DB vs deployed status")

    args = parser.parse_args()

    if args.check:
        check(args)
    else:
        generate(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
