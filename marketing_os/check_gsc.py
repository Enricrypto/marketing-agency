#!/usr/bin/env python3
"""
Marketing OS — Google Search Console Full Audit
WashDog — Indexing, Sitemaps, and Coverage Health Check.

Audits ALL pages on washdog.cl:
  - Indexing status per URL (via URL Inspection API)
  - Sitemap submission status (via Sitemaps API)
  - SEO flags: noindex recommendations, missing pages, coverage issues
  - Estimated fix timeline per issue type

Usage:
    python check_gsc.py                  # smart audit (skips already-indexed pages)
    python check_gsc.py --force          # full audit (checks all pages, ignores cache)
    python check_gsc.py --sitemaps       # sitemap status only
    python check_gsc.py --indexing       # indexing check only
    python check_gsc.py --report         # save report to logs/gsc_audit.txt
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

# ── Config ────────────────────────────────────────────────────────────────────

BASE_URL     = "https://www.washdog.cl"
_MOS_DIR     = Path(__file__).parent
_NEXTJS_DIR  = Path("/Users/enriqueibarra/washdog-website")
_LOG_DIR     = _MOS_DIR / "logs"
_LOG_DIR.mkdir(exist_ok=True)

_SC_SITE_RAW  = os.environ.get("SEARCH_CONSOLE_SITE_URL", "").strip()
_CACHE_PATH   = _MOS_DIR / "state" / "gsc_index_cache.json"


# ── Index cache helpers ───────────────────────────────────────────────────────

def _load_cache() -> dict:
    """Returns {url: {indexed, coverage, last_crawled, checked_at}} from disk."""
    if _CACHE_PATH.exists():
        try:
            return json.loads(_CACHE_PATH.read_text())
        except Exception:
            pass
    return {}


def _save_cache(cache: dict) -> None:
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_PATH.write_text(json.dumps(cache, indent=2), encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [check_gsc] %(message)s",
    handlers=[
        logging.FileHandler(_LOG_DIR / "check_gsc.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# ── Status explanations ───────────────────────────────────────────────────────

_COVERAGE_EXPLANATIONS = {
    "Submitted and indexed": {
        "icon": "✅",
        "meaning": "Page is indexed and live in Google Search.",
        "action":  "No action needed.",
        "days":    None,
    },
    "Indexed, not submitted in sitemap": {
        "icon": "⚠️",
        "meaning": "Google found and indexed it but it's not in your sitemap.",
        "action":  "Add URL to sitemap so Google can track freshness.",
        "days":    None,
    },
    "Crawled - currently not indexed": {
        "icon": "🔶",
        "meaning": "Google crawled the page but chose not to index it. Usually thin content, low quality signal, or near-duplicate.",
        "action":  "Improve content depth and uniqueness. Add internal links pointing to it.",
        "days":    14,
    },
    "Discovered - currently not indexed": {
        "icon": "🔷",
        "meaning": "Google found the URL but hasn't crawled it yet. Usually a crawl budget or priority issue.",
        "action":  "Add to sitemap. Add internal links. Request indexing in GSC.",
        "days":    7,
    },
    "URL is unknown to Google": {
        "icon": "❌",
        "meaning": "Google has never seen this URL. It's not in the sitemap and has no inbound links.",
        "action":  "Add to sitemap. Add internal links. Submit manually via GSC URL Inspection.",
        "days":    5,
    },
    "Duplicate without user-selected canonical": {
        "icon": "🔁",
        "meaning": "Google sees this as a duplicate and is using a different version.",
        "action":  "Add explicit <link rel=canonical> tag pointing to the preferred URL.",
        "days":    7,
    },
    "Redirect error": {
        "icon": "❗",
        "meaning": "The URL has a broken or chained redirect.",
        "action":  "Fix the redirect chain. Ensure clean 301 to final destination.",
        "days":    3,
    },
    "Soft 404": {
        "icon": "❗",
        "meaning": "Page returns 200 but Google treats it as not found (empty or near-empty content).",
        "action":  "Add real content or return a proper 404 status code.",
        "days":    7,
    },
    "Blocked by robots.txt": {
        "icon": "🚫",
        "meaning": "robots.txt is blocking Google from crawling this URL.",
        "action":  "Remove the block in robots.txt if this page should be indexed.",
        "days":    3,
    },
    "Excluded by 'noindex' tag": {
        "icon": "🙈",
        "meaning": "Page has a noindex meta tag. Google will not index it.",
        "action":  "If intentional (privacy/terms): this is correct. If not: remove the noindex tag.",
        "days":    3,
    },
}

_DEFAULT_EXPLANATION = {
    "icon": "❓",
    "meaning": "Unknown status.",
    "action":  "Check Google Search Console manually for more details.",
    "days":    None,
}

# ── Pages that should NOT be indexed ─────────────────────────────────────────

_NOINDEX_PATHS = {"/privacy", "/terms"}

# ── URL inventory builder ─────────────────────────────────────────────────────

def _get_blog_slugs() -> list[str]:
    blog_dir = _NEXTJS_DIR / "content" / "blog"
    if not blog_dir.exists():
        return []
    return [f"/blog/{p.stem}" for p in sorted(blog_dir.glob("*.md"))]


def _get_static_service_slugs() -> list[str]:
    servicios_dir = _NEXTJS_DIR / "src" / "app" / "servicios"
    if not servicios_dir.exists():
        return []
    slugs = []
    for d in servicios_dir.iterdir():
        if d.is_dir() and d.name != "[service]":
            slugs.append(f"/servicios/{d.name}")
    return sorted(slugs)


def _get_programmatic_slugs() -> list[str]:
    json_path = _NEXTJS_DIR / "data" / "local-pages.json"
    if not json_path.exists():
        return []
    try:
        data = json.loads(json_path.read_text())
        return [f"/servicios/{s}" for s in data.get("slugs", [])]
    except Exception:
        return []


def build_url_inventory() -> list[dict]:
    """
    Returns all known pages on washdog.cl with their type and SEO intent.
    """
    pages = []

    # Core pages
    pages.append({"path": "/",        "type": "core",    "noindex": False, "priority": "high"})
    pages.append({"path": "/blog",    "type": "core",    "noindex": False, "priority": "high"})
    pages.append({"path": "/privacy", "type": "legal",   "noindex": True,  "priority": "low"})
    pages.append({"path": "/terms",   "type": "legal",   "noindex": True,  "priority": "low"})

    # Static service pages
    for slug in _get_static_service_slugs():
        pages.append({"path": slug, "type": "service", "noindex": False, "priority": "high"})

    # Blog posts
    for slug in _get_blog_slugs():
        pages.append({"path": slug, "type": "blog", "noindex": False, "priority": "medium"})

    # Programmatic pages from local-pages.json (Phase 2)
    for slug in _get_programmatic_slugs():
        if not any(p["path"] == slug for p in pages):  # dedup
            pages.append({"path": slug, "type": "programmatic", "noindex": False, "priority": "medium"})

    return pages


# ── GSC clients ───────────────────────────────────────────────────────────────

def _sc_service():
    from googleapiclient.discovery import build
    from workspace.api import _get_credentials
    return build("searchconsole", "v1", credentials=_get_credentials())


# ── Indexing check ────────────────────────────────────────────────────────────

def check_indexing(pages: list[dict], force: bool = False) -> list[dict]:
    """
    Calls URL Inspection API for pages not yet confirmed indexed.
    Already-indexed pages are served from cache unless force=True.
    Returns augmented pages list.
    """
    if not _SC_SITE_RAW:
        log.error("SEARCH_CONSOLE_SITE_URL not set in .env")
        sys.exit(1)

    cache   = {} if force else _load_cache()
    service = _sc_service()
    results = []

    to_check = []
    for page in pages:
        full_url = f"{BASE_URL}{page['path']}"
        cached   = cache.get(full_url)
        if cached and cached.get("indexed"):
            # Already confirmed indexed — restore from cache, skip API call
            page["verdict"]      = "PASS"
            page["coverage"]     = cached.get("coverage", "Submitted and indexed")
            page["last_crawled"] = cached.get("last_crawled", "")
            page["robots_state"] = ""
            page["index_state"]  = ""
            page["indexed"]      = True
            page["from_cache"]   = True
            results.append(page)
        else:
            to_check.append((page, full_url))

    skipped = len(pages) - len(to_check)
    if skipped:
        log.info(f"Skipping {skipped} already-indexed URLs (cached). Use --force to recheck all.")
    log.info(f"\nChecking indexing status for {len(to_check)} URLs...")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for page, full_url in to_check:
        try:
            resp = service.urlInspection().index().inspect(body={
                "inspectionUrl": full_url,
                "siteUrl":       _SC_SITE_RAW,
            }).execute()

            isr          = resp.get("inspectionResult", {}).get("indexStatusResult", {})
            verdict      = isr.get("verdict", "VERDICT_UNSPECIFIED")
            coverage     = isr.get("coverageState", "Unknown")
            last_crawled = (isr.get("lastCrawlTime") or "")[:10]
            robots_state = isr.get("robotsTxtState", "")
            index_state  = isr.get("indexingState", "")

            page["verdict"]      = verdict
            page["coverage"]     = coverage
            page["last_crawled"] = last_crawled
            page["robots_state"] = robots_state
            page["index_state"]  = index_state
            page["indexed"]      = verdict == "PASS"
            page["from_cache"]   = False

            # Update cache
            cache[full_url] = {
                "indexed":      page["indexed"],
                "coverage":     coverage,
                "last_crawled": last_crawled,
                "checked_at":   today,
            }

        except Exception as e:
            page["verdict"]      = "ERROR"
            page["coverage"]     = str(e)[:80]
            page["last_crawled"] = ""
            page["robots_state"] = ""
            page["index_state"]  = ""
            page["indexed"]      = False
            page["from_cache"]   = False

        results.append(page)
        time.sleep(0.25)   # URL Inspection quota: 600 req/min

    _save_cache(cache)
    return results


# ── Sitemap check ─────────────────────────────────────────────────────────────

def check_sitemaps() -> list[dict]:
    """
    Lists submitted sitemaps and their status from GSC.
    """
    if not _SC_SITE_RAW:
        log.error("SEARCH_CONSOLE_SITE_URL not set in .env")
        sys.exit(1)

    service = _sc_service()
    try:
        resp     = service.sitemaps().list(siteUrl=_SC_SITE_RAW).execute()
        sitemaps = resp.get("sitemap", [])
    except Exception as e:
        log.error(f"Failed to list sitemaps: {e}")
        return []

    results = []
    for sm in sitemaps:
        results.append({
            "path":         sm.get("path", ""),
            "last_submitted": (sm.get("lastSubmitted") or "")[:10],
            "last_downloaded": (sm.get("lastDownloaded") or "")[:10],
            "is_pending":   sm.get("isPending", False),
            "is_processing":sm.get("isProcessing", False),
            "warnings":     sm.get("warnings", 0),
            "errors":       sm.get("errors", 0),
            "urls_in_sitemap": sum(
                int(c.get("count", 0))
                for c in sm.get("contents", [])
                if c.get("type") == "web"
            ),
            "indexed_urls":  sum(
                int(c.get("count", 0))
                for c in sm.get("contents", [])
                if c.get("type") == "indexedUrls"
            ) if any(c.get("type") == "indexedUrls" for c in sm.get("contents", [])) else None,
        })
    return results


# ── SEO flags ─────────────────────────────────────────────────────────────────

def run_seo_flags(pages: list[dict]) -> list[dict]:
    """
    Applies rule-based SEO flags to the audited pages.
    Returns list of flag dicts: {path, severity, issue, fix}.
    """
    flags = []

    for p in pages:
        path    = p["path"]
        verdict = p.get("verdict", "")
        coverage = p.get("coverage", "")

        # Legal pages: if indexed when they shouldn't be
        if p.get("noindex") and verdict == "PASS":
            flags.append({
                "path":     path,
                "severity": "MEDIUM",
                "issue":    f"Legal/utility page is indexed: {path}",
                "fix":      "Add <meta name='robots' content='noindex'> to this page.",
            })

        # Important pages not indexed — single flag per page (covers both not-indexed + never-crawled)
        if not p.get("noindex") and not p.get("indexed") and p["priority"] in ("high", "medium"):
            exp = _COVERAGE_EXPLANATIONS.get(coverage, _DEFAULT_EXPLANATION)
            never_crawled = p.get("last_crawled") == ""
            fix = ("Submit via GSC URL Inspection → 'Request Indexing'. " if never_crawled else "") + exp["action"]
            flags.append({
                "path":     path,
                "severity": "HIGH" if p["priority"] == "high" else "MEDIUM",
                "issue":    f"Page not indexed ({coverage})" + (" — never crawled" if never_crawled else ""),
                "fix":      fix,
                "days":     exp.get("days"),
            })

    return flags


# ── Report printer ────────────────────────────────────────────────────────────

def print_report(pages: list[dict], sitemaps: list[dict], flags: list[dict]) -> str:
    lines = []
    now   = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines.append(f"\n{'═' * 70}")
    lines.append(f"  WashDog GSC Audit — {now}")
    lines.append(f"{'═' * 70}")

    # ── Indexing summary ──────────────────────────────────────────────────────
    indexed     = [p for p in pages if p.get("indexed")]
    not_indexed = [p for p in pages if not p.get("indexed") and not p.get("noindex")]
    legal_pages = [p for p in pages if p.get("noindex")]

    lines.append(f"\n{'─' * 70}")
    lines.append(f"  INDEXING STATUS  ({len(pages)} total pages)")
    lines.append(f"{'─' * 70}")
    lines.append(f"  ✅  Indexed:         {len(indexed)}")
    lines.append(f"  ❌  Not indexed:     {len(not_indexed)}  (SEO pages only)")
    lines.append(f"  🙈  Legal/noindex:   {len(legal_pages)}  (privacy, terms — expected)")
    lines.append("")

    # Group by type
    for type_label in ["core", "service", "blog", "programmatic", "legal"]:
        group = [p for p in pages if p["type"] == type_label]
        if not group:
            continue
        lines.append(f"  {type_label.upper()} PAGES")
        for p in group:
            exp    = _COVERAGE_EXPLANATIONS.get(p.get("coverage", ""), _DEFAULT_EXPLANATION)
            icon   = "🙈" if p.get("noindex") and p.get("indexed") else exp["icon"]
            crawl  = f"  last crawl: {p['last_crawled']}" if p.get("last_crawled") else ""
            lines.append(f"    {icon}  {p['path']:<48} {p.get('coverage','–')}{crawl}")
        lines.append("")

    # ── Not-indexed detail ────────────────────────────────────────────────────
    if not_indexed:
        lines.append(f"{'─' * 70}")
        lines.append(f"  NOT INDEXED — DETAIL & FIX")
        lines.append(f"{'─' * 70}")
        for p in not_indexed:
            exp = _COVERAGE_EXPLANATIONS.get(p.get("coverage", ""), _DEFAULT_EXPLANATION)
            lines.append(f"\n  {exp['icon']}  {BASE_URL}{p['path']}")
            lines.append(f"     Status:  {p.get('coverage', 'Unknown')}")
            lines.append(f"     Why:     {exp['meaning']}")
            lines.append(f"     Fix:     {exp['action']}")
            if exp.get("days"):
                lines.append(f"     ETA:     ~{exp['days']} days after fix is applied")
        lines.append("")

    # ── Sitemap status ────────────────────────────────────────────────────────
    lines.append(f"{'─' * 70}")
    lines.append(f"  SITEMAPS")
    lines.append(f"{'─' * 70}")
    if not sitemaps:
        lines.append("  ❌  No sitemaps found in GSC. Submit your sitemap at:")
        lines.append(f"     https://search.google.com/search-console/sitemaps?resource_id={_SC_SITE_RAW}")
    else:
        for sm in sitemaps:
            has_errors = int(sm["errors"]) > 0
            status = "⏳" if sm["is_pending"] else ("❌" if has_errors else "✅")
            url_note = " (reprocessing after recent submission — check GSC UI for current count)" if sm["urls_in_sitemap"] == 0 else ""
            lines.append(f"  {status}  {sm['path']}")
            lines.append(f"       Submitted: {sm['last_submitted']}  |  Last downloaded: {sm['last_downloaded']}")
            lines.append(f"       URLs in sitemap: {sm['urls_in_sitemap']}{url_note}  |  Errors: {sm['errors']}  |  Warnings: {sm['warnings']}")
            if sm["is_pending"]:
                lines.append(f"       ⏳ Still being processed by Google")
            if has_errors:
                lines.append(f"       ❌ Has errors — check GSC Sitemaps panel for details")
    lines.append("")

    # ── SEO flags ─────────────────────────────────────────────────────────────
    lines.append(f"{'─' * 70}")
    lines.append(f"  SEO FLAGS  ({len(flags)} issue(s) found)")
    lines.append(f"{'─' * 70}")
    if not flags:
        lines.append("  ✅  No critical SEO issues detected.")
    else:
        high   = [f for f in flags if f["severity"] == "HIGH"]
        medium = [f for f in flags if f["severity"] == "MEDIUM"]
        for severity_group, label in [(high, "HIGH"), (medium, "MEDIUM")]:
            if severity_group:
                lines.append(f"\n  [{label}]")
                for f in severity_group:
                    lines.append(f"    • {f['path']}")
                    lines.append(f"      Issue: {f['issue']}")
                    lines.append(f"      Fix:   {f['fix']}")
                    if f.get("days"):
                        lines.append(f"      ETA:   ~{f['days']} days after fix")
    lines.append("")

    # ── Recommendations ───────────────────────────────────────────────────────
    lines.append(f"{'─' * 70}")
    lines.append(f"  RECOMMENDATIONS")
    lines.append(f"{'─' * 70}")

    # Check legal pages for noindex
    legal_not_noindexed = [p for p in legal_pages if p.get("indexed")]
    if legal_not_noindexed:
        lines.append(f"  ⚠️   Privacy/Terms pages are indexed. Add noindex to:")
        for p in legal_not_noindexed:
            lines.append(f"       {p['path']}")
    else:
        lines.append(f"  ✅  Legal pages (privacy, terms) correctly noindex or not indexed.")

    # Unknown URLs
    unknown = [p for p in pages if p.get("coverage") == "URL is unknown to Google" and not p.get("noindex")]
    if unknown:
        lines.append(f"\n  ⚠️   {len(unknown)} page(s) unknown to Google — never submitted:")
        for p in unknown:
            lines.append(f"       → Go to GSC > URL Inspection > paste URL > 'Request Indexing'")
            lines.append(f"         {BASE_URL}{p['path']}")

    # Crawl but not indexed
    crawled_not_indexed = [
        p for p in pages
        if p.get("coverage") == "Crawled - currently not indexed"
    ]
    if crawled_not_indexed:
        lines.append(f"\n  ⚠️   {len(crawled_not_indexed)} page(s) crawled but not indexed. Google may see them as thin content.")
        lines.append(f"       Add more unique content, improve internal linking, and wait 2–4 weeks.")

    # sitemap recommendation
    if sitemaps:
        total_sitemap_urls = sum(s["urls_in_sitemap"] for s in sitemaps)
        seo_pages = [p for p in pages if not p.get("noindex")]
        if total_sitemap_urls < len(seo_pages):
            lines.append(f"\n  ⚠️   Sitemap has {total_sitemap_urls} URLs but site has {len(seo_pages)} indexable pages.")
            lines.append(f"       Run: python generate_sitemap.py  to regenerate the sitemap.")

    lines.append(f"\n{'═' * 70}\n")
    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog        = "check_gsc.py",
        description = "Marketing OS — Full Google Search Console audit for WashDog",
        formatter_class = argparse.RawDescriptionHelpFormatter,
        epilog = """
Examples:
  python check_gsc.py              # full audit
  python check_gsc.py --sitemaps   # sitemap status only
  python check_gsc.py --indexing   # indexing check only
  python check_gsc.py --report     # save report to logs/gsc_audit.txt
        """,
    )
    parser.add_argument("--sitemaps", action="store_true", help="Check sitemap status only")
    parser.add_argument("--indexing", action="store_true", help="Check indexing status only")
    parser.add_argument("--report",   action="store_true", help="Save full report to logs/gsc_audit.txt")
    parser.add_argument("--force",    action="store_true", help="Recheck all URLs, ignoring the indexed cache")
    args = parser.parse_args()

    pages    = []
    sitemaps = []
    flags    = []

    inventory = build_url_inventory()
    log.info(f"URL inventory: {len(inventory)} pages")

    if not args.sitemaps:
        pages = check_indexing(inventory, force=args.force)
        flags = run_seo_flags(pages)

    if not args.indexing:
        sitemaps = check_sitemaps()

    report = print_report(
        pages    if pages    else inventory,
        sitemaps if sitemaps else [],
        flags    if flags    else [],
    )
    print(report)

    if args.report:
        out = _LOG_DIR / "gsc_audit.txt"
        out.write_text(report, encoding="utf-8")
        log.info(f"Report saved: {out}")


if __name__ == "__main__":
    main()
