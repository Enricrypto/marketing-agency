"""
Newsletter Engine — Resend Sender

Gestiona el envío autónomo de la newsletter semanal:
  - get_subscribers()   → lista contactos activos desde Resend Audiences
  - render_html()       → renderiza el borrador Markdown como HTML con Jinja2
  - send_issue()        → envía la edición a todos los suscriptores, registra en SQLite
  - generate_unsubscribe_token() / verify_unsubscribe_token() → HMAC firmado
"""

import hashlib
import hmac
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import resend
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader

# Load .env — searches from marketing_os/ upward
load_dotenv(Path(__file__).parent.parent / ".env")

resend.api_key = os.environ["RESEND_API_KEY"]

_AUDIENCE_ID      = os.environ.get("RESEND_AUDIENCE_ID", "")
_SECRET           = os.environ.get("NEWSLETTER_SECRET", "changeme").encode()
_FROM_ADDRESS     = os.environ.get("NEWSLETTER_FROM", "Santiago a Cuatro Patas <newsletter@washdog.cl>")
_UNSUBSCRIBE_BASE = os.environ.get("SITE_URL", "https://www.washdog.cl")

_TEMPLATE_DIR = Path(__file__).parent


# ── Token helpers ─────────────────────────────────────────────────────────────

def generate_unsubscribe_token(email: str) -> str:
    """Returns a time-stamped HMAC token for unsubscribe links."""
    ts  = str(int(time.time()))
    sig = hmac.new(_SECRET, f"{email}:{ts}".encode(), hashlib.sha256).hexdigest()
    return f"{ts}.{sig}"


def verify_unsubscribe_token(email: str, token: str, max_age_days: int = 365) -> bool:
    """Validates an unsubscribe token. Returns True if valid and not expired."""
    try:
        ts_str, sig = token.split(".", 1)
        ts = int(ts_str)
    except (ValueError, TypeError):
        return False

    age = time.time() - ts
    if age > max_age_days * 86400:
        return False

    expected = hmac.new(_SECRET, f"{email}:{ts_str}".encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected)


# ── Subscriber management ─────────────────────────────────────────────────────

def get_subscribers() -> list[dict]:
    """
    Returns list of active subscribers from Resend Audiences.
    Each dict has: id, email, first_name (may be empty).
    """
    if not _AUDIENCE_ID:
        raise ValueError("RESEND_AUDIENCE_ID not set in environment")

    contacts = resend.Contacts.list(audience_id=_AUDIENCE_ID)
    return [
        {
            "id":         c["id"],
            "email":      c["email"],
            "first_name": c.get("first_name") or "",
        }
        for c in contacts.get("data", [])
        if not c.get("unsubscribed", False)
    ]


def add_subscriber(email: str, first_name: str = "") -> dict:
    """Adds a contact to Resend Audiences. Idempotent (upsert)."""
    if not _AUDIENCE_ID:
        raise ValueError("RESEND_AUDIENCE_ID not set in environment")

    return resend.Contacts.create(
        audience_id=_AUDIENCE_ID,
        params={
            "email":      email,
            "first_name": first_name,
            "unsubscribed": False,
        },
    )


def remove_subscriber(email: str) -> None:
    """Marks a contact as unsubscribed in Resend Audiences."""
    if not _AUDIENCE_ID:
        raise ValueError("RESEND_AUDIENCE_ID not set in environment")

    contacts = resend.Contacts.list(audience_id=_AUDIENCE_ID)
    for c in contacts.get("data", []):
        if c["email"].lower() == email.lower():
            resend.Contacts.update(
                audience_id=_AUDIENCE_ID,
                id=c["id"],
                params={"unsubscribed": True},
            )
            return


# ── HTML rendering ────────────────────────────────────────────────────────────

def render_html(
    body_markdown: str,
    subject_line: str,
    issue_number: int,
    subscriber_email: str,
) -> str:
    """
    Renders the newsletter body (Markdown) into full HTML using the Jinja2 template.
    Injects a personalized unsubscribe link.
    """
    try:
        import markdown as md_lib
        html_body = md_lib.markdown(body_markdown, extensions=["nl2br", "tables"])
    except ImportError:
        # Fallback: wrap paragraphs manually without markdown library
        paragraphs = body_markdown.split("\n\n")
        html_body = "\n".join(f"<p>{p.replace(chr(10), '<br>')}</p>" for p in paragraphs)

    token = generate_unsubscribe_token(subscriber_email)
    import urllib.parse
    unsubscribe_url = (
        f"{_UNSUBSCRIBE_BASE}/api/newsletter-unsubscribe"
        f"?email={urllib.parse.quote(subscriber_email)}&token={token}"
    )

    env = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)))
    template = env.get_template("template.html")
    return template.render(
        subject_line    = subject_line,
        issue_number    = issue_number,
        html_body       = html_body,
        unsubscribe_url = unsubscribe_url,
    )


# ── Send ──────────────────────────────────────────────────────────────────────

def send_issue(
    issue_number:  int,
    subject_line:  str,
    preview_text:  str,
    body_markdown: str,
    workflow_id:   Optional[str] = None,
    dry_run:       bool = False,
) -> dict:
    """
    Sends the newsletter to all active subscribers.
    Records the issue in newsletter_issues table.
    Returns { issue_id, recipient_count, status }.
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from db import db, init_db

    init_db()

    issue_id    = str(uuid.uuid4())
    created_at  = datetime.utcnow().isoformat()
    subscribers = get_subscribers()

    if dry_run:
        print(f"[newsletter] DRY RUN — would send to {len(subscribers)} subscribers")
        return {"issue_id": issue_id, "recipient_count": len(subscribers), "status": "dry_run"}

    sent = 0
    failed = 0

    for sub in subscribers:
        try:
            html = render_html(
                body_markdown    = body_markdown,
                subject_line     = subject_line,
                issue_number     = issue_number,
                subscriber_email = sub["email"],
            )
            resend.Emails.send({
                "from":    _FROM_ADDRESS,
                "to":      [sub["email"]],
                "subject": subject_line,
                "html":    html,
                "headers": {
                    "X-Entity-Ref-ID": f"newsletter-{issue_number}-{sub['id']}",
                    "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
                },
            })
            sent += 1
            time.sleep(0.6)  # stay under Resend's 2 req/sec limit
        except Exception as exc:
            print(f"[newsletter] Failed to send to {sub['email']}: {exc}")
            failed += 1

    status = "sent" if failed == 0 else ("partial" if sent > 0 else "failed")

    with db() as conn:
        conn.execute(
            """INSERT INTO newsletter_issues
               (id, issue_number, focus_commune, subject_line, preview_text,
                status, recipient_count, workflow_id, sent_at, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(issue_number) DO UPDATE SET
                 status=excluded.status,
                 recipient_count=excluded.recipient_count,
                 sent_at=excluded.sent_at""",
            (
                issue_id, issue_number, "", subject_line, preview_text,
                status, sent, workflow_id,
                datetime.utcnow().isoformat(), created_at,
            ),
        )

    print(f"[newsletter] Issue #{issue_number} — sent={sent} failed={failed} status={status}")
    return {"issue_id": issue_id, "recipient_count": sent, "status": status}


def get_next_issue_number() -> int:
    """Returns the next issue number based on newsletter_issues table."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from db import fetch_all, init_db
    init_db()
    rows = fetch_all("SELECT MAX(issue_number) as max_n FROM newsletter_issues")
    max_n = rows[0]["max_n"] if rows and rows[0]["max_n"] is not None else 0
    return max_n + 1
