#!/usr/bin/env python3
"""
Marketing OS — Hub Page Generator (Phase 4)
WashDog Local SEO — Hub & Spoke Architecture.

Generates one SEO hub page per service in:
    washdog-website/content/servicios/[service-slug].md

Each hub page:
  - Targets "[service] Santiago" and related keywords
  - Links internally to all 28 commune landing pages (spokes)
  - Serves as the authority node for that service in the site hierarchy

Usage:
    python generate_hub_pages.py               # generate all 6 hub pages
    python generate_hub_pages.py --dry-run     # preview without writing
    python generate_hub_pages.py --service peluqueria-canina  # single service
    python generate_hub_pages.py --force       # overwrite existing files
"""

import argparse
import csv
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import anthropic

sys.path.insert(0, str(Path(__file__).parent))

# ── Paths ──────────────────────────────────────────────────────────────────────

_MOS_DIR    = Path(__file__).parent
_NEXTJS_DIR = Path("/Users/enriqueibarra/washdog-website")
_OUTPUT_DIR = _NEXTJS_DIR / "content" / "servicios"

BASE_URL = "https://www.washdog.cl"

# ── Logging ───────────────────────────────────────────────────────────────────

_LOG_DIR = _MOS_DIR / "logs"
_LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [hub_pages] %(message)s",
    handlers=[
        logging.FileHandler(_LOG_DIR / "generate_hub_pages.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# ── Business context ──────────────────────────────────────────────────────────

_BUSINESS_CONTEXT = """
WashDog es una peluquería canina y felina premium en Santiago, Chile.
Ubicación física: Ñuñoa, Santiago.
Servicios: peluquería canina, baño de perros, corte de perros, auto lavado de perros, peluquería de gatos, spa canino.
Diferenciadores: productos hipoalergénicos premium, atención personalizada, agenda online, personal capacitado.
Zona de servicio: Gran Santiago (28 comunas).
"""

# ── Service copy map ──────────────────────────────────────────────────────────
# Seed content that shapes the hub page tone and angle per service.

_SERVICE_CONFIG = {
    "peluqueria-canina": {
        "title":       "Peluquería Canina en Santiago",
        "description": "Peluquería canina profesional en Santiago. Cortes para todas las razas, baño completo y atención personalizada. Agenda online — servicio en las 28 comunas de Santiago.",
        "keywords":    "peluquería canina Santiago, peluquero de perros Santiago, grooming perros Santiago, corte de pelo perros Santiago",
        "h1":          "Peluquería Canina en Santiago",
        "intro_angle": "grooming profesional para perros de todas las razas, importancia de la higiene canina y el cuidado del pelaje según el tipo de pelo del perro",
        "service_detail": "peluquería canina completa: baño con shampoo hipoalergénico, secado profesional, corte de pelo según raza o preferencia del dueño, limpieza de oídos y corte de uñas",
    },
    "bano-perros": {
        "title":       "Baño de Perros en Santiago",
        "description": "Servicio de baño de perros profesional en Santiago. Productos hipoalergénicos, secado y perfume incluidos. Cubre las 28 comunas de Santiago — agenda tu hora online.",
        "keywords":    "baño de perros Santiago, bañar perros Santiago, lavado de perros Santiago, baño canino Santiago",
        "h1":          "Baño de Perros en Santiago",
        "intro_angle": "la importancia de bañar al perro con la frecuencia adecuada según raza y tipo de pelaje, productos seguros e hipoalergénicos versus champús genéricos",
        "service_detail": "baño completo que incluye lavado con shampoo hipoalergénico premium, enjuague, secado profesional con secador de mano, perfume y peinado final",
    },
    "corte-perros": {
        "title":       "Corte de Perros en Santiago",
        "description": "Corte de pelo para perros en Santiago. Estética canina para todas las razas, cortes de temporada y estilos personalizados. Disponible en las 28 comunas de Santiago.",
        "keywords":    "corte de pelo perros Santiago, corte canino Santiago, estética canina Santiago, peluquero perros Santiago",
        "h1":          "Corte de Pelo para Perros en Santiago",
        "intro_angle": "la diferencia entre un corte de pelo canino profesional y uno básico, incluyendo técnicas por raza (pelo liso, rizado, doble capa, pelo largo) y los beneficios de un grooming regular",
        "service_detail": "corte de pelo profesional adaptado a la raza y las necesidades del perro: corte de temporada, modelado de pelo, corte higiénico de patas y zona íntima",
    },
    "auto-lavado-perros": {
        "title":       "Auto Lavado de Perros en Santiago",
        "description": "Auto lavado de perros en Santiago: instala lava a tu mascota con equipos profesionales y productos premium. Práctico, económico y disponible en tu comuna.",
        "keywords":    "auto lavado perros Santiago, self-service perros Santiago, lavar perros yo mismo Santiago, auto baño perros Santiago",
        "h1":          "Auto Lavado de Perros en Santiago",
        "intro_angle": "el concepto de auto lavado de mascotas: cómo funciona, por qué es conveniente y económico, y en qué se diferencia del baño en casa o en una peluquería tradicional",
        "service_detail": "servicio de auto lavado donde el dueño puede bañar a su propio perro usando tinas profesionales de acero inoxidable, shampoo y acondicionador premium, secadores de alta potencia y toallas incluidas",
    },
    "peluqueria-gatos": {
        "title":       "Peluquería para Gatos en Santiago",
        "description": "Peluquería felina especializada en Santiago. Grooming profesional para gatos de todas las razas: baño, corte y deslanado. Atención libre de estrés en las 28 comunas.",
        "keywords":    "peluquería gatos Santiago, grooming gatos Santiago, baño gatos Santiago, corte pelo gatos Santiago",
        "h1":          "Peluquería para Gatos en Santiago",
        "intro_angle": "el grooming felino como práctica de salud (no solo estética): cómo ayuda a prevenir bolas de pelo, detectar problemas de piel y reducir la muda, con técnicas especializadas para manejar gatos con estrés mínimo",
        "service_detail": "peluquería especializada en felinos: baño con productos formulados para gatos, secado cuidadoso, corte de pelo (incluyendo corte sanitario y deslanado para pelo largo), limpieza de oídos y corte de uñas",
    },
    "spa-canino": {
        "title":       "Spa Canino en Santiago",
        "description": "Spa canino premium en Santiago. Tratamientos de relajación, hidratación de pelaje y bienestar integral para tu perro. Disponible en las 28 comunas de Santiago.",
        "keywords":    "spa canino Santiago, spa perros Santiago, tratamiento pelaje perros Santiago, bienestar canino Santiago",
        "h1":          "Spa Canino en Santiago",
        "intro_angle": "el spa canino como experiencia de bienestar integral: más allá del baño básico, incluye tratamientos de hidratación profunda, masajes relajantes y cuidados especiales para perros con ansiedad o necesidades especiales de pelaje",
        "service_detail": "experiencia spa completa: baño aromático con productos premium, masaje relajante, hidratación profunda de pelaje con mascarilla nutritiva, secado y peinado de lujo, perfume especial",
    },
}

# ── CSV loaders ───────────────────────────────────────────────────────────────

def _load_communes() -> list[dict]:
    csv_path = _MOS_DIR / "keywords" / "communes.csv"
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _load_services() -> list[dict]:
    csv_path = _MOS_DIR / "keywords" / "services.csv"
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ── Prompt builder ────────────────────────────────────────────────────────────

def _build_prompt(service_slug: str, communes: list[dict]) -> str:
    cfg = _SERVICE_CONFIG[service_slug]
    commune_list = "\n".join(f"  - {c['name']}" for c in communes)

    return f"""Eres un experto en SEO local y copywriting para mascotas. Escribe el contenido principal de una página hub de servicio para WashDog, una peluquería canina premium en Santiago, Chile.

CONTEXTO DEL NEGOCIO:
{_BUSINESS_CONTEXT}

SERVICIO A DESCRIBIR: {cfg['h1']}
ÁNGULO EDITORIAL: {cfg['intro_angle']}
DETALLE DEL SERVICIO: {cfg['service_detail']}

COMUNAS SERVIDAS (28):
{commune_list}

INSTRUCCIONES:
1. Escribe SOLO el cuerpo del artículo en markdown (sin frontmatter).
2. Longitud: 550-750 palabras.
3. Estructura sugerida:
   - Párrafo introductorio (2-3 oraciones) que incluya la keyword principal.
   - H2: ¿Qué incluye el servicio? (describe el servicio con detalle real).
   - H2: ¿Por qué elegir WashDog? (diferenciadores: productos premium, personal capacitado, agenda online).
   - H2: Cobertura en Santiago (menciona que cubren 28 comunas, incluye un párrafo con las comunas más cercanas como Ñuñoa, Providencia, Las Condes, La Reina).
   - H2: Agenda tu cita (CTA claro con link: https://www.washdog.cl).
4. Usa keywords de forma natural, NO las fuerces.
5. Tono: profesional pero cercano, orientado a dueños de mascotas en Santiago.
6. NO incluyas la tabla de comunas — eso se genera automáticamente. Solo menciona algunas en el texto.
7. NO inventes precios específicos — di "consulta nuestras tarifas online".
8. Escribe en español chileno natural.

Responde ÚNICAMENTE con el cuerpo en markdown, sin explicaciones adicionales.
"""


# ── Content generator ─────────────────────────────────────────────────────────

def _generate_content(service_slug: str, communes: list[dict]) -> str:
    """Calls Claude to generate hub page body content."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    prompt = _build_prompt(service_slug, communes)

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


# ── Markdown builder ──────────────────────────────────────────────────────────

def _build_commune_links(service_slug: str, communes: list[dict]) -> str:
    """Builds the 'Disponible en tu comuna' section with links to all 28 commune pages."""
    lines = ["## Disponible en tu comuna", ""]
    for c in communes:
        slug = f"{service_slug}-{c['slug']}"
        lines.append(f"- [{c['name']}](/servicios/{slug})")
    lines.append("")
    return "\n".join(lines)


def _build_frontmatter(service_slug: str, communes: list[dict]) -> str:
    cfg = _SERVICE_CONFIG[service_slug]
    commune_slugs = [c["slug"] for c in communes]
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    commune_yaml = "\n".join(f"  - {s}" for s in commune_slugs)
    return f"""---
title: "{cfg['title']}"
description: "{cfg['description']}"
keywords: "{cfg['keywords']}"
date: "{date_str}"
communes:
{commune_yaml}
---
"""


def build_hub_page(service_slug: str, communes: list[dict], body: str) -> str:
    """Assembles the full hub page markdown."""
    frontmatter   = _build_frontmatter(service_slug, communes)
    commune_links = _build_commune_links(service_slug, communes)
    return frontmatter + "\n" + body + "\n\n" + commune_links


# ── Main generation logic ─────────────────────────────────────────────────────

def generate_hub_pages(
    service_filter: str | None = None,
    dry_run: bool = False,
    force: bool = False,
) -> None:
    services = _load_services()
    communes = _load_communes()

    if service_filter:
        services = [s for s in services if s["slug"] == service_filter]
        if not services:
            log.error(f"Service '{service_filter}' not found in services.csv")
            sys.exit(1)

    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    generated = 0
    skipped   = 0

    for svc in services:
        slug     = svc["slug"]
        out_path = _OUTPUT_DIR / f"{slug}.md"

        if out_path.exists() and not force:
            log.info(f"  [skip] Already exists (use --force to overwrite): {out_path.name}")
            skipped += 1
            continue

        log.info(f"  Generating hub page: {slug} ...")

        if dry_run:
            log.info(f"  [dry-run] Would write: {out_path}")
            generated += 1
            continue

        try:
            body    = _generate_content(slug, communes)
            content = build_hub_page(slug, communes, body)
            out_path.write_text(content, encoding="utf-8")
            log.info(f"  [OK] Written: {out_path}")
            generated += 1
        except Exception as e:
            log.error(f"  [FAIL] {slug}: {e}")

    log.info(f"\nDone. Generated: {generated} | Skipped: {skipped}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog        = "generate_hub_pages.py",
        description = "Marketing OS — Hub page generator for WashDog services",
        formatter_class = argparse.RawDescriptionHelpFormatter,
        epilog = """
Examples:
  python generate_hub_pages.py                           # generate all 6 hub pages
  python generate_hub_pages.py --dry-run                 # preview without writing
  python generate_hub_pages.py --service peluqueria-canina  # single service
  python generate_hub_pages.py --force                   # overwrite existing files
        """,
    )
    parser.add_argument("--service",  help="Generate a single service by slug (e.g. peluqueria-canina)")
    parser.add_argument("--dry-run",  action="store_true", help="Preview without writing files")
    parser.add_argument("--force",    action="store_true", help="Overwrite existing hub page files")

    args = parser.parse_args()
    generate_hub_pages(
        service_filter = args.service,
        dry_run        = args.dry_run,
        force          = args.force,
    )


if __name__ == "__main__":
    main()
