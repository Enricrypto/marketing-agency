"""
Marketing OS — Google Business Profile Post Generator
======================================================
Generates and publishes posts to Google Business Profile.

Sources:
  - Latest newsletter issue (auto-extract key tip)
  - Manual text via --text flag
  - Weekly content calendar (rotating 4-week cycle)

Usage:
  # Publish from last newsletter
  .venv/bin/python google_posts.py --from-newsletter

  # Publish from a specific newsletter issue
  .venv/bin/python google_posts.py --from-newsletter --issue 3

  # Publish custom text
  .venv/bin/python google_posts.py --text "Tip de la semana: ..."

  # Dry-run (generate + print, don't publish)
  .venv/bin/python google_posts.py --from-newsletter --dry-run

  # Discover and print your GBP location name (one-time setup)
  .venv/bin/python google_posts.py --discover
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic

# ── paths ──────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
DB_PATH    = BASE_DIR / "state" / "marketing_os.db"
LOGS_DIR   = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

SITE_URL   = os.environ.get("SITE_URL", "https://www.washdog.cl")
NEWSLETTER_URL = f"{SITE_URL}/newsletter"

# ── Claude client ──────────────────────────────────────────────────────────
_client: anthropic.Anthropic | None = None

def _ai() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


# ── Weekly content calendar (4-week rotating cycle) ───────────────────────
# Used as fallback when no newsletter content is available.

CONTENT_CALENDAR = [
    # Week 1 — Tip
    {
        "type":    "tip",
        "summary": (
            "🐾 Consejo de la semana: cepilla a tu perro al menos 2 veces por semana "
            "para evitar nudos y mantener su pelo sano. ¿Necesita un baño profesional? "
            "Agendamos sin costo adicional.\n\n"
            "📍 Av. Irarrázaval 2086-B, Ñuñoa\n"
            "☎️ Reserva en washdog.cl"
        ),
        "cta_type": "LEARN_MORE",
        "cta_url":  SITE_URL,
    },
    # Week 2 — Park
    {
        "type":    "park",
        "summary": (
            "🌿 Parque dog-friendly de la semana: Parque Inés de Suárez en Providencia. "
            "Tiene zona habilitada para perros, buen espacio para correr y fácil acceso.\n\n"
            "Cuéntanos: ¿dónde llevas a tu perro a pasear? 👇\n\n"
            "📍 WashDog — Ñuñoa · washdog.cl"
        ),
        "cta_type": "LEARN_MORE",
        "cta_url":  SITE_URL,
    },
    # Week 3 — Service
    {
        "type":    "service",
        "summary": (
            "✂️ ¿Sabías que el corte de pelo correcto depende de la raza de tu perro? "
            "En WashDog adaptamos el servicio a las necesidades específicas de cada uno.\n\n"
            "Peluquería canina profesional en Ñuñoa.\n"
            "Agenda tu hora → washdog.cl\n\n"
            "📍 Av. Irarrázaval 2086-B"
        ),
        "cta_type": "BOOK",
        "cta_url":  SITE_URL,
    },
    # Week 4 — Newsletter promo
    {
        "type":    "newsletter",
        "summary": (
            "📧 Cada semana enviamos 'Santiago a Cuatro Patas': tips de cuidado, "
            "parques dog-friendly y descuentos exclusivos para suscriptores.\n\n"
            "Es gratis. Solo para dueños de perros en Santiago. 🐶\n\n"
            f"Suscríbete → {NEWSLETTER_URL}"
        ),
        "cta_type": "LEARN_MORE",
        "cta_url":  NEWSLETTER_URL,
    },
]


# ── DB helpers ─────────────────────────────────────────────────────────────

def _get_latest_newsletter(issue: int | None = None) -> dict | None:
    """Fetch newsletter content from DB."""
    if not DB_PATH.exists():
        return None
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        if issue:
            row = conn.execute(
                "SELECT * FROM newsletters WHERE issue_number = ? ORDER BY created_at DESC LIMIT 1",
                (issue,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM newsletters ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        return dict(row) if row else None


def _log_post(post_type: str, text: str, gbp_result: dict | None, dry_run: bool) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS gbp_posts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at  TEXT NOT NULL,
                post_type   TEXT NOT NULL,
                text        TEXT NOT NULL,
                gbp_name    TEXT,
                dry_run     INTEGER DEFAULT 0
            )
        """)
        conn.execute(
            "INSERT INTO gbp_posts (created_at, post_type, text, gbp_name, dry_run) VALUES (?,?,?,?,?)",
            (
                datetime.now(timezone.utc).isoformat(),
                post_type,
                text,
                gbp_result.get("name") if gbp_result else None,
                int(dry_run),
            ),
        )
        conn.commit()


# ── AI content generation ──────────────────────────────────────────────────

def _generate_from_newsletter(newsletter: dict) -> dict:
    """
    Uses Claude to extract the best Google Business post from a newsletter issue.
    Returns {text, cta_type, cta_url}.
    """
    body   = newsletter.get("body", "")
    title  = newsletter.get("subject_line", "")
    issue  = newsletter.get("issue_number", "")

    prompt = f"""Eres el community manager de WashDog, peluquería canina en Ñuñoa, Santiago.

Tienes el contenido del newsletter semanal "Santiago a Cuatro Patas" (edición #{issue}).
Tu tarea es extraer el tip o dato más valioso y convertirlo en un post para Google Business Profile.

REGLAS:
- Máximo 400 caracteres (Google muestra solo las primeras líneas)
- Empieza con un emoji relevante
- Incluye una llamada a la acción corta al final
- Termina con "📍 WashDog · Ñuñoa · washdog.cl"
- Escribe en español natural, no corporativo
- NO uses hashtags (son para Instagram, no GBP)

NEWSLETTER:
Título: {title}
---
{body[:3000]}
---

Responde SOLO con el texto del post (sin explicaciones, sin comillas).
"""

    msg = _ai().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text.strip()

    return {
        "text":     text,
        "cta_type": "LEARN_MORE",
        "cta_url":  SITE_URL,
        "source":   f"newsletter-{issue}",
    }


def _get_weekly_calendar_post() -> dict:
    """Returns the post for the current week (0-indexed 4-week cycle)."""
    week_of_year = datetime.now().isocalendar()[1]
    slot = CONTENT_CALENDAR[week_of_year % 4]
    return {"text": slot["summary"], "cta_type": slot["cta_type"], "cta_url": slot["cta_url"], "source": "calendar"}


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Publish a post to Google Business Profile")
    parser.add_argument("--from-newsletter", action="store_true", help="Generate post from latest newsletter")
    parser.add_argument("--issue",           type=int,            help="Specific newsletter issue number")
    parser.add_argument("--text",            type=str,            help="Custom post text")
    parser.add_argument("--dry-run",         action="store_true", help="Print post without publishing")
    parser.add_argument("--discover",        action="store_true", help="Discover GBP location name and exit")
    args = parser.parse_args()

    # Load env
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR.parent / ".env")

    if args.discover:
        sys.path.insert(0, str(BASE_DIR))
        from workspace.api import gbp_get_location
        account, location = gbp_get_location()
        print(f"\nAdd to .env:\nGBP_ACCOUNT_NAME={account}\nGBP_LOCATION_NAME={location}\n")
        return

    # Resolve post content
    if args.text:
        post = {"text": args.text, "cta_type": "LEARN_MORE", "cta_url": SITE_URL, "source": "manual"}

    elif args.from_newsletter:
        newsletter = _get_latest_newsletter(args.issue)
        if newsletter:
            print(f"[GBP] Generando post desde newsletter #{newsletter.get('issue_number')}...")
            post = _generate_from_newsletter(newsletter)
        else:
            print("[GBP] No se encontró newsletter en la DB. Usando calendario.")
            post = _get_weekly_calendar_post()

    else:
        print("[GBP] Sin fuente especificada. Usando calendario semanal.")
        post = _get_weekly_calendar_post()

    # Print preview
    print("\n" + "─" * 60)
    print("📍 GOOGLE BUSINESS POST PREVIEW")
    print("─" * 60)
    print(post["text"])
    print(f"\nCTA: {post['cta_type']} → {post['cta_url']}")
    print(f"Fuente: {post['source']}")
    print(f"Caracteres: {len(post['text'])}")
    print("─" * 60 + "\n")

    if args.dry_run:
        print("[GBP] Dry-run — no publicado.")
        _log_post(post["source"], post["text"], None, dry_run=True)
        return

    # Publish
    sys.path.insert(0, str(BASE_DIR))
    from workspace.api import gbp_create_post
    result = gbp_create_post(
        text=post["text"],
        call_to_action_type=post["cta_type"],
        cta_url=post["cta_url"],
    )
    _log_post(post["source"], post["text"], result, dry_run=False)
    print(f"[GBP] ✅ Post publicado: {result.get('name', '')}")


if __name__ == "__main__":
    main()
