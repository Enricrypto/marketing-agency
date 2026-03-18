#!/usr/bin/env python3
"""
Marketing OS — Enrich service pages with local landmark sections.

Adds a "Dónde pasear a tu perro en [Commune]" section to commune pages
that are missing local content — a key signal for Google local relevance.

Usage:
    python enrich_local_sections.py --dry-run   # preview changes
    python enrich_local_sections.py             # apply + commit
"""

import argparse
import subprocess
import sys
from pathlib import Path

_CONTENT_DIR = Path("/Users/enriqueibarra/washdog-website/content/servicios")
_WEBSITE_DIR = Path("/Users/enriqueibarra/washdog-website")

# ── Local content per commune ──────────────────────────────────────────────────
# Parks, metro stops, and local context for each commune.
# WashDog address: Irarrázaval 2086 B, Ñuñoa (near metro Ñuñoa, Línea 3)

LOCAL_SECTIONS: dict[str, str] = {

    "peluqueria-canina-nunoa": """
### Paseos cerca de WashDog en Ñuñoa

Ñuñoa es una de las comunas más amigables con mascotas de Santiago. Muchos de nuestros clientes aprovechan de pasear a sus perros antes o después de la visita a WashDog.

**Parques y espacios favoritos en Ñuñoa:**
- **Parque Juan XXIII** — ideal para perros activos, con áreas verdes amplias y sombra
- **Plaza Ñuñoa** — perfecta para paseos tranquilos en el barrio
- **Parque Paraguay** — zona residencial tranquila a pasos de Irarrázaval
- **Parque Inés de Suárez** — popular entre familias con mascotas del sector

**Cómo llegar a WashDog desde Ñuñoa:**
Estamos en Irarrázaval 2086 B. La forma más fácil es tomar **Metro Ñuñoa (Línea 3)** o **Metro Irarrázaval (Línea 3)** — quedamos a menos de 10 minutos caminando desde cualquier estación del eje Irarrázaval.
""",

    "peluqueria-canina-providencia": """
### Paseos cerca de WashDog en Providencia

Providencia tiene varios parques excelentes para pasear antes de traer a tu perro a su sesión de grooming. Muchos clientes de Providencia nos visitan combinando el paseo con la cita en WashDog.

**Parques y espacios favoritos en Providencia:**
- **Parque Balmaceda** — uno de los más grandes de la zona, ideal para perros enérgicos
- **Parque Uruguay** — espacio tranquilo y arbolado sobre el Canal San Carlos
- **Parque Bustamante** — popular entre mascotas del sector Pedro de Valdivia
- **Parque Inés de Suárez** — en el límite con Ñuñoa, a minutos de WashDog

**Cómo llegar a WashDog desde Providencia:**
Toma **Metro Salvador (Línea 1)** o **Metro Pedro de Valdivia (Línea 1)** y combina con bus por Irarrázaval directo hasta nuestra puerta — en menos de 20 minutos estás acá.
""",

    "peluqueria-canina-las-condes": """
### Paseos cerca de WashDog en Las Condes

Las Condes tiene algunos de los mejores parques caninos de Santiago. Muchos de nuestros clientes del sector oriente aprovechan de pasear antes de traernos a su perro.

**Parques y espacios favoritos en Las Condes:**
- **Parque Araucano** — el parque canino más grande de Las Condes, con zona especial para perros
- **Parque Juan Pablo II** — espacio verde amplio sobre Av. Apoquindo
- **Parque de los Andes** — ideal para razas grandes que necesitan correr
- **Parque Padre Hurtado** — tranquilo y arbolado en el sector alto

**Cómo llegar a WashDog desde Las Condes:**
Toma **Metro Tobalaba (Línea 1 o Línea 4)** o **Metro El Golf (Línea 1)** y combina hacia Ñuñoa. En auto, Irarrázaval conecta directamente con Av. Apoquindo — unos 15 minutos sin tráfico.
""",

    "peluqueria-canina-vitacura": """
### Paseos cerca de WashDog en Vitacura

Vitacura es conocida por sus amplias veredas arboladas y parques bien mantenidos — perfectos para pasear perros. Varios de nuestros clientes de Vitacura hacen del paseo y el grooming una rutina semanal.

**Parques y espacios favoritos en Vitacura:**
- **Parque Bicentenario** — con zona especial de perros, ideal para cualquier raza
- **Parque La Dehesa** — cerca del límite con Lo Barnechea, con senderos extensos
- **Av. Alonso de Córdova** — veredas amplias y arboladas, muy transitadas por mascotas
- **Parque Los Andes** — orillas del río Mapocho, zona verde tranquila

**Cómo llegar a WashDog desde Vitacura:**
En auto por Av. Las Condes → Tobalaba → Irarrázaval son aproximadamente 20 minutos. También puedes llegar en **Metro Tobalaba (Línea 1)** combinando con bus hacia Ñuñoa.
""",

    "peluqueria-canina-macul": """
### Paseos cerca de WashDog en Macul

Macul y Ñuñoa son comunas vecinas, lo que hace que WashDog sea una de las peluquerías caninas más cercanas para quienes viven en Macul. Muchos clientes del sector nos visitan regularmente.

**Parques y espacios favoritos en Macul:**
- **Parque Macul** — zona verde con árboles y espacio abierto para correr
- **Plaza Los Castaños** — tranquila y familiar, popular entre vecinos con mascotas
- **Canal San Carlos** — paseo lineal ideal para caminatas largas con perros energéticos
- **Estadio San Carlos de Apoquindo** — alrededores con veredas amplias para pasear

**Cómo llegar a WashDog desde Macul:**
Toma **Metro Macul (Línea 4A)** y conecta a Ñuñoa — o simplemente ven en auto por Av. Departamental. Estamos en Irarrázaval 2086 B, a menos de 10 minutos desde Macul.
""",

    "peluqueria-canina-la-florida": """
### Paseos cerca de WashDog en La Florida

La Florida tiene varios parques naturales únicos en Santiago. Antes de venir a WashDog, muchos dueños de La Florida aprovechan de cansarlos un poco — así llegan más tranquilos a la sesión.

**Parques y espacios favoritos en La Florida:**
- **Parque Mahuida** — uno de los parques naturales más grandes de Santiago, con senderos de tierra ideales para perros activos
- **Quebrada de Macul** — zona natural con vegetación nativa y senderos amplios
- **Parque Lo Cañas** — zona residencial tranquila con áreas verdes bien mantenidas
- **Canal San Carlos** — paseo lineal que conecta varias comunas del sur oriente

**Cómo llegar a WashDog desde La Florida:**
Toma **Metro Las Mercedes (Línea 4)** o **Metro La Florida (Línea 4)** conectando hacia Ñuñoa. En auto por Av. Vicuña Mackenna llegas directo a Irarrázaval en unos 20-25 minutos.
""",

    "peluqueria-canina-huechuraba": """
### Paseos cerca de WashDog en Huechuraba

Huechuraba tiene espacios naturales excelentes para perros, especialmente en el sector alto de la comuna. Muchos clientes del sector norte de Santiago nos eligen por la calidad del servicio y el trato individualizado.

**Parques y espacios favoritos en Huechuraba:**
- **Parque Cerro Colorado** — área natural con vistas y senderos, perfecta para perros exploradores
- **Parque Estadio** — zona verde con espacio para correr en el sector Recoleta / Huechuraba
- **Av. Los Libertadores** — veredas amplias en el corredor principal de la comuna
- **Sector La Punta** — zona residencial tranquila con espacios verdes informales

**Cómo llegar a WashDog desde Huechuraba:**
La mejor ruta en auto es por Av. Recoleta → Av. Irarrázaval, aproximadamente 25-30 minutos. En transporte público, combina bus desde Huechuraba hacia el centro y luego metro Línea 3 hasta la estación Ñuñoa.
""",
}


# ── Anchor text before which we insert the local section ──────────────────────
_INSERT_BEFORE = "### ¿Listo para darle lo mejor"


def _add_local_section(slug: str, content: str, local_md: str) -> str | None:
    """
    Inserts the local section before the final CTA block.
    Returns updated content, or None if already present or anchor not found.
    """
    if "Paseos cerca de WashDog" in content:
        return None  # already has a local section

    idx = content.find(_INSERT_BEFORE)
    if idx == -1:
        # Fallback: insert before the last --- separator
        idx = content.rfind("\n---\n")
        if idx == -1:
            return None

    section = f"\n---\n{local_md.strip()}\n\n---\n\n"
    return content[:idx] + section + content[idx:]


def run(dry_run: bool = False) -> None:
    changed = []

    for slug, local_md in LOCAL_SECTIONS.items():
        path = _CONTENT_DIR / f"{slug}.md"
        if not path.exists():
            print(f"[enrich] SKIP (file not found): {slug}")
            continue

        original = path.read_text(encoding="utf-8")
        updated = _add_local_section(slug, original, local_md)

        if updated is None:
            print(f"[enrich] SKIP (already has local section): {slug}")
            continue

        if dry_run:
            print(f"[enrich] DRY-RUN: would enrich {slug}")
            continue

        path.write_text(updated, encoding="utf-8")
        print(f"[enrich] Enriched: {slug}")
        changed.append(f"content/servicios/{slug}.md")

    if not changed:
        print("[enrich] Nothing to commit.")
        return

    # Git commit + push
    try:
        subprocess.run(["git", "add"] + changed, cwd=str(_WEBSITE_DIR), check=True)
        subprocess.run(
            ["git", "commit", "-m", f"seo: add local landmark sections to {len(changed)} commune pages\n\nAdds neighbourhood parks, metro stops and routing info per commune\nto strengthen local relevance signals for Google.\n\nCo-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"],
            cwd=str(_WEBSITE_DIR), check=True,
        )
        subprocess.run(["git", "push"], cwd=str(_WEBSITE_DIR), check=True)
        print(f"\n[enrich] Committed and pushed {len(changed)} file(s).")
    except subprocess.CalledProcessError as e:
        print(f"[enrich] Git error: {e}")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Add local landmark sections to commune pages")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing files")
    args = parser.parse_args()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
