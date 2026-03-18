"""
Newsletter Engine — Instagram Auto-Post

Publica un teaser de la edición semanal en Instagram Business
usando la Meta Graph API.

Requiere en .env:
    INSTAGRAM_BUSINESS_ACCOUNT_ID  — ID de tu cuenta de negocio IG
    INSTAGRAM_ACCESS_TOKEN         — Token de acceso de larga duración (Page token)

Cómo obtener el token:
    1. Meta Business Suite → Configuración → Cuentas de Instagram
    2. O via Meta for Developers → Graph API Explorer
       Permisos requeridos: instagram_basic, instagram_content_publish, pages_read_engagement
"""

import os
import textwrap
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

_IG_ACCOUNT_ID   = os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")
_IG_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
_GRAPH_API       = "https://graph.facebook.com/v19.0"


def _is_configured() -> bool:
    return bool(_IG_ACCOUNT_ID and _IG_ACCESS_TOKEN)


def build_caption(
    issue_number:  int,
    subject_line:  str,
    focus_commune: str,
    sections:      dict,
) -> str:
    """Builds the Instagram post caption from newsletter sections."""
    lugar  = sections.get("lugar", {})
    tip    = sections.get("tip", {})
    evento = sections.get("evento", {})

    lines = [
        f"🐾 Santiago a Cuatro Patas — Edición #{issue_number}",
        "",
        f"📍 {lugar.get('nombre', focus_commune)}",
        lugar.get("por_que", ""),
        "",
    ]

    if evento.get("nombre"):
        lines += [f"🗓️ {evento['nombre']} — {evento.get('cuando', '')}"]
        lines += [""]

    if tip.get("titulo"):
        lines += [f"💡 {tip['titulo']}"]
        lines += [""]

    lines += [
        "Suscríbete gratis en washdog.cl 👇",
        "#SantiagoCuatroPatas #PerrosSantiago #DogFriendlySantiago",
        f"#{focus_commune.replace(' ', '')} #PeluqueriaCanina #WashDog",
    ]

    caption = "\n".join(lines)
    # Instagram caption limit: 2200 chars
    return caption[:2200]


def post_to_instagram(
    image_url:     str,
    caption:       str,
) -> dict:
    """
    Posts an image + caption to Instagram Business via Meta Graph API.

    Args:
        image_url: Publicly accessible image URL (must be HTTPS)
        caption:   Post caption text

    Returns:
        dict with post_id on success, or error details
    """
    if not _is_configured():
        print("[instagram] Skipping — INSTAGRAM_BUSINESS_ACCOUNT_ID or INSTAGRAM_ACCESS_TOKEN not set")
        return {"skipped": True}

    # Step 1: Create media container
    container_res = requests.post(
        f"{_GRAPH_API}/{_IG_ACCOUNT_ID}/media",
        params={
            "image_url":    image_url,
            "caption":      caption,
            "access_token": _IG_ACCESS_TOKEN,
        },
        timeout=30,
    )
    container_data = container_res.json()

    if "error" in container_data:
        print(f"[instagram] Container error: {container_data['error']}")
        return {"error": container_data["error"]}

    container_id = container_data["id"]

    # Step 2: Publish container
    publish_res = requests.post(
        f"{_GRAPH_API}/{_IG_ACCOUNT_ID}/media_publish",
        params={
            "creation_id":  container_id,
            "access_token": _IG_ACCESS_TOKEN,
        },
        timeout=30,
    )
    publish_data = publish_res.json()

    if "error" in publish_data:
        print(f"[instagram] Publish error: {publish_data['error']}")
        return {"error": publish_data["error"]}

    post_id = publish_data.get("id", "")
    print(f"[instagram] ✓ Posted — post_id={post_id}")
    return {"post_id": post_id}


def post_text_only(caption: str) -> dict:
    """
    Posts a caption-only post using a default WashDog image stored in the CDN.
    Falls back gracefully if no image URL is configured.
    """
    default_image = os.environ.get(
        "INSTAGRAM_DEFAULT_IMAGE_URL",
        "https://www.washdog.cl/og-image.jpg",  # use your existing OG image
    )
    return post_to_instagram(image_url=default_image, caption=caption)
