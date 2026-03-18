# Marketing Agency — Claude Instructions

## Project
WashDog (washdog.cl) — programmatic SEO machine for a dog grooming business in Santiago, Chile.

- Marketing OS: `marketing_os/` (Python, SQLite, cron-driven)
- Website: `/Users/enriqueibarra/washdog-website/` (Next.js, Vercel)
- Full context: see `memory/MEMORY.md` and `memory/programmatic_seo_safety.md`

## Always Apply: Programmatic SEO Safety Rules

When generating, reviewing, or modifying any landing page or blog content:

1. **No thin content** — every page needs unique local elements (neighborhoods, landmarks, local testimonials). Same template + only location changed = Google penalty risk.

2. **Batch limit: max 15 pages/day** — WashDog is a low-authority new site. Never increase above 15 pages per batch. Current setting of 10/day is correct.

3. **Vary CTA anchor text** — never repeat the same CTA phrase more than twice on a page. Use different phrasings across CTAs.

4. **No orphan pages** — always run `enrich_internal_links.py` after generating pages. Hub pages must link to all commune subpages.

5. **Sitemap after every batch** — always run `generate_sitemap.py` after deploying pages to notify Google.

Full safety guidelines: `memory/programmatic_seo_safety.md`

## Key Commands
```bash
cd marketing_os

# Generate pages
.venv/bin/python run_pending_pages.py --batch 10

# Generate blog posts
.venv/bin/python run_blog.py

# Sync to Google Sheets (deduped, best score per page)
.venv/bin/python sync_sheets.py --all --best-only

# Regenerate sitemap + submit to GSC
.venv/bin/python generate_sitemap.py

# Enrich internal links
.venv/bin/python enrich_internal_links.py --all

# GSC audit (indexing status)
.venv/bin/python check_gsc.py

# Analytics sync
.venv/bin/python sync_analytics.py --days 7
```

## Workflow After Any New Pages Are Generated
1. `generate_sitemap.py` — update sitemap + submit to GSC
2. `enrich_internal_links.py --all` — add internal links
3. `sync_sheets.py --all --best-only` — update tracking sheets
4. Manual GSC "Request Indexing" for priority pages if needed
