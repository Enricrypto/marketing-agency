# WashDog Marketing Workflows

Automated workflows executed by the Marketing Agency OS for WashDog.
Each workflow has a defined trigger, step sequence, output, and cost estimate.

---

## Workflow Index

| # | Workflow | Trigger | Output | Est. Cost |
|---|---|---|---|---|
| 1 | SEO Growth Cycle | Weekly (Monday) | Markdown file → website repo | ~$0.05 |
| 2 | Blog Content Generator | On-demand / scheduled | `/content/blog/*.md` | ~$0.04 |
| 3 | SEO Monitoring | Weekly (Monday) | Google Sheets dashboard | ~$0.03 |
| 4 | Landing Page Optimization | Biweekly (Thursday) | Google Doc with recommendations | ~$0.03 |
| 5 | Social Media Generation | Weekly (Wednesday) | Google Doc with all channel copy | ~$0.05 |

---

## Workflow 1 — SEO Growth Cycle

**Goal:** Continuously publish SEO-optimized blog content based on real keyword opportunities.

**Trigger:** Weekly, every Monday (part of `scheduler.py` run)

**Script:** `scripts/run_growth_cycle.py` *(Phase 8 — planned)*

**Steps:**

```
1. Pull Search Console data
   analytics/import_search_console.py
   → fetch impressions, clicks, avg_position for all pages

2. Identify low-competition keyword opportunities
   → queries: position 8–20 (near page 1), low clicks vs high impressions
   → cross-reference with docs/SEO_CONTENT_PLAN.md topics

3. Select next topic from SEO_CONTENT_PLAN.md
   → priority queue: Core Service Pages first, then Blog Topics

4. Run Blog Content Generator workflow (Workflow 2)
   python run_workflow.py blog \
     --topic "<selected topic>" \
     --keyword "<target keyword>" \
     --city "Ñuñoa"

5. QA gate
   evaluations/scorer.py → overall_score >= 70

6. Convert to Markdown + frontmatter
   workflows/base.py → save_as_markdown()
   → writes to washdog-website/content/blog/YYYY-MM-DD-slug.md

7. Commit to website repo
   branch: marketing-os/blog
   commit_hash stored in content_outputs table

8. Trigger deployment
   GitHub Actions → Next.js build → Vercel deploy
```

**Output:** Live blog post at `washdog.cl/blog/[slug]`

**Agents used:** `seo-audit`, `copywriting`, `analytics-tracking`

---

## Workflow 2 — Blog Content Generator

**Goal:** Generate a complete, SEO-optimized blog article for WashDog from a topic + keyword pair.

**Trigger:** On-demand or as Step 4 of the SEO Growth Cycle.

**CLI:**
```bash
python run_workflow.py blog \
  --topic "cómo bañar a tu perro en casa" \
  --keyword "bañar perro en casa" \
  --city "Ñuñoa" \
  --model claude-sonnet-4-6
```

**From Python:**
```python
from workflows.blog_seo import run_blog_seo

result = run_blog_seo(
    topic          = "cómo bañar a tu perro en casa",
    target_keyword = "bañar perro en casa",
    city           = "Ñuñoa",
)
print(result["content"])      # full Markdown article
print(result["scores"])       # SEO, conversion, local relevance scores
```

**Pipeline:**

```
Input: topic + keyword + city
          │
          ▼
Step 1: keyword_research          [agent: seo-audit]
  → 10 long-tail keywords for Chile
  → Focus: Ñuñoa, Providencia, Las Condes

          │
          ▼
Step 2: outline_generation        [agent: copywriting]
  → title (SEO-optimized, 60 chars)
  → meta description (155 chars)
  → H2/H3 heading structure
  → Output: JSON

          │
          ▼
Step 3: article_writing           [agent: copywriting]
  → 900–1,200 words
  → Markdown with headings, lists, CTA
  → Keyword in H1, first paragraph, 2–3x in body
  → Mentions Ñuñoa + surrounding comunas
  → Internal link suggestions

          │
          ▼
Step 4: seo_evaluation            [model: haiku — low cost]
  → SEO score (keyword density, heading structure)
  → Readability score (tone, paragraph length)
  → Conversion score (CTA clarity)
  → Local relevance score (Chile mentions, CLP)
  → overall_score = weighted average

          │
          ▼
Output:
  • content_outputs table (SQLite)
  • evaluations table (SQLite)
  • outputs/docs/ (local file)
  • Google Docs (if workspace/ configured)
```

**Database trace:** Every run creates records in `workflows`, `steps`, `content_outputs`, and `evaluations`.

---

## Workflow 3 — SEO Monitoring

**Goal:** Track keyword rankings, traffic, and identify pages needing improvement.

**Trigger:** Weekly, every Monday (before content generation).

**CLI:**
```bash
python runner.py --agent analytics-tracking \
  --task "Reporte semanal SEO: keywords, posiciones, tráfico blog WashDog"
```

**Pipeline:**

```
1. Fetch Search Console data           [Phase 8 — planned]
   analytics/import_search_console.py
   → keywords: impressions, clicks, avg_position, CTR

2. Fetch GA4 data                       [Phase 8 — planned]
   analytics/import_ga4.py
   → page_views, avg_time_on_page, bounce_rate, conversions

3. Store in performance_metrics table

4. Generate monitoring report           [agent: analytics-tracking]
   → Top 10 keywords by impressions
   → Pages with declining CTR (opportunity)
   → New keywords entering top 20 (quick wins)
   → Blog posts with high bounce (content issue)

5. Save to Google Sheets
   MarketingOS/sheets/SEO-Monitor-YYYY-WW
```

**Key metrics tracked:**

| Metric | Source | Target |
|---|---|---|
| Ranking for "peluquería canina ñuñoa" | Search Console | Top 3 |
| Ranking for "baño perros ñuñoa" | Search Console | Top 3 |
| Monthly blog organic traffic | GA4 | +20% MoM |
| Avg. page position for blog posts | Search Console | < 15 |
| WhatsApp click-through rate | GA4 (event) | > 3% |

**Output:** Google Sheets dashboard + alert if key keyword drops below position 5.

---

## Workflow 4 — Landing Page Optimization

**Goal:** Generate CRO recommendations and updated copy for WashDog's service landing pages.

**Trigger:** Biweekly, every Thursday (alternating weeks).

**CLI:**
```bash
python run_workflow.py landing \
  --service "peluquería canina" \
  --location "Ñuñoa" \
  --promotion "primera visita $19.990 CLP"
```

**Pipeline:**

```
Input: service + location + current promotion
          │
          ▼
Step 1: market_positioning         [agent: page-cro]
  → Unique value proposition (1 sentence)
  → 3 customer objections + how to resolve each
  → Trust signals (experience, guarantees, reviews)
  → Emotional angle for Ñuñoa dog owners

          │
          ▼
Step 2: copy_generation            [agent: copywriting]
  → H1 + subheadline
  → Service details (benefit-focused bullets)
  → Why WashDog section
  → Social proof (2 testimonials)
  → Pricing table in CLP
  → CTA: "Reserva tu hora por WhatsApp"

          │
          ▼
Step 3: conversion_scoring         [model: haiku]
  → CTA visibility
  → Offer clarity
  → Trust signal coverage
  → Local relevance

          │
          ▼
Output:
  • Google Doc in MarketingOS/docs/
  • content_outputs table
  • evaluations table
```

**Skills used:** `page-cro`, `copywriting`, `marketing-psychology`

**Note:** Output is a **recommendation and draft** — the developer implements in the website repo.

---

## Workflow 5 — Social Media Generation

**Goal:** Generate a week's worth of social media content across all channels for WashDog.

**Trigger:** Weekly, every Wednesday.

**CLI:**
```bash
python run_workflow.py campaign \
  --name "Contenido Social Semana $(date +%Y-W%V)" \
  --season "$(python -c 'import datetime; m=datetime.date.today().month; print(\"verano\" if m in [12,1,2] else \"otoño\" if m in [3,4,5] else \"invierno\" if m in [6,7,8] else \"primavera\")')" \
  --offer ""
```

Or directly via runner:
```bash
python runner.py --agent social-content \
  --task "5 posts para Instagram de WashDog esta semana, temporada actual Santiago"
```

**Pipeline:**

```
Input: campaign theme + season + optional promotion
          │
          ▼
Step 1: campaign_angle             [agent: marketing-ideas]
  → Creative concept for the week
  → Emotional hook for Santiago dog owners
  → 3 content angles (educational / promotional / community)

          │
          ▼
Step 2: multichannel_copy          [agent: social-content]
  → Instagram feed post (150–200 words + hashtags)
  → Instagram Stories text (60 words + CTA)
  → WhatsApp Business broadcast message
  → Google Business Profile post
  → 3 Google Ads headlines + 2 descriptions
  → Email subject + preview text

          │
          ▼
Step 3: roi_projection             [agent: analytics-tracking]
  → 3-scenario ROI estimate (conservative / realistic / optimistic)
  → Projected bookings and CLP revenue
  → Recommended budget for paid promotion

          │
          ▼
Output:
  • Google Doc: MarketingOS/docs/social-YYYY-WW
  • content_outputs table
  • evaluations table
```

**Output format** (copy_assets JSON):
```json
{
  "instagram_post": "...",
  "instagram_story": "...",
  "whatsapp_broadcast": "...",
  "google_business_post": "...",
  "google_ads_headline_1": "...",
  "google_ads_headline_2": "...",
  "google_ads_headline_3": "...",
  "google_ads_description_1": "...",
  "google_ads_description_2": "...",
  "email_subject": "...",
  "email_preview_text": "..."
}
```

---

## Running Workflows

### From CLI

```bash
cd marketing_os/
source .venv/bin/activate

# Individual workflows
python run_workflow.py blog --topic "..." --keyword "..."
python run_workflow.py landing --service "..." --location "..."
python run_workflow.py campaign --name "..." --season "..."

# Weekly scheduler (all workflows)
python scheduler.py --run-week

# Analytics report
python run_workflow.py report
```

### From Python (import)

```python
from workflows.blog_seo        import run_blog_seo
from workflows.landing_page    import run_landing_page
from workflows.seasonal_campaign import run_seasonal_campaign

# All return: { workflow_id, title, content, scores, ... }
```

### Checking what ran

```python
from analytics.queries import cost_per_workflow, print_report
print_report("Workflows esta semana", cost_per_workflow())
```

---

## Workflow Output Reference

All workflows store data in SQLite and optionally sync to Google Workspace:

| Table | What's stored |
|---|---|
| `workflows` | Run metadata: type, topic, keyword, city, status, timing |
| `steps` | Each AI call: name, tokens, cost, duration, status |
| `content_outputs` | Full generated text, title, meta, word count |
| `evaluations` | SEO/readability/conversion/local scores per output |
| `performance_metrics` | Real GA4 + Search Console data (Phase 8) |
