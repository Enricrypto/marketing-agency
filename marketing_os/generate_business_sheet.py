#!/usr/bin/env python3
"""
Marketing OS — Business Directory Sheet Generator
WashDog Local SEO — Single Source of Truth for Directory Submissions.

Creates or updates a Google Sheet: "WashDog Master Directory Info"
One row per location (commune). Used as the master reference for:
  - Google Business Profile
  - Local directory submissions (Yelp, Páginas Amarillas, etc.)
  - NAP consistency audits (Name, Address, Phone)
  - Future bulk CSV exports

Usage:
    python generate_business_sheet.py --init        # create/reset the sheet with all communes
    python generate_business_sheet.py --update      # update existing sheet (skips existing rows)
    python generate_business_sheet.py --csv         # export to washdog_directory.csv locally
    python generate_business_sheet.py --dry-run     # print rows without writing
"""

import argparse
import csv
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

# ── Logging ───────────────────────────────────────────────────────────────────

_LOG_DIR = Path(__file__).parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [business_sheet] %(message)s",
    handlers=[
        logging.FileHandler(_LOG_DIR / "generate_business_sheet.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# ── Sheet config ──────────────────────────────────────────────────────────────

SHEET_NAME = "WashDog Master Directory Info"

HEADERS = [
    "Business Name",
    "Commune",
    "Address",
    "Phone",
    "Website",
    "Services",
    "Hours",
    "Description",
    "Short Description",
    "Keywords",
    "Category",
    "Images",
    "Hub Page URL",
    "Status",
]

# ── Business data ─────────────────────────────────────────────────────────────
# Central source of truth — update here when any business info changes.

_BUSINESS = {
    "name":     "WashDog",
    "address":  " Av. Irarrázaval 2086, B, 7750000 Ñuñoa, Región Metropolitana, Chile",
    "phone":    "+56 9 87230388",      
    "website":  "https://www.washdog.cl",
    "hours":    "Lunes–Domingo 10:00–20:00",
    "category": "Peluquería y estética de mascotas",
    "services": (
        "Peluquería canina, Baño de perros, Corte de pelo canino, "
        "Auto lavado de perros, Peluquería de gatos, Spa canino"
    ),
    "images":   "Logo + foto exterior + 2 fotos de atención",
}

BASE_URL = "https://www.washdog.cl"

# ── Priority communes for directory submissions ───────────────────────────────
# Listed in submission priority order. All 28 communes of Gran Santiago.

_COMMUNES = [
    # slug, display name, specific address (if different from base), priority tier
    ("nunoa",              "Ñuñoa",              "Ñuñoa, Santiago",               "1 — Main"),
    ("providencia",        "Providencia",         "Providencia, Santiago",          "1 — Priority"),
    ("las-condes",         "Las Condes",          "Las Condes, Santiago",           "1 — Priority"),
    ("la-reina",           "La Reina",            "La Reina, Santiago",             "1 — Priority"),
    ("macul",              "Macul",               "Macul, Santiago",                "1 — Priority"),
    ("santiago-centro",    "Santiago Centro",     "Santiago Centro, Santiago",      "2 — Secondary"),
    ("penalolen",          "Peñalolén",           "Peñalolén, Santiago",            "2 — Secondary"),
    ("la-florida",         "La Florida",          "La Florida, Santiago",           "2 — Secondary"),
    ("vitacura",           "Vitacura",            "Vitacura, Santiago",             "2 — Secondary"),
    ("lo-barnechea",       "Lo Barnechea",        "Lo Barnechea, Santiago",         "2 — Secondary"),
    ("huechuraba",         "Huechuraba",          "Huechuraba, Santiago",           "3 — Expansion"),
    ("independencia",      "Independencia",       "Independencia, Santiago",        "3 — Expansion"),
    ("recoleta",           "Recoleta",            "Recoleta, Santiago",             "3 — Expansion"),
    ("quilicura",          "Quilicura",           "Quilicura, Santiago",            "3 — Expansion"),
    ("cerro-navia",        "Cerro Navia",         "Cerro Navia, Santiago",          "3 — Expansion"),
    ("renca",              "Renca",               "Renca, Santiago",                "3 — Expansion"),
    ("quinta-normal",      "Quinta Normal",       "Quinta Normal, Santiago",        "3 — Expansion"),
    ("lo-prado",           "Lo Prado",            "Lo Prado, Santiago",             "3 — Expansion"),
    ("estacion-central",   "Estación Central",    "Estación Central, Santiago",     "3 — Expansion"),
    ("san-miguel",         "San Miguel",          "San Miguel, Santiago",           "3 — Expansion"),
    ("san-joaquin",        "San Joaquín",         "San Joaquín, Santiago",          "3 — Expansion"),
    ("pedro-aguirre-cerda","Pedro Aguirre Cerda", "Pedro Aguirre Cerda, Santiago",  "3 — Expansion"),
    ("san-ramon",          "San Ramón",           "San Ramón, Santiago",            "3 — Expansion"),
    ("lo-espejo",          "Lo Espejo",           "Lo Espejo, Santiago",            "3 — Expansion"),
    ("cerrillos",          "Cerrillos",           "Cerrillos, Santiago",            "3 — Expansion"),
    ("la-granja",          "La Granja",           "La Granja, Santiago",            "3 — Expansion"),
    ("la-cisterna",        "La Cisterna",         "La Cisterna, Santiago",          "3 — Expansion"),
    ("la-pintana",         "La Pintana",          "La Pintana, Santiago",           "3 — Expansion"),
]

# ── Row builder ───────────────────────────────────────────────────────────────

def _build_row(commune_slug: str, commune_name: str, address: str, tier: str) -> list:
    """Builds one directory row for a given commune."""
    business_name = f"{_BUSINESS['name']} — {commune_name}"
    description = (
        f"WashDog es una peluquería canina profesional que atiende en {commune_name}, Santiago. "
        f"Ofrecemos baño de perros, corte de pelo, peluquería de gatos y spa canino con productos "
        f"hipoalergénicos premium. Agenda online disponible en www.washdog.cl."
    )
    short_description = (
        f"Peluquería y estética canina en {commune_name}. "
        f"Baño, corte y spa para perros y gatos. Agenda online."
    )
    keywords = (
        f"peluquería canina {commune_name}, baño de perros {commune_name}, "
        f"grooming perros {commune_name}, corte pelo perros {commune_name}"
    )
    hub_url = f"{BASE_URL}/servicios/peluqueria-canina-{commune_slug}"

    return [
        business_name,
        commune_name,
        address,
        _BUSINESS["phone"],
        _BUSINESS["website"],
        _BUSINESS["services"],
        _BUSINESS["hours"],
        description,
        short_description,
        keywords,
        _BUSINESS["category"],
        _BUSINESS["images"],
        hub_url,
        tier,
    ]


def _build_all_rows() -> list[list]:
    """Returns [headers] + one row per commune."""
    rows = [HEADERS]
    for slug, name, address, tier in _COMMUNES:
        rows.append(_build_row(slug, name, address, tier))
    return rows


# ── Outputs ───────────────────────────────────────────────────────────────────

def write_to_sheet(rows: list[list], reset: bool = False) -> str:
    """
    Writes rows to Google Sheets.

    Args:
        rows:  All rows including headers.
        reset: If True, overwrites the entire sheet. If False, appends new rows only.

    Returns:
        Sheet URL.
    """
    from workspace.api import append_to_sheet, _sheets, _find_sheet_by_name

    if reset:
        # Full overwrite: use append_to_sheet which creates-or-replaces
        # We clear by writing from scratch (sheet is re-created if it doesn't exist)
        existing_id = _find_sheet_by_name(SHEET_NAME)
        if existing_id:
            # Clear existing content and rewrite
            service = _sheets()
            service.spreadsheets().values().clear(
                spreadsheetId=existing_id,
                range=f"{SHEET_NAME}!A:Z",
            ).execute()
            service.spreadsheets().values().update(
                spreadsheetId=existing_id,
                range=f"{SHEET_NAME}!A1",
                valueInputOption="RAW",
                body={"values": rows},
            ).execute()
            url = f"https://docs.google.com/spreadsheets/d/{existing_id}/edit"
            log.info(f"[OK] Sheet cleared and rewritten: {url}")
            return url
        else:
            sheet_id = append_to_sheet(SHEET_NAME, rows)
            return f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
    else:
        # Append only header + data rows (skip header if sheet exists)
        sheet_id = append_to_sheet(SHEET_NAME, rows)
        return f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"


def write_to_csv(rows: list[list]) -> Path:
    """Exports rows to a local CSV file."""
    out_path = Path(__file__).parent / "outputs" / "washdog_directory.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    log.info(f"[OK] CSV exported: {out_path}  ({len(rows) - 1} data rows)")
    return out_path


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog        = "generate_business_sheet.py",
        description = "Marketing OS — Business directory sheet generator for WashDog",
        formatter_class = argparse.RawDescriptionHelpFormatter,
        epilog = """
Examples:
  python generate_business_sheet.py --init        # create/reset the Google Sheet
  python generate_business_sheet.py --update      # append new rows to existing sheet
  python generate_business_sheet.py --csv         # export CSV locally
  python generate_business_sheet.py --dry-run     # preview rows without writing
        """,
    )
    parser.add_argument("--init",    action="store_true", help="Create or fully reset the Google Sheet")
    parser.add_argument("--update",  action="store_true", help="Append rows to existing sheet")
    parser.add_argument("--csv",     action="store_true", help="Export rows to local CSV file")
    parser.add_argument("--dry-run", action="store_true", help="Preview rows without writing")

    args = parser.parse_args()

    if not any([args.init, args.update, args.csv, args.dry_run]):
        parser.print_help()
        sys.exit(1)

    rows = _build_all_rows()
    log.info(f"Built {len(rows) - 1} directory rows ({len(_COMMUNES)} communes)")

    if args.dry_run:
        print(f"\n{'─' * 70}")
        print(f"  DRY RUN — {SHEET_NAME}")
        print(f"{'─' * 70}")
        print(f"  Headers: {HEADERS}")
        print(f"\n  Sample row (Ñuñoa):")
        for header, value in zip(HEADERS, rows[1]):
            print(f"    {header:<22} {value}")
        print(f"\n  Total: {len(rows) - 1} rows (1 per commune)")
        print(f"{'─' * 70}\n")
        return

    if args.init or args.update:
        try:
            url = write_to_sheet(rows, reset=args.init)
            log.info(f"Sheet URL: {url}")
        except Exception as e:
            log.error(f"Failed to write to Google Sheets: {e}")
            sys.exit(1)

    if args.csv:
        write_to_csv(rows)


if __name__ == "__main__":
    main()
