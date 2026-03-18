# Marketing OS — WashDog Growth Infrastructure

An AI-powered marketing engine built on top of the [Marketing Skills](../README.md) library, tailored exclusively for **WashDog** — a premium dog grooming salon in Santiago, Chile.

> **Not a generic tool.** Every prompt, every workflow, every evaluation criterion is tuned for WashDog's services, audience, pricing (CLP), and local SEO targets.

---

## Table of Contents

1. [What This System Does](#1-what-this-system-does)
2. [Full Architecture](#2-full-architecture)
3. [Folder Structure](#3-folder-structure)
4. [Quick Start](#4-quick-start)
5. [Phase 0–2 — Core Engine](#5-phase-02--core-engine)
6. [Phase 3 — Google Workspace Integration](#6-phase-3--google-workspace-integration)
7. [Phase 4 — Database, Workflows & Evaluations](#7-phase-4--database-workflows--evaluations)
8. [Phase 5 — Scheduler & Cost Control](#8-phase-5--scheduler--cost-control)
9. [Phase 6 — Full-Week Automation](#9-phase-6--full-week-automation)
10. [Phase 7 — Blog in Next.js (Planned)](#10-phase-7--blog-in-nextjs-planned)
11. [Phase 8 — Analytics Pipeline (Planned)](#11-phase-8--analytics-pipeline-planned)
12. [Phase 9 — QA & Auto-Deploy (Planned)](#12-phase-9--qa--auto-deploy-planned)
13. [Database Schema Reference](#13-database-schema-reference)
14. [Agent Reference](#14-agent-reference)
15. [Environment Variables](#15-environment-variables)
16. [Cost Reference](#16-cost-reference)

---

## 1. What This System Does

Marketing OS is a **measurable, automated marketing engine** that:

- Runs 23 specialized marketing agents (copywriting, SEO, ads, CRO, analytics...)
- Generates blog posts, landing pages, email campaigns, and seasonal promotions
- Scores every piece of content automatically (SEO, conversion, local relevance)
- Stores all outputs in SQLite with full token/cost tracking
- Syncs content to Google Docs, Sheets, and Drive
- Schedules weekly agent runs with dynamic budget control
- Will publish directly to a Next.js blog with SSG (Phase 7)

**Every output is a draft** — nothing is published without human review.

---

## 2. Full Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        MARKETING OS                             │
│                  WashDog Growth Infrastructure                  │
└──────────────┬──────────────────────────────────┬──────────────┘
               │                                  │
    ┌──────────▼──────────┐            ┌──────────▼──────────┐
    │   Workflow Engine   │            │    Agent Runner     │
    │  (Phase 4 — new)    │            │  (Phase 0-3 — base) │
    │                     │            │                     │
    │ • blog_seo.py        │            │ • runner.py         │
    │ • landing_page.py   │            │ • call_claude()     │
    │ • seasonal_campaign │            │ • 23 agents/        │
    │ • WorkflowRunner    │            │   SKILL.md files    │
    └──────────┬──────────┘            └──────────┬──────────┘
               │                                  │
    ┌──────────▼──────────────────────────────────▼──────────┐
    │                   Claude API (Anthropic)                │
    │         opus-4-6 / sonnet-4-6 / haiku-4-5              │
    └────────────────────────────┬────────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌────────▼────────┐   ┌──────────▼────────┐   ┌────────▼──────────┐
│  SQLite DB      │   │  Google Workspace  │   │  Local /outputs   │
│  state/         │   │  workspace/api.py  │   │                   │
│                 │   │                   │   │ docs/             │
│ • workflows     │   │ • Google Docs     │   │ sheets/           │
│ • steps         │   │ • Google Sheets   │   │ drive/            │
│ • content_      │   │ • Google Drive    │   │ logs/             │
│   outputs       │   │  (OAuth 2.0)      │   │                   │
│ • evaluations   │   └───────────────────┘   └───────────────────┘
│ • performance_  │
│   metrics       │            ┌─────────────────────────────────┐
└────────┬────────┘            │        Scheduler (Phase 5-6)    │
         │                     │        scheduler.py             │
┌────────▼────────┐            │                                 │
│  Evaluations    │            │ • Weekly calendar               │
│  evaluations/   │            │ • Budget policy (dynamic)       │
│  scorer.py      │            │ • agents_for_day()              │
│                 │            │ • run_full_week()               │
│ • SEO score     │            └─────────────────────────────────┘
│ • Readability   │
│ • Conversion    │            ┌─────────────────────────────────┐
│ • Local         │            │     Analytics (Phase 4)         │
│   relevance     │            │     analytics/queries.py        │
└─────────────────┘            │                                 │
                               │ • avg_seo_scores_by_type()      │
                               │ • cost_per_workflow()           │
                               │ • top_performing_content()      │
                               │ • agent_efficiency()            │
                               │ • monthly_cost_report()         │
                               └─────────────────────────────────┘
```

**Planned additions (Phase 7-9):**

```
Marketing OS
    │
    └── Next.js Blog (Phase 7)
            /content/blog/*.md  ←── generated by workflows
            /pages/blog/[slug]  ←── SSG rendering
            sitemap.xml         ←── auto-generated
                │
                └── GitHub Actions (Phase 9)
                        auto-commit + deploy on Vercel/Netlify
                            │
                            └── GA4 + Search Console (Phase 8)
                                    → back into performance_metrics table
```

---

## 3. Folder Structure

```
marketing_os/
│
├── agents/                         # 23 SKILL.md files (one per agent)
│   ├── copywriting/SKILL.md
│   ├── social-content/SKILL.md
│   ├── seo-audit/SKILL.md
│   └── ...
│
├── workflows/                      # Phase 4 — WashDog-specific workflows
│   ├── __init__.py
│   ├── base.py                     # WorkflowRunner base class
│   ├── blog_seo.py                 # Blog SEO workflow (3 steps)
│   ├── landing_page.py             # Landing page workflow (2 steps)
│   └── seasonal_campaign.py        # Seasonal campaign workflow (3 steps)
│
├── evaluations/                    # Phase 4 — AI quality scoring
│   ├── __init__.py
│   └── scorer.py                   # score_content() → evaluations table
│
├── analytics/                      # Phase 4 — Pre-written SQL queries
│   ├── __init__.py
│   └── queries.py                  # 9 dashboard queries
│
├── workspace/                      # Phase 3 — Google Workspace (OAuth 2.0)
│   ├── __init__.py
│   ├── api.py                      # create_doc, append_to_sheet, upload_file
│   ├── credentials.json            # ← you provide this (not in git)
│   └── .token.json                 # ← auto-generated after first login
│
├── context/                        # Business context and config
│   ├── business_context.md         # WashDog description, audience, services
│   ├── agents_config.json          # 23 agents: role, output_type, responsibility
│   ├── schedule_config.json        # Weekly schedule, budget, model assignments
│   ├── agent_responsibilities.md   # Human-readable agent table
│   ├── cost_schedule.md            # Phase 5 cost reference
│   └── weekly_plan.md              # Phase 6 execution calendar
│
├── state/
│   └── marketing_os.db             # SQLite database (auto-created)
│
├── outputs/                        # Local file saves (gitignored)
│   ├── docs/
│   ├── sheets/
│   ├── drive/
│   └── logs/
│           runner.log              # JSONL — every agent run
│
├── db.py                           # Phase 4 — SQLite connection + migrations
├── runner.py                       # Phase 0-3 — Core agent runner
├── scheduler.py                    # Phase 5-6 — Weekly scheduler
├── run_workflow.py                 # Phase 4 — Workflow CLI
├── run_nunoa.sh                    # Batch runner — all 4 Ñuñoa service pages
├── sync_sheets.py                  # Sync SQLite results → Google Sheets tracking
│
├── requirements.txt
├── .env                            # ← you create this (not in git)
├── .env.example                    # ← template with all required vars
├── .gitignore
└── README.md
```

---

## 4. Quick Start

### Prerequisites

- Python 3.11+
- Anthropic API key ([console.anthropic.com](https://console.anthropic.com))
- Google Cloud project with OAuth credentials (for Google Workspace sync)

### Setup

```bash
# 1. Clone and enter project
cd marketing_os/

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
# .env is already present — add your real API key:
#   ANTHROPIC_API_KEY=sk-ant-your-key-here

# 5. Initialize database
python db.py
# → Creates state/marketing_os.db with all 5 tables

# 6. (Optional) Google Workspace — first-time OAuth
#   Place your credentials.json in workspace/credentials.json
#   Then run any workflow — browser will open once for login
```

### Run your first workflow

```bash
# Generate a blog post
python run_workflow.py blog \
  --topic "cuidado del pelaje en verano" \
  --keyword "peluquería canina Santiago"

# Generate a landing page
python run_workflow.py landing \
  --service "baño antipulgas" \
  --location "Providencia" \
  --promotion "20% descuento primera visita"

# Generate a seasonal campaign
python run_workflow.py campaign \
  --name "Campaña Verano 2026" \
  --season verano \
  --offer "2x1 en baño hasta el 28 de febrero"

# View analytics report
python run_workflow.py report
```

### Run all Ñuñoa service pages

```bash
# Generate all 4 landing pages + 4 blog posts for the Ñuñoa services
./run_nunoa.sh

# Landing pages only
./run_nunoa.sh --landing

# Blog posts only
./run_nunoa.sh --blog
```

All output is logged to `outputs/logs/nunoa_run_<timestamp>.log`. The 4 Ñuñoa services covered:

| Service | Blog keyword |
|---|---|
| Peluquería canina Ñuñoa | peluquería canina Ñuñoa |
| Auto lavado perros Ñuñoa | auto lavado perros Ñuñoa |
| Peluquería gatos Ñuñoa | peluquería gatos Ñuñoa |
| Precio peluquería Ñuñoa | precio peluquería canina Ñuñoa |

### Run the weekly scheduler

```bash
# Preview the week (no tokens spent)
python scheduler.py --preview-week

# Simulate full week (no tokens spent)
python scheduler.py --run-week --dry-run

# Execute today's agents
python scheduler.py

# Execute full week
python scheduler.py --run-week

# Check budget usage
python scheduler.py --budget-report
```

---

## 5. Phase 0–2 — Core Engine

### What was built

The base layer that powers everything:

- **`runner.py`** — the central execution pipeline
- **23 `agents/*/SKILL.md`** files — specialized marketing knowledge
- **`context/business_context.md`** — WashDog's brand, services, audience
- **`.venv/`** — isolated Python environment (required on macOS)

### How `runner.py` works

```
run_agent(agent_name, task_input, model)
    │
    ├── validate_agent()          ← checks agents/ + agents_config.json
    ├── load_skill()              ← reads agents/{name}/SKILL.md
    ├── load_business_context()   ← reads context/business_context.md
    ├── build_prompt()            ← combines: context + skill + task
    ├── call_claude()             ← sends to Anthropic API, tracks tokens
    ├── save_output()             ← saves to outputs/docs/ or sheets/
    ├── upload_to_google()        ← syncs to Google Docs/Sheets/Drive
    ├── log_task()                ← writes JSONL to outputs/logs/runner.log
    └── returns dict:
            agent, role, output_type, saved_path, google, content, tokens
```

### Using the agent runner directly

```bash
# Run any agent on-demand
python runner.py --agent social-content \
  --task "5 posts Instagram para WashDog esta semana"

# Run with specific model
python runner.py --agent copywriting \
  --task "Homepage copy para WashDog" \
  --model claude-opus-4-6

# List all available agents
python runner.py --list
```

### Using runner.py from Python

```python
from runner import run_agent

result = run_agent(
    agent_name = "social-content",
    task_input = {
        "task_description": "5 posts Instagram para WashDog, temporada verano",
        "output_type": "doc",
        "title": "Social Content — Verano 2026",
    },
    model = "claude-sonnet-4-6",
)

print(result["content"])
print(f"Saved: {result['saved_path']}")
print(f"Cost:  ${result['tokens']['cost_usd']:.4f} USD")
if result["google"]:
    print(f"Docs:  {result['google']['url']}")
```

---

## 6. Phase 3 — Google Workspace Integration

### Authentication

Uses **OAuth 2.0 Desktop App** (not Service Account — more org-compatible).

**First-time setup:**

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Enable: Google Drive API, Google Docs API, Google Sheets API
3. Create credentials: `APIs & Services → Credentials → OAuth 2.0 Client IDs → Desktop app`
4. Download JSON → save as `workspace/credentials.json`
5. Run any workflow → browser opens once for login
6. Token saved automatically to `workspace/.token.json` (refreshes silently)

**Scopes used:**
- `documents` — create/edit Google Docs
- `spreadsheets` — create/append Google Sheets
- `drive.file` — upload to Drive (only files created by this app)

### Drive folder structure

All content is organized under `MarketingOS/` in your Drive:

```
MarketingOS/
├── docs/      ← Blog posts, landing pages, email campaigns
├── sheets/    ← Analytics data, ad performance, SEO audits
└── drive/     ← Raw file uploads
```

### Using workspace/api.py directly

```python
from workspace.api import create_doc, append_to_sheet, get_or_create_folder

# Create a Google Doc
doc_id = create_doc("My Blog Post", "# Content here...", folder_id="...")
print(f"https://docs.google.com/document/d/{doc_id}/edit")

# Append rows to a Sheet
sheet_id = append_to_sheet("SEO Metrics", [["URL", "Clicks"], ["/blog/post", 42]])

# Get or create a folder
folder_id = get_or_create_folder("MarketingOS")
```

---

## 7. Phase 4 — Database, Workflows & Evaluations

### What was built

- **`db.py`** — SQLite connection manager, table migrations, helpers
- **`workflows/`** — 3 WashDog-specific AI workflow pipelines
- **`evaluations/scorer.py`** — automatic quality scoring via Claude Haiku
- **`analytics/queries.py`** — 9 pre-written dashboard queries
- **`run_workflow.py`** — unified CLI for all workflows

### The three workflow types

#### 1. Blog SEO Workflow (`blog_seo.py`)

Generates complete SEO blog posts for WashDog's dog care topics.

```
Step 1: keyword_research   → 10 long-tail Chile keywords
Step 2: outline_generation → title + meta description + headings (JSON)
Step 3: article_writing    → 900–1,200 word Markdown article
Step 4: seo_evaluation     → AI quality scoring (haiku, low cost)
```

```bash
python run_workflow.py blog \
  --topic "cómo deslanar un golden retriever en verano" \
  --keyword "deslanado canino Santiago" \
  --city "Las Condes"
```

#### 2. Landing Page Workflow (`landing_page.py`)

Generates conversion-optimized service pages.

```
Step 1: market_positioning → value prop, objections, trust signals
Step 2: copy_generation    → full landing page Markdown with CTA
Step 3: conversion_scoring → AI evaluation
```

```bash
python run_workflow.py landing \
  --service "corte de pelo canino" \
  --location "Ñuñoa" \
  --promotion "primera visita $19.990 CLP"
```

**Current service pages (all in `_BUSINESS_CONTEXT`):**

| Service | Canonical URL |
|---|---|
| Baño completo | `/servicios/bano-completo` |
| Corte de pelo canino | `/servicios/corte-pelo-canino` |
| Tratamiento antipulgas | `/servicios/antipulgas` |
| Deslanado | `/servicios/deslanado` |
| Corte y lima de uñas | `/servicios/corte-unas` |
| Peluquería canina Ñuñoa | `/servicios/peluqueria-canina-nunoa` |
| Auto lavado perros Ñuñoa | `/servicios/auto-lavado-perros-nunoa` |
| Peluquería gatos Ñuñoa | `/servicios/peluqueria-gatos-nunoa` |
| Precio peluquería Ñuñoa | `/servicios/precio-peluqueria-nunoa` |

These URLs are the canonical list used by `blog_seo.py` when generating internal links. To add a new service page, update `_BUSINESS_CONTEXT` in both `workflows/landing_page.py` and `workflows/blog_seo.py`, and add its URL to the internal link prompt in `blog_seo.py`.

#### 3. Seasonal Campaign Workflow (`seasonal_campaign.py`)

Generates multi-channel campaigns with copy for every channel + ROI projection.

```
Step 1: campaign_angle     → creative concept, emotional hook, urgency
Step 2: multichannel_copy  → Instagram, WhatsApp, Google Ads, Email (JSON)
Step 3: roi_projection     → 3-scenario ROI table in CLP
Step 4: campaign_scoring   → AI evaluation
```

```bash
python run_workflow.py campaign \
  --name "Fiestas Patrias 2026 — Baño Premium" \
  --season "fiestas patrias" \
  --offer "3 servicios por el precio de 2, hasta el 20 de septiembre"
```

### Evaluation scoring

Every piece of content is automatically scored after generation:

| Score | Weight | What it measures |
|---|---|---|
| `seo_score` | 30% | Keyword density, heading structure, meta description |
| `readability_score` | 20% | Clarity, tone, paragraph length |
| `conversion_score` | 30% | CTA clarity, urgency, benefit language |
| `local_relevance_score` | 20% | Chile/Santiago mentions, CLP pricing, cultural fit |
| `overall_score` | — | Weighted average (0–100) |

Model used for scoring: **claude-haiku-4-5** (lowest cost, ~$0.001/evaluation).

### Analytics queries

```python
from analytics.queries import (
    avg_seo_scores_by_type,
    cost_per_workflow,
    top_performing_content,
    agent_efficiency,
    monthly_cost_report,
    print_report,
)

# Print dashboard in terminal
print_report("Top 5 Content", top_performing_content(5))
print_report("Cost by Workflow", cost_per_workflow())
print_report("Agent Efficiency", agent_efficiency())
```

Or from CLI:

```bash
python run_workflow.py report
python analytics/queries.py
```

---

## 8. Phase 5 — Scheduler & Cost Control

### What was built

- **`scheduler.py`** — weekly execution engine with dynamic budget gates
- **`context/schedule_config.json`** — full 23-agent schedule
- **`context/cost_schedule.md`** — cost reference documentation

### Agent priorities

| Priority | Agents | Default model |
|---|---|---|
| `critical` | copywriting, social-content, analytics-tracking, paid-ads, email-sequence | claude-opus-4-6 |
| `important` | seo-audit, page-cro, form-cro, popup-cro, schema-markup, ab-test-setup | claude-sonnet-4-6 |
| `support` | marketing-ideas, launch-strategy, onboarding-cro, and others | claude-haiku-4-5 |

### Dynamic budget policy

The scheduler automatically adjusts model selection based on monthly spend:

| Budget used | Action |
|---|---|
| 0–80% | Normal execution with configured models |
| 80–90% | Downgrade `support` + `important` agents to haiku |
| 90–100% | Skip `support` agents, downgrade `critical` to sonnet |
| >100% | Block all execution until next month |

### Scheduler commands

```bash
# Run today's agents
python scheduler.py

# Run a specific day
python scheduler.py --day tuesday

# Preview the week (no API calls)
python scheduler.py --preview-week

# Check budget
python scheduler.py --budget-report

# Dry-run full week
python scheduler.py --run-week --dry-run
```

---

## 9. Phase 6 — Full-Week Automation

### What was built

- `run_full_week()` in `scheduler.py` — executes Mon–Sun with inter-day budget gates
- `apply_budget_policy()` — automatic model downgrade at thresholds
- `context/weekly_plan.md` — calendar tables and execution snippets

### Weekly calendar (Week 1 & 3)

| Day | Agents | Model | Est. Cost |
|---|---|---|---|
| Monday | analytics-tracking, seo-audit | opus + sonnet | ~$0.19 |
| Tuesday | copywriting (2 posts) | opus | ~$0.16 |
| Wednesday | social-content (5 posts) | opus | ~$0.16 |
| Thursday | paid-ads (3 ads), page-cro | opus + sonnet | ~$0.19 |
| Friday | email-sequence (1 campaign) | opus | ~$0.16 |
| Saturday | marketing-ideas (5), onboarding-cro | haiku | ~$0.004 |
| Sunday | **Human Review** | — | $0 |

**Monthly cost estimate: ~$3.60 USD** (well within the $20/month budget).

### Running a full week from Python

```python
from scheduler import load_schedule_config, run_full_week

config = load_schedule_config()

# Dry run (no tokens spent)
run_full_week(config, dry_run=True)

# Real execution
run_full_week(config, dry_run=False)
```

---

## 10. Phase 7 — Blog in Next.js (Planned)

### Goal

Publish Marketing OS-generated blog posts directly to the WashDog website using Next.js Static Site Generation (SSG). Every article is version-controlled, indexable by Google, and traceable back to its workflow in the database.

### Architecture

```
Marketing OS (Python)
    │
    ├── run_workflow.py blog ...
    │       │
    │       └── Generates article + metadata
    │               │
    │               └── Writes: /content/blog/YYYY-MM-DD-slug.md
    │                           (includes frontmatter + Markdown body)
    │
    └── Commits to git repo → triggers GitHub Actions
            │
            └── Next.js build (SSG)
                    /pages/blog/[slug].tsx  ←── getStaticProps reads .md
                    /pages/blog/index.tsx   ←── lists all posts
                    /public/sitemap.xml     ←── auto-generated
```

### Markdown file format

Each generated blog post will be saved as:

```
/content/blog/2026-03-05-cuidados-pelaje-verano.md
```

With frontmatter:

```yaml
---
title: "Cuidado del pelaje en verano — WashDog Santiago"
date: "2026-03-05"
slug: "cuidados-del-pelaje-verano"
author: "WashDog Team"
keywords: ["peluquería canina", "Santiago", "cuidado del pelaje", "verano"]
meta_description: "Descubre cómo cuidar el pelaje de tu perro en verano. Servicio de deslanado y baño en Santiago."
workflow_id: "abc12345"
google_doc_url: "https://docs.google.com/document/d/.../edit"
seo_score: 82
overall_score: 79.4
---

# Cuidado del pelaje en verano...
[article body]
```

### Next.js pages to build

**`/pages/blog/[slug].tsx`** — individual post with SSG:

```tsx
export async function getStaticPaths() {
  const files = fs.readdirSync('content/blog')
  return {
    paths: files.map(f => ({ params: { slug: f.replace('.md', '') } })),
    fallback: false,
  }
}

export async function getStaticProps({ params }) {
  const raw = fs.readFileSync(`content/blog/${params.slug}.md`, 'utf-8')
  const { data: frontMatter, content } = matter(raw)
  return { props: { frontMatter, content } }
}
```

**`/pages/blog/index.tsx`** — posts listing:
- All posts sorted by date
- Excerpt, date, keywords, estimated read time
- Links to `/blog/[slug]`

**Dynamic SEO meta tags** (per post):

```tsx
<Head>
  <title>{frontMatter.title}</title>
  <meta name="description" content={frontMatter.meta_description} />
  <meta name="keywords" content={frontMatter.keywords.join(', ')} />
  <meta property="og:title" content={frontMatter.title} />
  <meta property="og:description" content={frontMatter.meta_description} />
</Head>
```

### Implementation tasks (Phase 7)

- [ ] Add `save_as_markdown()` to `WorkflowRunner.save_content()` — writes `.md` file with full frontmatter to `/content/blog/`
- [ ] Update `workflows/blog_seo.py` to call `save_as_markdown()` after content generation
- [ ] Create `/pages/blog/[slug].tsx` with `getStaticPaths` + `getStaticProps`
- [ ] Create `/pages/blog/index.tsx` with post listing
- [ ] Add `gray-matter` and `react-markdown` dependencies
- [ ] Create `scripts/generate-sitemap.ts` — reads `/content/blog/` and writes `/public/sitemap.xml`
- [ ] Store `commit_hash` in `content_outputs` table for rollback reference

---

## 11. Phase 8 — Analytics Pipeline (Planned)

### Goal

Close the feedback loop: read real-world performance data (GA4, Search Console) back into the `performance_metrics` table, enabling data-driven content decisions.

### Recommended integration sequence

Follow these steps in order — each one unblocks the next:

1. **Run `run_nunoa.sh`** — populate the DB with all Ñuñoa landing pages and blog posts. Verify scorer output is stable (no `TypeError` from float bars).
2. **Add Google Workspace credentials** — place `credentials.json` in `workspace/`. Run any workflow to trigger the OAuth browser flow and generate `.token.json`.
3. **Test Docs/Sheets sync** — run a single landing page workflow and confirm it appears in `MarketingOS/docs/` in your Drive.
4. **Add GA4 integration** — create `analytics/import_ga4.py` (see tasks below). Connect the `performance_metrics` table to real page view and conversion data.
5. **Expand to Search Console** — add `analytics/import_search_console.py` to pull ranking data (impressions, clicks, avg position) per service page URL.
6. **Connect Ads and other Google services** — once GA4 and Search Console are stable, wire in Google Ads conversion data to close the ROI loop.

### Extended `performance_metrics` schema

```sql
performance_metrics (
    id               TEXT PRIMARY KEY,
    workflow_id      TEXT,
    url              TEXT,              -- /blog/slug
    impressions      INTEGER,           -- Search Console
    clicks           INTEGER,           -- Search Console
    avg_position     REAL,              -- Search Console (keyword ranking)
    page_views       INTEGER,           -- GA4
    avg_time_on_page REAL,              -- GA4 (seconds)
    bounce_rate      REAL,              -- GA4
    conversions      INTEGER,           -- GA4 (bookings, WhatsApp clicks)
    revenue_generated REAL,             -- in CLP (if connected to booking system)
    recorded_at      DATETIME
)
```

### WashDog KPIs to track

**SEO KPIs:**
- Ranking for `"peluquería canina Santiago"` and variants
- Blog traffic growth (month-over-month)
- Number of indexed pages
- Click-through rate from Search Console

**Conversion KPIs:**
- WhatsApp button clicks per post
- Booking form submissions
- Coupon redemptions

**Business KPIs:**
- Cost per booking (campaign cost ÷ bookings)
- Revenue per campaign (bookings × avg ticket in CLP)
- ROI per workflow

### Implementation tasks (Phase 8)

- [ ] Create `analytics/import_ga4.py` — fetches data from GA4 Data API; writes to `performance_metrics`
- [ ] Create `analytics/import_search_console.py` — fetches impressions, clicks, avg position per URL
- [ ] Add `url` column to `performance_metrics` table (migration in `db.py`)
- [ ] Schedule weekly import via `scheduler.py` (new `analytics-import` step)
- [ ] Add `analytics/kpi_report.py` — WashDog KPI dashboard (bookings, WhatsApp clicks, revenue CLP)
- [ ] Update `analytics/queries.py` with real-performance joins (content score vs. actual traffic)
- [ ] Connect Google Ads conversion data for cost-per-booking tracking

---

## 12. Phase 9 — QA & Auto-Deploy (Planned)

### Goal

Automate the publish pipeline: Marketing OS generates content → passes quality gate → commits to repo → triggers Next.js deploy → Vercel/Netlify serves the new post.

### QA gate

Before committing a post, the system checks:
- `overall_score >= 70` (otherwise regenerates once, then flags for human review)
- `seo_score >= 65`
- `word_count >= 700`
- No placeholder text (e.g., `[INSERT]`, `TODO`)

### GitHub Actions workflow

```yaml
# .github/workflows/deploy-blog.yml
name: Deploy Blog Post

on:
  push:
    paths:
      - 'content/blog/**.md'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm ci
      - run: npm run build
      - run: npm run sitemap
      - uses: vercel/actions/deploy@v1
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
```

### Rollback strategy

Every post commit hash is stored in `content_outputs.commit_hash`. To rollback:

```bash
# Find the previous good commit hash from DB
python analytics/queries.py --rollback-info

# Revert the specific file
git checkout <commit_hash> -- content/blog/slug.md
git commit -m "revert: rollback post to previous version"
```

### Implementation tasks (Phase 9)

- [ ] Add `qa_gate()` function to `evaluations/scorer.py`
- [ ] Add `git_commit_post()` to `workflows/base.py` — commits `.md` to `marketing-os/blog` branch
- [ ] Store `commit_hash` in `content_outputs` table
- [ ] Create `.github/workflows/deploy-blog.yml`
- [ ] Create `scripts/generate-sitemap.ts` (runs as part of build)
- [ ] Add `VERCEL_TOKEN` / `NETLIFY_TOKEN` to GitHub secrets

---

## 13. Database Schema Reference

Location: `state/marketing_os.db`

### `workflows`

One row per marketing execution run.

| Column | Type | Description |
|---|---|---|
| `id` | TEXT PK | UUID |
| `type` | TEXT | `blog_post` \| `landing_page` \| `seasonal_campaign` |
| `topic` | TEXT | Article topic or campaign name |
| `target_keyword` | TEXT | Primary SEO keyword |
| `city` | TEXT | Target city (default: Santiago) |
| `status` | TEXT | `running` \| `completed` \| `failed` |
| `started_at` | DATETIME | |
| `finished_at` | DATETIME | |

### `steps`

One row per AI call inside a workflow.

| Column | Type | Description |
|---|---|---|
| `id` | TEXT PK | UUID |
| `workflow_id` | TEXT FK | → workflows.id |
| `step_name` | TEXT | `keyword_research`, `outline_generation`, etc. |
| `agent_name` | TEXT | Marketing agent used |
| `status` | TEXT | `completed` \| `failed` |
| `duration_ms` | INTEGER | Wall-clock time of the API call |
| `token_input` | INTEGER | Input tokens used |
| `token_output` | INTEGER | Output tokens used |
| `cost_usd` | REAL | Estimated USD cost |
| `created_at` | DATETIME | |

### `content_outputs`

Generated content, persisted forever.

| Column | Type | Description |
|---|---|---|
| `id` | TEXT PK | UUID |
| `workflow_id` | TEXT FK | → workflows.id |
| `content_type` | TEXT | `blog` \| `landing` \| `campaign` \| `ad_copy` |
| `title` | TEXT | SEO title of the content |
| `meta_description` | TEXT | SEO meta description |
| `content` | TEXT | Full Markdown body |
| `word_count` | INTEGER | |
| `created_at` | DATETIME | |

### `evaluations`

AI-generated quality scores.

| Column | Type | Description |
|---|---|---|
| `id` | TEXT PK | UUID |
| `workflow_id` | TEXT FK | → workflows.id |
| `seo_score` | INTEGER | 0–100 |
| `readability_score` | INTEGER | 0–100 |
| `conversion_score` | INTEGER | 0–100 |
| `local_relevance_score` | INTEGER | 0–100 |
| `overall_score` | REAL | Weighted average (0–100) |
| `notes` | TEXT | AI observations |
| `created_at` | DATETIME | |

### `performance_metrics`

Real-world analytics (manual import or API — Phase 8).

| Column | Type | Description |
|---|---|---|
| `id` | TEXT PK | UUID |
| `workflow_id` | TEXT FK | → workflows.id |
| `page_views` | INTEGER | From GA4 |
| `avg_time_on_page` | REAL | Seconds, from GA4 |
| `bounce_rate` | REAL | From GA4 |
| `conversions` | INTEGER | Bookings, clicks |
| `revenue_generated` | REAL | In CLP |
| `recorded_at` | DATETIME | |

---

## 14. Agent Reference

All 23 agents are available in `agents/*/SKILL.md`. Each has a defined role, default output type, and is tuned for WashDog's context.

| Agent | Role | Output | Frequency |
|---|---|---|---|
| `copywriting` | contenido | doc | Weekly |
| `social-content` | contenido | doc | Weekly |
| `email-sequence` | contenido | doc | Weekly |
| `analytics-tracking` | analitica | sheet | Weekly |
| `paid-ads` | ads | sheet | Weekly |
| `seo-audit` | seo | sheet | Biweekly |
| `page-cro` | cro | doc | Biweekly |
| `form-cro` | cro | doc | Biweekly |
| `popup-cro` | cro | doc | Biweekly |
| `schema-markup` | seo | doc | Biweekly |
| `ab-test-setup` | cro | doc | Biweekly |
| `marketing-ideas` | estrategia | doc | Monthly |
| `launch-strategy` | estrategia | doc | Monthly |
| `onboarding-cro` | cro | doc | On-demand |
| `paywall-upgrade-cro` | cro | doc | On-demand |
| `referral-program` | growth | doc | On-demand |
| `competitor-alternatives` | estrategia | sheet | Monthly |
| `pricing-strategy` | estrategia | doc | Monthly |
| `free-tool-strategy` | growth | doc | On-demand |
| `marketing-psychology` | estrategia | doc | On-demand |
| `signup-flow-cro` | cro | doc | On-demand |
| `copy-editing` | contenido | doc | On-demand |
| `programmatic-seo` | seo | doc | On-demand |

---

## 15. Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Required for Google Workspace sync
GOOGLE_OAUTH_CREDENTIALS=workspace/credentials.json

# Optional — legacy service account (most users don't need this)
# GOOGLE_APPLICATION_CREDENTIALS=workspace/service_account.json
```

Variables are loaded from `.env` automatically via `python-dotenv`.

---

## 16. Cost Reference

### Model pricing (per 1M tokens)

| Model | Input | Output | Typical use |
|---|---|---|---|
| `claude-opus-4-6` | $15.00 | $75.00 | Critical agents (copywriting, ads) |
| `claude-sonnet-4-6` | $3.00 | $15.00 | Important agents (CRO, SEO audit) |
| `claude-haiku-4-5` | $0.25 | $1.25 | Support agents, evaluations |

### Typical workflow costs

| Workflow | Steps | Model | Est. cost |
|---|---|---|---|
| Blog SEO post | 3 + eval | sonnet + haiku | ~$0.04 |
| Landing page | 2 + eval | sonnet + haiku | ~$0.03 |
| Seasonal campaign | 3 + eval | sonnet + haiku | ~$0.05 |
| Full week (scheduled) | ~12 agents | mixed | ~$0.85 |
| Full month | ~50 agents | mixed | ~$3.60 |

**Monthly budget:** $20 USD · **Typical spend:** ~$3.60 USD · **Margin:** ~$16.40 USD

---

---

## Phase 2 — Programmatic Local SEO Expansion

Generates landing pages at scale: **6 services × 28 communes = 168 pages** targeting local keywords like `peluquería canina Providencia`, `baño perros Vitacura`, etc.

### New Files

| File | Purpose |
|---|---|
| `keywords/communes.csv` | 28 Santiago communes (slug + display name) |
| `keywords/services.csv` | 6 WashDog services (slug + display name) |
| `page_registry.py` | CRUD helpers for the `pages` DB table |
| `generate_local_pages.py` | Populates the registry with all combinations |
| `run_pending_pages.py` | Runs workflows for pending pages, N per batch |

### Database Table: `pages`

Tracks every service × commune combination and prevents duplicate generation.

| Column | Description |
|---|---|
| `page_id` | `{service_slug}__{commune_slug}` — deterministic primary key |
| `status` | `pending` → `generated` → `published` / `failed` |
| `workflow_id` | Links to the `workflows` table after generation |

### Quick Start

```bash
# 1. Register all 168 combinations (run once)
cd marketing_os
.venv/bin/python generate_local_pages.py --init

# Preview without writing
.venv/bin/python generate_local_pages.py --init --dry-run

# 2. Check the registry
.venv/bin/python generate_local_pages.py --status
.venv/bin/python generate_local_pages.py --list

# 3. Generate first batch (10 pages)
.venv/bin/python run_pending_pages.py --batch 10

# Safe test with a single page
.venv/bin/python run_pending_pages.py --batch 1

# 4. Sync to Google Sheets
.venv/bin/python sync_sheets.py --all --best-only
```

### Cron Schedule

```
# Daily: generate 10 new pages — 06:00
0 6 * * *  .venv/bin/python run_pending_pages.py --batch 10

# Daily: sync to Sheets — 06:30
30 6 * * * .venv/bin/python sync_sheets.py --all --best-only

# Weekly: analytics import — Mondays 07:00
0 7 * * 1  .venv/bin/python sync_analytics.py --days 7
```

At 10 pages/day the full 168-page corpus is generated in **~17 days**.

### Generated URL Pattern

```
/servicios/{service-slug}-{commune-slug}

Examples:
  /servicios/peluqueria-canina-providencia
  /servicios/bano-perros-vitacura
  /servicios/spa-canino-las-condes
```

---

*Built on the [Marketing Skills](../README.md) library.*
