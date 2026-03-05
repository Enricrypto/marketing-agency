# WashDog Marketing System Architecture

## Overview

The WashDog marketing system consists of two independent repositories:

1. **WashDog Website** (Next.js) — public-facing rendering layer
2. **Marketing Agency OS** (Python + AI) — intelligence and automation brain

The goal is a **self-improving marketing system** that:

- Generates SEO content from keyword research
- Monitors analytics and ranking performance
- Detects new marketing opportunities automatically
- Publishes content to the website with zero manual formatting

---

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│              Marketing Agency OS (brain)            │
│                                                     │
│  • SEO strategy & keyword research                  │
│  • Blog + landing page content generation           │
│  • Analytics ingestion & interpretation             │
│  • Competitor monitoring                            │
│  • Social media content creation                    │
│  • Evaluation & quality scoring                     │
│                                                     │
│  Stack: Python · Claude API · Marketing Skills      │
│         SQLite · Google APIs                        │
└────────────────────┬────────────────────────────────┘
                     │  writes Markdown + commits to repo
                     ▼
┌─────────────────────────────────────────────────────┐
│              WashDog Website (renderer)             │
│                                                     │
│  • Service pages (peluquería, baño, antipulgas...)  │
│  • Blog rendering (SSG from Markdown)               │
│  • Booking interface / reservation capture          │
│  • Schema markup (LocalBusiness, Service, FAQ)      │
│  • Dynamic SEO metadata per page                    │
│                                                     │
│  Stack: Next.js · React · Tailwind                  │
│         Static Markdown blog                        │
└────────────────────┬────────────────────────────────┘
                     │  events, conversions, rankings
                     ▼
┌─────────────────────────────────────────────────────┐
│              Google Ecosystem (measurement)         │
│                                                     │
│  • Google Analytics 4    — traffic, conversions     │
│  • Search Console        — impressions, clicks,     │
│                            keyword rankings          │
│  • Google Business       — local SEO, reviews,      │
│    Profile                 Q&A, posts               │
│  • Google Workspace      — Docs, Sheets, Drive      │
│                            for drafts + data         │
└─────────────────────────────────────────────────────┘
```

Data flows **both ways**: Marketing OS writes content to the website, and reads performance data back from Google to improve future content.

---

## Repository Responsibilities

### WashDog Website

**Purpose:** Public-facing marketing website — the customer touchpoint.

**Responsibilities:**
- Render service pages (`/peluqueria-canina-nunoa`, `/bano-perros-nunoa`, etc.)
- Build blog posts from Markdown files via Next.js SSG (`/blog/[slug]`)
- Implement schema markup (LocalBusiness, Service, FAQ, BreadcrumbList)
- Capture booking intent (WhatsApp link, contact form)
- Serve dynamic SEO metadata (title, meta description, OG tags) per page
- Maintain sitemap.xml (auto-generated on build)

**Technologies:** Next.js · React · gray-matter · react-markdown · Tailwind

**Important rule:**
> The website **never generates content**. It only renders what Marketing OS provides. All copy, keywords, meta descriptions, and blog articles originate in Marketing OS and arrive as Markdown files or data.

---

### Marketing Agency OS

**Purpose:** Marketing intelligence engine — runs autonomously on a schedule.

**Responsibilities:**
- Define and execute SEO keyword strategy (see `docs/SEO_CONTENT_PLAN.md`)
- Generate blog articles, landing page copy, and social content via Claude
- Ingest GA4 + Search Console data into SQLite (`performance_metrics` table)
- Monitor competitor rankings and identify content gaps
- Score all generated content automatically (SEO, conversion, local relevance)
- Commit finalized Markdown files to the WashDog website repo
- Trigger deploys via GitHub Actions on commit

**Technologies:** Python · Claude API (opus/sonnet/haiku) · SQLite · Google APIs · Marketing Skills library

**Key files:**
```
marketing_os/
├── run_workflow.py      ← CLI entry point for all workflows
├── scheduler.py         ← Weekly automation with budget control
├── runner.py            ← On-demand agent runner
├── db.py                ← SQLite layer
├── workflows/           ← Blog SEO, Landing Page, Campaign pipelines
├── evaluations/         ← Automatic quality scoring
└── analytics/           ← Dashboard queries
```

---

## Blog System

Blog posts live in the **website repository**, not in Marketing OS.

**Location in website repo:**
```
washdog-website/
└── content/
    └── blog/
        ├── 2026-03-01-como-banar-tu-perro.md
        ├── 2026-03-08-corte-yorkshire-nunoa.md
        └── 2026-03-15-peluqueria-gatos-nunoa.md
```

**File format:** Markdown with YAML frontmatter

```yaml
---
title: "Cómo bañar a tu perro en casa — Guía WashDog"
date: "2026-03-01"
slug: "como-banar-perro-casa"
author: "WashDog Team"
keywords: ["bañar perro en casa", "peluquería canina", "Ñuñoa"]
meta_description: "Aprende paso a paso cómo bañar a tu perro en casa. Consejos de los groomers de WashDog en Ñuñoa."
workflow_id: "abc12345"
google_doc_url: "https://docs.google.com/document/d/.../edit"
seo_score: 84
overall_score: 81.2
---

# Cómo bañar a tu perro en casa
...
```

**Next.js automatically builds** a page for each `.md` file at `/blog/[slug]`.

---

## Content Publishing Pipeline

```
1. SEO opportunity detected
   (keyword research or Search Console gap)
          │
          ▼
2. Marketing OS generates article
   python run_workflow.py blog \
     --topic "cómo bañar a tu perro" \
     --keyword "bañar perro en casa"
          │
          ▼
3. Markdown file created
   content/blog/2026-03-01-como-banar-perro.md
   (includes frontmatter: title, slug, keywords,
    seo_score, workflow_id, google_doc_url)
          │
          ▼
4. QA gate (Phase 9)
   overall_score >= 70, seo_score >= 65,
   word_count >= 700 → passes automatically
   → fails → flagged for human review
          │
          ▼
5. File committed to website repo
   branch: marketing-os/blog
   commit stored in content_outputs.commit_hash
          │
          ▼
6. GitHub Actions triggered
   → Next.js build
   → sitemap.xml regenerated
   → Vercel/Netlify deploy
          │
          ▼
7. Article live at washdog.cl/blog/[slug]
          │
          ▼
8. Analytics collected (Phase 8)
   GA4 + Search Console → performance_metrics table
   → informs next content cycle
```

---

## Design Principles

**1. Separation of concerns**
The website renders; Marketing OS thinks. Never mix them.

**2. Everything is measurable**
Every piece of content has a `workflow_id` traceable to tokens spent, scores achieved, and eventually — real traffic and bookings.

**3. Drafts first, publish second**
All outputs are drafts in Google Docs before any commit. Human review happens on Sundays (see `context/weekly_plan.md`).

**4. Budget-aware execution**
The scheduler never exceeds $20/month. Dynamic model downgrade protects the budget automatically.

**5. Local-first SEO**
Every prompt, every evaluation criterion, every keyword target is oriented to Santiago, Chile — specifically Ñuñoa and surrounding comunas.
