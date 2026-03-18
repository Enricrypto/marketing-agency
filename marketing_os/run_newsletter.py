#!/usr/bin/env python3
"""
Marketing OS — Newsletter Runner
Genera y envía la newsletter semanal "Santiago a Cuatro Patas".

Uso:
    .venv/bin/python run_newsletter.py               # genera y envía
    .venv/bin/python run_newsletter.py --dry-run     # genera, no envía
    .venv/bin/python run_newsletter.py --issue 5     # fuerza número de edición
    .venv/bin/python run_newsletter.py --commune "Las Condes"
    .venv/bin/python run_newsletter.py --draft-only  # genera borrador y lo guarda, no envía
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from db import init_db
from newsletter.send import get_next_issue_number, send_issue
from newsletter.instagram import build_caption, post_text_only
from workflows.newsletter import run_newsletter

# ── Comunas en rotación semanal ───────────────────────────────────────────────
_COMMUNES = [
    "Ñuñoa",
    "Providencia",
    "Las Condes",
    "Vitacura",
    "Santiago Centro",
    "Macul",
    "La Reina",
    "Peñalolén",
    "San Miguel",
    "Miraflores",
]


def _commune_for_issue(issue_number: int) -> str:
    return _COMMUNES[(issue_number - 1) % len(_COMMUNES)]


_WEBSITE_CONTENT_DIR = Path(__file__).parent.parent.parent / "washdog-website" / "content" / "newsletter"


def _build_web_markdown(result: dict, issue_number: int, focus_commune: str, date_str: str) -> str:
    """Builds the SEO-ready markdown for the web archive page."""
    slug_title = result["subject_line"].replace('"', '').replace("'", "")
    return f"""---
issue_number: {issue_number}
title: "{slug_title}"
subject_line: "{result['subject_line']}"
description: "{result['preview_text']}"
date: "{date_str}"
commune: "{focus_commune}"
---

{result['body']}
"""


def _save_draft(result: dict, issue_number: int, focus_commune: str) -> tuple[Path, Path | None]:
    """Saves draft to outputs/ AND to washdog-website/content/newsletter/."""
    date_str = datetime.utcnow().strftime("%Y-%m-%d")

    # 1. Local outputs archive
    out_dir = Path(__file__).parent / "outputs" / "newsletters"
    out_dir.mkdir(parents=True, exist_ok=True)
    local_path = out_dir / f"newsletter-{date_str}-issue-{issue_number}.md"
    local_path.write_text(result["full_draft"], encoding="utf-8")

    # 2. Website content (for web archive)
    web_path = None
    if _WEBSITE_CONTENT_DIR.exists():
        _WEBSITE_CONTENT_DIR.mkdir(parents=True, exist_ok=True)
        web_path = _WEBSITE_CONTENT_DIR / f"issue-{issue_number}.md"
        web_path.write_text(
            _build_web_markdown(result, issue_number, focus_commune, date_str),
            encoding="utf-8",
        )
        print(f"[newsletter] Publicado en web: {web_path}")

    return local_path, web_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera y envía la newsletter semanal")
    parser.add_argument("--issue",       type=int,  default=None, help="Fuerza número de edición")
    parser.add_argument("--commune",     type=str,  default=None, help="Fuerza la comuna de foco")
    parser.add_argument("--dry-run",     action="store_true",     help="Genera pero no envía")
    parser.add_argument("--draft-only",  action="store_true",     help="Genera borrador y guarda, no envía")
    parser.add_argument("--no-instagram", action="store_true",   help="Skip Instagram post")
    parser.add_argument("--model",       type=str,  default="claude-sonnet-4-6")
    args = parser.parse_args()

    init_db()

    issue_number = args.issue or get_next_issue_number()
    focus_commune = args.commune or _commune_for_issue(issue_number)

    print(f"[newsletter] Generando edición #{issue_number} — foco: {focus_commune}")

    # ── Step 1: Generar contenido con Claude ─────────────────────────────────
    result = run_newsletter(
        issue_number  = issue_number,
        focus_commune = focus_commune,
        model         = args.model,
    )

    draft_path, web_path = _save_draft(result, issue_number, focus_commune)
    print(f"[newsletter] Borrador guardado: {draft_path}")
    print(f"[newsletter] Subject: {result['subject_line']}")
    print(f"[newsletter] Preview: {result['preview_text']}")

    if args.draft_only:
        print("[newsletter] --draft-only: terminando sin enviar.")
        return

    # ── Step 2: Enviar ───────────────────────────────────────────────────────
    send_result = send_issue(
        issue_number  = issue_number,
        subject_line  = result["subject_line"],
        preview_text  = result["preview_text"],
        body_markdown = result["body"],
        workflow_id   = result["workflow_id"],
        dry_run       = args.dry_run,
    )

    print(f"[newsletter] Resultado: {json.dumps(send_result, indent=2)}")

    # ── Step 3: Instagram post ───────────────────────────────────────────────
    if not args.no_instagram and not args.dry_run:
        caption = build_caption(
            issue_number  = issue_number,
            subject_line  = result["subject_line"],
            focus_commune = focus_commune,
            sections      = result["sections"],
        )
        ig_result = post_text_only(caption)
        print(f"[instagram] {json.dumps(ig_result)}")


if __name__ == "__main__":
    main()
