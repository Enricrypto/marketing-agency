#!/usr/bin/env python3
"""
Marketing OS — Workflow CLI (Phase 4)
WashDog Growth Infrastructure

Ejecuta workflows de marketing para WashDog desde la línea de comandos.

Uso:
    python run_workflow.py blog --topic "cuidado del pelaje en verano" --keyword "peluquería canina Santiago"
    python run_workflow.py landing --service "baño antipulgas" --location "Providencia"
    python run_workflow.py campaign --name "Verano 2026" --season verano --offer "2x1 en baño"
    python run_workflow.py report
    python run_workflow.py db-init
"""

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()


# ── Helpers de output ─────────────────────────────────────────────────────────

def _print_result(result: dict) -> None:
    """Imprime el resultado de un workflow de forma legible."""
    print("\n" + "═" * 60)
    print(f"  WORKFLOW COMPLETADO — ID: {result['workflow_id'][:8]}")
    print("═" * 60)

    if "title" in result:
        print(f"\n  Título:  {result['title']}")
    if "campaign_name" in result:
        print(f"\n  Campaña: {result['campaign_name']}")

    scores = result.get("scores", {})
    if scores:
        overall = scores.get("overall_score", 0)
        blocks = min(max(int(overall // 10), 0), 10)
        bar = "█" * blocks + "░" * (10 - blocks)
        print(f"\n  Scores [{bar}] {overall}/100")
        print(f"    SEO:          {scores.get('seo_score', 0)}/100")
        print(f"    Legibilidad:  {scores.get('readability_score', 0)}/100")
        print(f"    Conversión:   {scores.get('conversion_score', 0)}/100")
        print(f"    Relevancia:   {scores.get('local_relevance_score', 0)}/100")
        if scores.get("notes"):
            print(f"    Notas:        {scores['notes']}")

    print("\n" + "─" * 60)

    # Mostrar contenido principal según tipo de workflow
    if "content" in result:
        content_preview = result["content"][:1_500]
        if len(result["content"]) > 1_500:
            content_preview += f"\n\n... [{len(result['content']) - 1_500} caracteres más]"
        print("\n" + content_preview)

    elif "copy_assets" in result:
        assets = result["copy_assets"]
        if isinstance(assets, dict):
            for key, val in assets.items():
                if val and key != "raw_copy":
                    print(f"\n── {key.upper().replace('_', ' ')} ──")
                    print(val)
        if "roi_projection" in result:
            print("\n── PROYECCIÓN DE ROI ──")
            print(result["roi_projection"])

    print("\n" + "═" * 60)


# ── Comandos ──────────────────────────────────────────────────────────────────

def cmd_blog(args) -> None:
    from workflows.blog_seo import run_blog_seo
    result = run_blog_seo(
        topic           = args.topic,
        target_keyword  = args.keyword,
        city            = args.city,
        model           = args.model,
    )
    _print_result(result)


def cmd_landing(args) -> None:
    from workflows.landing_page import run_landing_page
    result = run_landing_page(
        service   = args.service,
        location  = args.location,
        promotion = args.promotion or "",
        model     = args.model,
    )
    _print_result(result)


def cmd_campaign(args) -> None:
    from workflows.seasonal_campaign import run_seasonal_campaign
    result = run_seasonal_campaign(
        campaign_name = args.name,
        season        = args.season,
        offer         = args.offer or "",
        model         = args.model,
    )
    _print_result(result)


def cmd_report(args) -> None:
    from analytics.queries import (
        avg_seo_scores_by_type, cost_per_workflow,
        top_performing_content, agent_efficiency,
        workflow_success_rate, print_report,
    )
    print_report("Score Promedio por Tipo de Contenido",  avg_seo_scores_by_type())
    print_report("Top 5 Contenidos por Overall Score",   top_performing_content(5))
    print_report("Costo por Workflow (más recientes)",    cost_per_workflow())
    print_report("Eficiencia por Agente",                agent_efficiency())
    print_report("Tasa de Éxito por Tipo de Workflow",   workflow_success_rate())


def cmd_db_init(args) -> None:
    from db import init_db, fetch_all
    init_db()
    tables = fetch_all("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    print("[db] Tablas disponibles:")
    for t in tables:
        print(f"  • {t['name']}")


# ── Parser ────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog        = "run_workflow.py",
        description = "Marketing OS — WashDog Growth Infrastructure",
        formatter_class = argparse.RawDescriptionHelpFormatter,
        epilog = """
Ejemplos:
  python run_workflow.py blog \\
      --topic "cuidado del pelaje en verano" \\
      --keyword "peluquería canina Santiago" \\
      --city "Santiago"

  python run_workflow.py landing \\
      --service "baño antipulgas" \\
      --location "Providencia" \\
      --promotion "20% descuento primera visita"

  python run_workflow.py campaign \\
      --name "Campaña Verano 2026" \\
      --season verano \\
      --offer "2x1 en baño hasta el 28 de febrero"

  python run_workflow.py report
  python run_workflow.py db-init
        """,
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # ── blog ──
    p_blog = sub.add_parser("blog", help="Generar artículo SEO para WashDog")
    p_blog.add_argument("--topic",   required=True, help="Tema del artículo")
    p_blog.add_argument("--keyword", required=True, help="Keyword SEO principal")
    p_blog.add_argument("--city",    default="Santiago", help="Ciudad objetivo (default: Santiago)")
    p_blog.add_argument("--model",   default="claude-sonnet-4-6", help="Modelo Claude")

    # ── landing ──
    p_land = sub.add_parser("landing", help="Generar landing page de servicio")
    p_land.add_argument("--service",   required=True, help="Nombre del servicio")
    p_land.add_argument("--location",  required=True, help="Comuna o ciudad")
    p_land.add_argument("--promotion", default="",    help="Promoción activa (opcional)")
    p_land.add_argument("--model",     default="claude-sonnet-4-6", help="Modelo Claude")

    # ── campaign ──
    p_camp = sub.add_parser("campaign", help="Generar campaña estacional multi-canal")
    p_camp.add_argument("--name",   required=True, help="Nombre de la campaña")
    p_camp.add_argument("--season", required=True, help="Temporada (verano, invierno, etc.)")
    p_camp.add_argument("--offer",  default="",    help="Oferta principal (opcional)")
    p_camp.add_argument("--model",  default="claude-sonnet-4-6", help="Modelo Claude")

    # ── report ──
    sub.add_parser("report", help="Ver reporte de analytics desde la base de datos")

    # ── db-init ──
    sub.add_parser("db-init", help="Inicializar / verificar base de datos SQLite")

    return parser


def main() -> None:
    parser  = build_parser()
    args    = parser.parse_args()

    commands = {
        "blog":     cmd_blog,
        "landing":  cmd_landing,
        "campaign": cmd_campaign,
        "report":   cmd_report,
        "db-init":  cmd_db_init,
    }

    handler = commands.get(args.command)
    if not handler:
        parser.print_help()
        sys.exit(1)

    try:
        handler(args)
    except (EnvironmentError, FileNotFoundError, ValueError) as e:
        print(f"\n[error] {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[cancelado] Workflow interrumpido por el usuario.")
        sys.exit(0)


if __name__ == "__main__":
    main()
