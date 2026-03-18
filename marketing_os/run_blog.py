#!/usr/bin/env python3
"""
Marketing OS — Blog Runner
WashDog automated blog generation for SEO authority.

Phase 1: 36 core authority posts (blog_topics.csv)   — 3/week for 8 weeks
Phase 2: 112+ breed-specific articles (breed_articles.csv) — long-tail SEO

Flow per post:
  1. Pick next pending topic from CSV (skip if .md already exists)
  2. Run blog_seo workflow (keyword research → outline → article → score)
  3. Write .md to washdog-website/content/blog/
  4. Git commit + push → Vercel deploys automatically
  5. Submit URL to Google Search Console for indexing

Usage:
    python run_blog.py                   # auto catch-up (recommended for cron)
    python run_blog.py --batch 1         # generate exactly 1 post
    python run_blog.py --phase 2         # breed articles (after phase 1 is done)
    python run_blog.py --dry-run         # preview without generating
    python run_blog.py --status          # show progress
"""

import argparse
import csv
import json
import logging
import os
import re
import subprocess
import sys
import time
import unicodedata
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

# ── Paths ─────────────────────────────────────────────────────────────────────

_MARKETING_DIR = Path(__file__).parent
_WEBSITE_DIR   = Path(os.environ.get("WASHDOG_WEBSITE_DIR", "/Users/enriqueibarra/washdog-website"))
_BLOG_DIR      = _WEBSITE_DIR / "content" / "blog"
_LOG_DIR       = _MARKETING_DIR / "logs"
_STATE_FILE    = _MARKETING_DIR / "state" / "blog_state.json"
_TOPICS_CSV    = _MARKETING_DIR / "keywords" / "blog_topics.csv"
_BREEDS_CSV    = _MARKETING_DIR / "keywords" / "breed_articles.csv"

BASE_URL = "https://www.washdog.cl"

# Posts written by hand — never regenerate these
_EXISTING_SLUGS = {
    "frecuencia-bano-perros",
    "shampoo-correcto-perros",
    "senales-corte-pelo-perro",
    "peluqueria-canina-nunoa",
    "auto-lavado-perros-nunoa",
    "peluqueria-gatos-nunoa",
    "precio-peluqueria-canina-nunoa",
}

# Phase 1 target: 36 posts at 3/week
_PHASE1_TARGET   = 36
_PHASE1_PER_WEEK = 3
_PHASE2_PER_WEEK = 5

_LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [run_blog] %(message)s",
    handlers=[
        logging.FileHandler(_LOG_DIR / "run_blog.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ── State ─────────────────────────────────────────────────────────────────────

def _load_state() -> dict:
    if _STATE_FILE.exists():
        return json.loads(_STATE_FILE.read_text())
    state = {"start_date": date.today().isoformat(), "phase": 1}
    _STATE_FILE.parent.mkdir(exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2))
    return state


def _count_deployed(phase: int) -> int:
    """Count blog posts already deployed for the given phase."""
    if not _BLOG_DIR.exists():
        return 0
    deployed = {p.stem for p in _BLOG_DIR.glob("*.md")}
    if phase == 1:
        topics = _load_topics(1)
        return sum(1 for t in topics if t["slug"] in deployed)
    else:
        topics = _load_topics(2)
        return sum(1 for t in topics if t["slug"] in deployed)


def _calculate_catchup_batch(base_batch: int, phase: int) -> int:
    """
    How many posts should we generate today?
    If the laptop was off and we're behind schedule, catch up automatically.
    Caps at 5 to avoid burning too many Claude tokens in one run.
    """
    state        = _load_state()
    start        = date.fromisoformat(state["start_date"])
    days_elapsed = (date.today() - start).days
    per_week     = _PHASE1_PER_WEEK if phase == 1 else _PHASE2_PER_WEEK
    target       = _PHASE1_TARGET if phase == 1 else len(_load_topics(2))

    expected  = min(target, round(days_elapsed * per_week / 7))
    deployed  = _count_deployed(phase)
    behind    = max(0, expected - deployed)
    catchup   = max(base_batch, behind)
    return min(catchup, 5)  # never more than 5 in one run


# ── CSV loaders ───────────────────────────────────────────────────────────────

def _load_topics(phase: int) -> list[dict]:
    csv_file = _TOPICS_CSV if phase == 1 else _BREEDS_CSV
    if not csv_file.exists():
        return []
    with open(csv_file, newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if int(r.get("phase", 1)) == phase]


def _get_pending_topics(phase: int) -> list[dict]:
    """Topics from CSV that don't have a deployed .md file yet."""
    deployed = {p.stem for p in _BLOG_DIR.glob("*.md")} if _BLOG_DIR.exists() else set()
    topics   = _load_topics(phase)
    return [t for t in topics if t["slug"] not in deployed and t["slug"] not in _EXISTING_SLUGS]


# ── Slug / helpers ────────────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    slug = ascii_only.lower().strip()
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"[^a-z0-9\-]", "", slug)
    return re.sub(r"-{2,}", "-", slug).strip("-")


def _read_time(content: str) -> str:
    words = len(content.split())
    mins  = max(2, round(words / 200))
    return f"{mins} min"


# ── Deploy ────────────────────────────────────────────────────────────────────

def _build_blog_md(title: str, description: str, content: str, category: str, today: str) -> str:
    read_time = _read_time(content)
    # Strip any accidental code fences from generated content
    content = re.sub(r"^```[a-z]*\n?", "", content.strip())
    content = re.sub(r"\n?```$", "", content.strip())
    frontmatter = (
        f"---\n"
        f'title: "{title}"\n'
        f'description: "{description}"\n'
        f'date: "{today}"\n'
        f'category: "{category}"\n'
        f'readTime: "{read_time}"\n'
        f"---\n\n"
    )
    return frontmatter + content


def _deploy_post(slug: str, title: str, description: str, content: str, category: str) -> Path | None:
    """Write blog post .md to washdog-website/content/blog/. Returns path or None if skipped."""
    if slug in _EXISTING_SLUGS:
        log.warning(f"  [deploy] BLOCKED — '{slug}' is a hand-written post. Skipping.")
        return None

    # Strip leading H1 — page template renders post.title as <h1>; avoid duplicate
    content = re.sub(r"^#\s+[^\n]*\n?", "", content.strip(), count=1).strip()

    _BLOG_DIR.mkdir(parents=True, exist_ok=True)
    dest        = _BLOG_DIR / f"{slug}.md"
    today       = date.today().isoformat()
    new_content = _build_blog_md(title, description, content, category, today)

    if dest.exists():
        log.info(f"  [deploy] Already exists, skipping: {slug}.md")
        return None

    dest.write_text(new_content, encoding="utf-8")
    log.info(f"  [deploy] Written: content/blog/{slug}.md")
    return dest


def _git_push_posts(paths: list[Path]) -> None:
    """Commit and push new blog posts to trigger Vercel deploy."""
    if not paths:
        return
    try:
        rel = [str(p.relative_to(_WEBSITE_DIR)) for p in paths]
        n   = len(paths)
        msg = (
            f"content: add {n} blog post{'s' if n > 1 else ''} "
            f"({', '.join(p.stem for p in paths[:3])}{'...' if n > 3 else ''})"
        )
        subprocess.run(["git", "add"] + rel, cwd=_WEBSITE_DIR, check=True)
        subprocess.run(["git", "commit", "-m", msg], cwd=_WEBSITE_DIR, check=True)
        subprocess.run(["git", "push"], cwd=_WEBSITE_DIR, check=True)
        log.info(f"  [git] Pushed {n} blog post(s) — Vercel deploy triggered")
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


# ── Runner ────────────────────────────────────────────────────────────────────

def run_batch(batch: int | None = None, phase: int = 1, dry_run: bool = False, no_index: bool = False) -> None:
    """
    Generate up to `batch` blog posts from pending topics.
    If batch is None, auto-calculate catch-up count.
    Auto-progresses from Phase 1 → Phase 2 once Phase 1 is complete.
    """
    base     = 1 if batch is None else batch
    n_to_run = _calculate_catchup_batch(base, phase) if batch is None else batch

    pending = _get_pending_topics(phase)
    if not pending:
        deployed = _count_deployed(phase)
        total    = len(_load_topics(phase)) + (len(_EXISTING_SLUGS) if phase == 1 else 0)
        log.info(f"No pending topics for phase {phase}. Deployed: {deployed}/{total}")
        # Auto-progress: if Phase 1 is done and caller didn't specify a phase, run Phase 2
        if phase == 1 and batch is None:
            log.info("Phase 1 complete — auto-progressing to Phase 2 (breed articles)")
            run_batch(batch=None, phase=2, dry_run=dry_run, no_index=no_index)
        return

    # ── Crawl budget governor ─────────────────────────────────────────────────
    # Pause generation if Google has indexed < 60% of already-published posts.
    if not dry_run and not no_index and _BLOG_DIR.exists():
        from indexing import check_indexing_health
        deployed_urls = [
            f"{BASE_URL}/blog/{p.stem}"
            for p in sorted(_BLOG_DIR.glob("*.md"))
            if p.stem not in _EXISTING_SLUGS
        ]
        health = check_indexing_health(deployed_urls)
        if health["below_threshold"]:
            log.warning(
                f"[governor] Blog indexing rate {health['rate']:.0%} is below "
                f"{health['threshold']:.0%} threshold "
                f"({health['indexed']}/{health['checked']} sampled posts indexed). "
                f"Pausing batch — Google needs to catch up. "
                f"Will retry in ~6h or run with --no-index to bypass."
            )
            return

    log.info(f"Phase {phase} | Pending: {len(pending)} topics | Generating: {n_to_run}")

    deployed_paths: list[Path] = []
    succeeded = 0
    failed    = 0

    for topic in pending[:n_to_run]:
        slug     = topic["slug"]
        t        = topic["topic"]
        keyword  = topic["target_keyword"]
        city     = topic.get("city", "Santiago")
        category = topic.get("category", "Cuidado")

        # Extra context for breed articles
        breed_context = f" ({topic['breed']})" if "breed" in topic else ""
        log.info(f"[{slug}] Starting: '{t}'{breed_context}")

        if dry_run:
            log.info(f"  [dry-run] Would generate: {slug} | '{keyword}'")
            succeeded += 1
            continue

        try:
            from workflows.blog_seo import run_blog_seo

            result = run_blog_seo(
                topic          = t,
                target_keyword = keyword,
                city           = city,
                breed          = topic.get("breed") or None,
            )

            overall = result.get("scores", {}).get("overall_score", 0)
            log.info(f"  [OK] workflow={result['workflow_id'][:8]}  score={overall}/100  '{result['title'][:55]}'")

            path = _deploy_post(
                slug        = slug,
                title       = result["title"],
                description = result["meta_description"],
                content     = result["content"],
                category    = category,
            )
            if path:
                deployed_paths.append(path)

            succeeded += 1
            time.sleep(2)

        except Exception as e:
            log.error(f"  [FAIL] {slug}: {e}")
            failed += 1

    if deployed_paths:
        _git_push_posts(deployed_paths)
        # One sitemap resubmission covers all new posts — no per-URL API calls needed
        if not no_index:
            _resubmit_sitemap()

    remaining = len(pending) - succeeded - failed
    log.info(
        f"Done. Succeeded: {succeeded} | Failed: {failed} | "
        f"Deployed: {len(deployed_paths)} | Remaining: {remaining}"
    )


def print_status() -> None:
    state    = _load_state()
    start    = date.fromisoformat(state["start_date"])
    elapsed  = (date.today() - start).days

    deployed_slugs = {p.stem for p in _BLOG_DIR.glob("*.md")} if _BLOG_DIR.exists() else set()
    p1_topics      = _load_topics(1)
    p2_topics      = _load_topics(2)
    p1_done        = sum(1 for t in p1_topics if t["slug"] in deployed_slugs) + len(
        _EXISTING_SLUGS & deployed_slugs
    )
    p1_total       = len(p1_topics)
    p2_done        = sum(1 for t in p2_topics if t["slug"] in deployed_slugs)
    p2_total       = len(p2_topics)

    print(f"\nBlog Status — WashDog Marketing OS")
    print(f"  Start date : {state['start_date']} ({elapsed} days ago)")
    print(f"  Phase 1    : {p1_done}/{p1_total} posts (target: {_PHASE1_TARGET})")
    print(f"  Phase 2    : {p2_done}/{p2_total} breed articles")
    print(f"  Total live : {len(deployed_slugs)} posts in content/blog/")
    catchup = _calculate_catchup_batch(1, 1)
    print(f"  Next run   : generate {catchup} post(s) (catch-up included)")
    print()


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog        = "run_blog.py",
        description = "Marketing OS — Automated blog generation for WashDog",
        formatter_class = argparse.RawDescriptionHelpFormatter,
        epilog = """
Examples:
  python run_blog.py                   # auto catch-up (use this for cron)
  python run_blog.py --batch 1         # exactly 1 post
  python run_blog.py --batch 3         # exactly 3 posts
  python run_blog.py --phase 2         # breed articles
  python run_blog.py --dry-run         # preview without generating
  python run_blog.py --status          # show progress summary
        """,
    )
    parser.add_argument("--batch",    type=int,            help="Force exact number of posts (default: auto catch-up)")
    parser.add_argument("--phase",    type=int, default=1, help="1=core posts, 2=breed articles (default: 1)")
    parser.add_argument("--dry-run",  action="store_true", help="Preview without calling Claude")
    parser.add_argument("--no-index", action="store_true", help="Skip GSC indexing submission")
    parser.add_argument("--status",   action="store_true", help="Show blog progress and exit")

    args = parser.parse_args()

    if args.status:
        print_status()
        return

    run_batch(
        batch    = args.batch,
        phase    = args.phase,
        dry_run  = args.dry_run,
        no_index = args.no_index,
    )


if __name__ == "__main__":
    main()
