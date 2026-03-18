"""
Marketing OS — Indexing Module
WashDog programmatic SEO

How Google indexing actually works:
  ✅ Sitemap resubmission  — primary mechanism, reliable, no per-URL quota
  ✅ Internal links        — pages linked from indexed pages get crawled naturally
  ❌ URL Inspection API    — that API only CHECKS status, it does NOT submit pages
  ❌ There is no official Google API to "request indexing" for general pages

This module:
  1. Regenerates sitemap after each batch (content → data/local-pages.json → sitemap.xml)
  2. Resubmits sitemap to GSC via API so Google re-crawls it immediately
  3. Tracks daily resubmission attempts and raises clearly if something fails
  4. Keeps a log of every submission with timestamp so nothing is silent
  5. Crawl budget governor — spot-checks indexing rate, pauses generation if < 60%
"""

import json
import logging
import os
import subprocess
from datetime import date, datetime
from pathlib import Path

log = logging.getLogger(__name__)

_MARKETING_DIR = Path(__file__).parent
_WEBSITE_DIR   = Path(os.environ.get("WASHDOG_WEBSITE_DIR", "/Users/enriqueibarra/washdog-website"))
_STATE_DIR     = _MARKETING_DIR / "state"
_LOG_DIR       = _MARKETING_DIR / "logs"
_QUOTA_FILE    = _STATE_DIR / "indexing_quota.json"
_HEALTH_FILE   = _STATE_DIR / "indexing_health.json"
_SUBMIT_LOG    = _LOG_DIR / "indexing_submissions.log"

# GSC sitemap resubmission quota: 10,000/day — far more than we'll ever use
# URL Inspection quota:           2,000/day  — for status checks only
_DAILY_SUBMIT_LIMIT  = 50    # self-imposed conservative limit per day
_INDEXING_THRESHOLD  = 0.6   # pause generation if fewer than 60% of sampled pages are indexed
_HEALTH_CACHE_HOURS  = 6     # re-use last health check result for 6 hours


# ── Quota tracking ────────────────────────────────────────────────────────────

def _load_quota() -> dict:
    _STATE_DIR.mkdir(exist_ok=True)
    if _QUOTA_FILE.exists():
        data = json.loads(_QUOTA_FILE.read_text())
        if data.get("date") == date.today().isoformat():
            return data
    # Reset for new day
    data = {"date": date.today().isoformat(), "sitemap_submits": 0, "inspect_calls": 0}
    _QUOTA_FILE.write_text(json.dumps(data, indent=2))
    return data


def _save_quota(data: dict) -> None:
    _STATE_DIR.mkdir(exist_ok=True)
    _QUOTA_FILE.write_text(json.dumps(data, indent=2))


def _log_submission(action: str, detail: str, status: str) -> None:
    _LOG_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(_SUBMIT_LOG, "a", encoding="utf-8") as f:
        f.write(f"{ts} [{status}] {action}: {detail}\n")


# ── Sitemap resubmission (primary indexing mechanism) ─────────────────────────

def resubmit_sitemap(sitemap_url: str = "https://www.washdog.cl/sitemap.xml") -> bool:
    """
    Primary indexing mechanism. Tells Google to re-crawl the sitemap,
    which discovers all new pages in one call.

    Returns True on success, False on failure (never raises).
    """
    sc_site = os.environ.get("SEARCH_CONSOLE_SITE_URL", "").strip()
    if not sc_site:
        log.warning("[indexing] SEARCH_CONSOLE_SITE_URL not set — skipping sitemap resubmission")
        _log_submission("sitemap_submit", sitemap_url, "SKIPPED_NO_ENV")
        return False

    quota = _load_quota()
    if quota["sitemap_submits"] >= _DAILY_SUBMIT_LIMIT:
        log.warning(
            f"[indexing] Daily sitemap resubmission limit reached "
            f"({quota['sitemap_submits']}/{_DAILY_SUBMIT_LIMIT}). "
            f"Resets at midnight. No action needed — Google will re-crawl the sitemap within 24–48h."
        )
        _log_submission("sitemap_submit", sitemap_url, "QUOTA_LIMIT")
        return False

    try:
        from workspace.api import _get_credentials
        from googleapiclient.discovery import build

        creds   = _get_credentials()
        service = build("searchconsole", "v1", credentials=creds)
        service.sitemaps().submit(siteUrl=sc_site, feedpath=sitemap_url).execute()

        quota["sitemap_submits"] += 1
        _save_quota(quota)

        log.info(
            f"[indexing] Sitemap submitted to GSC: {sitemap_url} "
            f"(today: {quota['sitemap_submits']}/{_DAILY_SUBMIT_LIMIT})"
        )
        _log_submission("sitemap_submit", sitemap_url, "OK")
        return True

    except Exception as e:
        log.error(
            f"[indexing] Sitemap resubmission FAILED: {e}\n"
            f"           → Google will still re-crawl within 24–48h via the existing submission.\n"
            f"           → Fix: check GSC credentials or run manually in GSC > Sitemaps."
        )
        _log_submission("sitemap_submit", sitemap_url, f"ERROR: {e}")
        return False


def regenerate_and_resubmit() -> bool:
    """
    Full indexing pipeline after a new batch is deployed:
      1. Run generate_sitemap.py to update data/local-pages.json + sitemap-local.xml
      2. Git commit + push the updated sitemap files
      3. Submit sitemap to GSC

    Call this once after each batch, not once per page.
    Returns True if all steps succeeded.
    """
    marketing_dir = str(_MARKETING_DIR)
    python        = str(_MARKETING_DIR / ".venv" / "bin" / "python")

    # Step 1: regenerate sitemap
    try:
        result = subprocess.run(
            [python, "generate_sitemap.py"],
            cwd=marketing_dir, capture_output=True, text=True
        )
        if result.returncode != 0:
            log.error(f"[indexing] generate_sitemap.py failed:\n{result.stderr}")
            _log_submission("regenerate_sitemap", "generate_sitemap.py", f"ERROR: {result.stderr[:200]}")
            return False
        log.info(f"[indexing] Sitemap regenerated")
    except Exception as e:
        log.error(f"[indexing] Could not run generate_sitemap.py: {e}")
        return False

    # Step 2: git add + commit sitemap files
    sitemap_files = [
        "data/local-pages.json",
        "public/sitemap-local.xml",
    ]
    try:
        # Only commit if there are changes
        status = subprocess.run(
            ["git", "status", "--porcelain"] + sitemap_files,
            cwd=str(_WEBSITE_DIR), capture_output=True, text=True
        )
        if status.stdout.strip():
            subprocess.run(["git", "add"] + sitemap_files, cwd=str(_WEBSITE_DIR), check=True)
            subprocess.run(
                ["git", "commit", "-m", "chore: update sitemap after new pages deployed"],
                cwd=str(_WEBSITE_DIR), check=True
            )
            subprocess.run(["git", "push"], cwd=str(_WEBSITE_DIR), check=True)
            log.info("[indexing] Sitemap files committed and pushed")
        else:
            log.info("[indexing] Sitemap unchanged — no commit needed")
    except subprocess.CalledProcessError as e:
        log.warning(f"[indexing] Sitemap git push failed: {e} (resubmission will continue)")

    # Step 3: tell GSC to re-crawl the sitemap
    return resubmit_sitemap()


# ── URL status check (inspection only, not submission) ────────────────────────

def check_url_indexed(url: str) -> dict:
    """
    Checks whether a URL is indexed in Google. Returns a status dict.
    This uses the URL Inspection API for CHECKING only — not for requesting indexing.
    Quota: 2,000/day.
    """
    sc_site = os.environ.get("SEARCH_CONSOLE_SITE_URL", "").strip()
    if not sc_site:
        return {"url": url, "status": "unknown", "error": "SEARCH_CONSOLE_SITE_URL not set"}

    quota = _load_quota()
    if quota["inspect_calls"] >= 1800:  # leave 200 buffer below 2,000 limit
        log.warning(f"[indexing] URL Inspection daily quota nearly exhausted ({quota['inspect_calls']}/2000). Skipping.")
        return {"url": url, "status": "skipped", "error": "quota_limit"}

    try:
        from workspace.api import _get_credentials
        from googleapiclient.discovery import build

        creds   = _get_credentials()
        service = build("searchconsole", "v1", credentials=creds)
        resp    = service.urlInspection().index().inspect(
            body={"inspectionUrl": url, "siteUrl": sc_site}
        ).execute()

        quota["inspect_calls"] += 1
        _save_quota(quota)

        result  = resp.get("inspectionResult", {})
        verdict = result.get("indexStatusResult", {}).get("verdict", "UNKNOWN")
        return {
            "url":          url,
            "status":       verdict,
            "coverage":     result.get("indexStatusResult", {}).get("coverageState", ""),
            "last_crawled": result.get("indexStatusResult", {}).get("lastCrawlTime", ""),
        }
    except Exception as e:
        return {"url": url, "status": "error", "error": str(e)}


# ── Crawl budget governor ─────────────────────────────────────────────────────

def check_indexing_health(
    published_urls: list[str],
    sample_size: int = 10,
) -> dict:
    """
    Crawl budget governor. Spot-checks a sample of published URLs to estimate
    what fraction Google has actually indexed.

    Results are cached for _HEALTH_CACHE_HOURS to avoid burning URL Inspection
    quota on every cron run.

    Returns:
        rate             — fraction of sampled pages confirmed indexed (0.0–1.0)
        indexed          — count confirmed indexed
        checked          — count actually checked (skipped if quota exhausted)
        below_threshold  — True if rate < _INDEXING_THRESHOLD (caller should pause)
        cached           — True if result came from cache
    """
    _STATE_DIR.mkdir(exist_ok=True)

    # Return cached result if fresh enough
    if _HEALTH_FILE.exists():
        try:
            cached = json.loads(_HEALTH_FILE.read_text())
            age_h = (datetime.now() - datetime.fromisoformat(cached["checked_at"])).total_seconds() / 3600
            if age_h < _HEALTH_CACHE_HOURS:
                log.info(
                    f"[governor] Cached health: {cached['indexed']}/{cached['checked']} indexed "
                    f"({cached['rate']:.0%}) — {age_h:.1f}h old"
                )
                return {**cached, "cached": True}
        except Exception:
            pass

    if not published_urls:
        return {"rate": 1.0, "indexed": 0, "checked": 0, "below_threshold": False, "cached": False}

    # Sample the most recently published pages (end of list = newest)
    sample = published_urls[-sample_size:] if len(published_urls) > sample_size else published_urls

    results = []
    for url in sample:
        result = check_url_indexed(url)
        results.append(result)
        if result.get("status") == "skipped":
            break  # quota exhausted — stop early

    checked = sum(1 for r in results if r.get("status") not in ("skipped", "error"))
    if checked == 0:
        log.warning("[governor] Could not check any URLs (quota exhausted or no env). Assuming healthy.")
        return {"rate": 1.0, "indexed": 0, "checked": 0, "below_threshold": False, "cached": False}

    indexed          = sum(1 for r in results if r.get("status") == "PASS")
    rate             = indexed / checked
    below_threshold  = rate < _INDEXING_THRESHOLD

    data = {
        "rate":            rate,
        "indexed":         indexed,
        "checked":         checked,
        "below_threshold": below_threshold,
        "threshold":       _INDEXING_THRESHOLD,
        "checked_at":      datetime.now().isoformat(),
        "cached":          False,
    }
    _HEALTH_FILE.write_text(json.dumps(data, indent=2))
    _log_submission("health_check", f"{checked} URLs sampled", f"rate={rate:.0%} {'BELOW_THRESHOLD' if below_threshold else 'OK'}")

    log.info(
        f"[governor] Indexing health: {indexed}/{checked} indexed ({rate:.0%}) "
        f"— threshold {_INDEXING_THRESHOLD:.0%} "
        f"{'⚠ BELOW — generation will be paused' if below_threshold else '✓ OK'}"
    )
    return data
