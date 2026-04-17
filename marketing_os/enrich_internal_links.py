#!/usr/bin/env python3
"""
Marketing OS — Internal Linking Engine (Phase 3)
WashDog Local SEO Distribution.

Enriches generated content with internal links to:
  1. Same service, neighboring communes (horizontal links)
  2. Service hub pages (vertical upward links)
  3. Blog articles → related service pages (topical authority)

This dramatically improves Google's understanding of page hierarchy and
distributes link authority across the site.

Usage:
    python enrich_internal_links.py --all           # enrich all generated pages
    python enrich_internal_links.py --dry-run       # print links without writing
    python enrich_internal_links.py --blog          # enrich blog posts with service links
"""

import argparse
import csv
import logging
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

# ── Paths ──────────────────────────────────────────────────────────────────────

_MOS_DIR    = Path(__file__).parent
_NEXTJS_DIR = Path("/Users/enriqueibarra/washdog-website")
_BLOG_DIR   = _NEXTJS_DIR / "content" / "blog"

BASE_URL = "https://www.washdog.cl"

# ── Logging ───────────────────────────────────────────────────────────────────

_LOG_DIR = _MOS_DIR / "logs"
_LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [internal_links] %(message)s",
    handlers=[
        logging.FileHandler(_LOG_DIR / "enrich_internal_links.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# ── Blog → service keyword map ────────────────────────────────────────────────
# Maps blog keywords/topics to relevant service slugs.
# When a blog post matches a keyword, it gets links to those service pages.

_BLOG_SERVICE_MAP = {
    "baño":         "bano-perros",
    "bañar":        "bano-perros",
    "lavado":       "bano-perros",
    "auto lavado":  "auto-lavado-perros",
    "shampoo":      "bano-perros",
    "frecuencia":   "bano-perros",
    "peluquería":   "peluqueria-canina",
    "corte":        "peluqueria-canina",
    "pelo":         "peluqueria-canina",
    "gato":         "peluqueria-gatos",
    "felino":       "peluqueria-gatos",
    "spa":          "spa-canino",
    "precio":       "peluqueria-canina",
    "costo":        "peluqueria-canina",
}

# Priority communes to link from blog posts (nearest to WashDog's location)
_PRIORITY_COMMUNES = [
    ("nunoa",        "Ñuñoa"),
    ("providencia",  "Providencia"),
    ("la-reina",     "La Reina"),
    ("macul",        "Macul"),
    ("las-condes",   "Las Condes"),
]


# ── CSV loaders ───────────────────────────────────────────────────────────────

def _load_communes() -> list[dict]:
    csv_path = _MOS_DIR / "keywords" / "communes.csv"
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _load_services() -> list[dict]:
    csv_path = _MOS_DIR / "keywords" / "services.csv"
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ── Link block builders ───────────────────────────────────────────────────────

def _build_related_communes_block(service_slug: str, current_commune_slug: str) -> str:
    """
    Builds a 'Disponible en otras comunas' section linking to
    same service in neighboring communes.
    """
    communes = _load_communes()
    servicios_dir = _NEXTJS_DIR / "content" / "servicios"
    links = []
    for com in communes:
        if com["slug"] == current_commune_slug:
            continue
        slug = f"{service_slug}-{com['slug']}"
        if not (servicios_dir / f"{slug}.md").exists():
            continue  # skip links to pages that don't exist yet
        links.append(f"- [{com['name']}](/servicios/{slug})")

    if not links:
        return ""

    lines = ["", "## Disponible en otras comunas de Santiago", ""]
    lines += links[:12]  # Cap at 12 to avoid over-linking
    lines += [""]
    return "\n".join(lines)


def _build_hub_link_block(service_slug: str) -> str:
    """Links back up to the service hub page."""
    services = _load_services()
    svc = next((s for s in services if s["slug"] == service_slug), None)
    if not svc:
        return ""
    hub_slug = f"{service_slug}-santiago-centro"
    hub_file = _NEXTJS_DIR / "content" / "servicios" / f"{hub_slug}.md"
    if not hub_file.exists():
        return ""  # skip until the hub page is generated
    return (
        f"\n\n---\n\n"
        f"Ver todos los servicios de **{svc['service']}** en Santiago → "
        f"[{svc['service'].capitalize()} en Santiago](/servicios/{hub_slug})\n"
    )


def _build_blog_service_links(blog_content: str) -> str:
    """
    Detects which service the blog post is about and returns a
    'Te puede interesar' section with links to priority commune pages.
    """
    content_lower = blog_content.lower()

    # Detect service from content keywords
    detected_service = None
    for keyword, svc_slug in _BLOG_SERVICE_MAP.items():
        if keyword in content_lower:
            detected_service = svc_slug
            break

    if not detected_service:
        return ""

    servicios_dir = _NEXTJS_DIR / "content" / "servicios"

    def _commune_links(service_slug: str) -> list[str]:
        result = []
        for commune_slug, commune_name in _PRIORITY_COMMUNES:
            slug = f"{service_slug}-{commune_slug}"
            if (servicios_dir / f"{slug}.md").exists():
                result.append(f"- [{commune_name}](/servicios/{slug})")
        return result

    links = _commune_links(detected_service)

    # Fallback: if no commune pages exist for the detected service yet,
    # link to peluqueria-canina communes (they always exist first).
    if not links and detected_service != "peluqueria-canina":
        links = _commune_links("peluqueria-canina")

    if not links:
        return ""

    lines = ["", "## Agenda tu cita en tu comuna", ""]
    lines += links
    lines += [""]
    return "\n".join(lines)


# ── Content enrichment ────────────────────────────────────────────────────────

def _already_enriched(content: str) -> bool:
    return "## Disponible en otras comunas" in content or "## Agenda tu cita en tu comuna" in content


def enrich_service_page_content(
    content: str,
    service_slug: str,
    commune_slug: str,
) -> str:
    """Adds internal links to a service page markdown string."""
    if _already_enriched(content):
        return content

    related = _build_related_communes_block(service_slug, commune_slug)
    hub     = _build_hub_link_block(service_slug)
    return content.rstrip() + "\n" + related + hub


def enrich_blog_post(filepath: Path, dry_run: bool = False) -> bool:
    """
    Reads a blog post markdown file and appends service internal links.
    Returns True if the file was (or would be) modified.
    """
    content = filepath.read_text(encoding="utf-8")

    if _already_enriched(content):
        log.info(f"  [skip] Already enriched: {filepath.name}")
        return False

    addition = _build_blog_service_links(content)
    if not addition:
        log.info(f"  [skip] No matching service detected: {filepath.name}")
        return False

    enriched = content.rstrip() + "\n" + addition

    if dry_run:
        log.info(f"  [dry-run] Would add {len(addition.splitlines())} lines to {filepath.name}")
        return True

    filepath.write_text(enriched, encoding="utf-8")
    log.info(f"  [OK] Enriched: {filepath.name}")
    return True


# ── DB-level enrichment ───────────────────────────────────────────────────────

def enrich_generated_pages(dry_run: bool = False) -> None:
    """
    Fetches all generated pages from the DB and updates their content
    with internal links. Writes back to content_outputs.
    """
    from db import fetch_all, db as db_ctx

    rows = fetch_all("""
        SELECT co.id AS output_id, co.content, p.service_slug, p.commune_slug
        FROM content_outputs co
        JOIN pages p ON co.workflow_id = p.workflow_id
        WHERE p.status IN ('generated', 'published')
          AND co.content_type = 'landing'
    """)

    if not rows:
        log.info("No generated landing pages found in DB.")
        return

    log.info(f"Found {len(rows)} generated landing page(s) to process")
    enriched_count = 0

    for row in rows:
        content      = row.get("content") or ""
        service_slug = row["service_slug"]
        commune_slug = row["commune_slug"]

        if _already_enriched(content):
            continue

        new_content = enrich_service_page_content(content, service_slug, commune_slug)

        if dry_run:
            log.info(f"  [dry-run] Would enrich: {service_slug}__{commune_slug}")
            enriched_count += 1
            continue

        with db_ctx() as conn:
            conn.execute(
                "UPDATE content_outputs SET content = ? WHERE id = ?",
                (new_content, row["output_id"]),
            )
        log.info(f"  [OK] Enriched DB content: {service_slug}__{commune_slug}")
        enriched_count += 1

    log.info(f"Done. Enriched {enriched_count}/{len(rows)} page(s).")


def enrich_blog_posts(dry_run: bool = False) -> None:
    """Enriches all blog markdown files with internal service links."""
    if not _BLOG_DIR.exists():
        log.warning(f"Blog directory not found: {_BLOG_DIR}")
        return

    md_files = list(_BLOG_DIR.glob("*.md"))
    log.info(f"Found {len(md_files)} blog post(s) to process")

    enriched = 0
    for f in md_files:
        if enrich_blog_post(f, dry_run=dry_run):
            enriched += 1

    log.info(f"Done. Enriched {enriched}/{len(md_files)} blog post(s).")


# ── CLI ───────────────────────────────────────────────────────────────────────

def audit_broken_links() -> None:
    """Scans all deployed .md files for internal links pointing to non-existent pages."""
    servicios_dir = _NEXTJS_DIR / "content" / "servicios"
    blog_dir      = _NEXTJS_DIR / "content" / "blog"
    app_dir       = _NEXTJS_DIR / "src" / "app"
    all_dirs      = [d for d in [servicios_dir, blog_dir] if d.exists()]

    # Slugs from .md content files
    existing_slugs = {
        f.stem
        for d in [servicios_dir, blog_dir] if d.exists()
        for f in d.glob("*.md")
    }

    # Slugs from static Next.js app directory routes (e.g. app/servicios/bano/page.tsx)
    for route_dir in [app_dir / "servicios", app_dir / "blog"]:
        if route_dir.exists():
            for entry in route_dir.iterdir():
                if entry.is_dir() and not entry.name.startswith("[") and (entry / "page.tsx").exists():
                    existing_slugs.add(entry.name)

    broken: list[tuple[str, str]] = []
    link_re = re.compile(r'\]\(/(?:servicios|blog)/([^/)]+)\)')

    for d in all_dirs:
        for f in d.glob("*.md"):
            for match in link_re.finditer(f.read_text(encoding="utf-8")):
                target = match.group(1)
                if target not in existing_slugs:
                    broken.append((f.name, target))

    if broken:
        log.warning(f"[audit] Found {len(broken)} broken internal link(s):")
        for source, target in broken:
            log.warning(f"  {source} → /servicios/{target} (404)")
    else:
        log.info("[audit] No broken internal links found. ✓")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog        = "enrich_internal_links.py",
        description = "Marketing OS — Internal linking enricher for WashDog SEO",
        formatter_class = argparse.RawDescriptionHelpFormatter,
        epilog = """
Examples:
  python enrich_internal_links.py --all           # enrich DB pages + blog posts
  python enrich_internal_links.py --blog          # blog posts only
  python enrich_internal_links.py --all --dry-run # preview without writing
  python enrich_internal_links.py --audit         # scan for broken internal links
        """,
    )
    parser.add_argument("--all",     action="store_true", help="Enrich DB landing pages + blog posts")
    parser.add_argument("--blog",    action="store_true", help="Enrich blog markdown files only")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--audit",   action="store_true", help="Scan all .md files for broken internal links")

    args = parser.parse_args()

    if args.audit:
        audit_broken_links()
    elif args.all:
        enrich_generated_pages(dry_run=args.dry_run)
        enrich_blog_posts(dry_run=args.dry_run)
    elif args.blog:
        enrich_blog_posts(dry_run=args.dry_run)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
