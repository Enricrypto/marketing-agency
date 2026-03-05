"""
Marketing OS — Analytics Queries (Phase 4)
Consultas pre-escritas para dashboards y reportes de WashDog.

Todas las funciones retornan list[dict] listos para imprimir, exportar
o consumir desde un dashboard (Streamlit, Datasette, etc.).

Uso:
    from analytics.queries import cost_per_workflow, print_report
    rows = cost_per_workflow()
    print_report("Costo por Workflow", rows)
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from db import fetch_all


# ── Dashboard 1 — Content Performance ────────────────────────────────────────

def avg_seo_scores_by_type() -> list[dict]:
    """Score SEO y overall promedio por tipo de contenido."""
    return fetch_all("""
        SELECT
            co.content_type                       AS tipo,
            COUNT(*)                              AS total_piezas,
            ROUND(AVG(e.seo_score),             1) AS seo_promedio,
            ROUND(AVG(e.readability_score),     1) AS legibilidad_promedio,
            ROUND(AVG(e.conversion_score),      1) AS conversion_promedio,
            ROUND(AVG(e.local_relevance_score), 1) AS relevancia_local_promedio,
            ROUND(AVG(e.overall_score),         1) AS overall_promedio
        FROM evaluations e
        JOIN content_outputs co ON co.workflow_id = e.workflow_id
        GROUP BY co.content_type
        ORDER BY overall_promedio DESC
    """)


def content_production_summary() -> list[dict]:
    """Piezas de contenido producidas por tipo y semana."""
    return fetch_all("""
        SELECT
            content_type                          AS tipo,
            strftime('%Y-W%W', created_at)        AS semana,
            COUNT(*)                              AS piezas,
            ROUND(AVG(word_count), 0)             AS palabras_promedio,
            SUM(word_count)                       AS palabras_totales
        FROM content_outputs
        GROUP BY content_type, semana
        ORDER BY semana DESC, tipo
    """)


def top_performing_content(limit: int = 10) -> list[dict]:
    """Las piezas de contenido con mayor overall_score."""
    return fetch_all("""
        SELECT
            co.title                              AS titulo,
            co.content_type                       AS tipo,
            e.overall_score                       AS overall,
            e.seo_score                           AS seo,
            e.conversion_score                    AS conversion,
            e.local_relevance_score               AS relevancia_local,
            co.word_count                         AS palabras,
            strftime('%d/%m/%Y', co.created_at)   AS fecha
        FROM content_outputs co
        JOIN evaluations e ON e.workflow_id = co.workflow_id
        ORDER BY e.overall_score DESC
        LIMIT ?
    """, (limit,))


def content_quality_trend() -> list[dict]:
    """Evolución del overall_score promedio por semana."""
    return fetch_all("""
        SELECT
            strftime('%Y-W%W', e.created_at)   AS semana,
            COUNT(*)                           AS evaluaciones,
            ROUND(AVG(e.overall_score),  1)    AS overall_promedio,
            ROUND(AVG(e.seo_score),      1)    AS seo_promedio,
            ROUND(AVG(e.conversion_score), 1)  AS conversion_promedio
        FROM evaluations e
        GROUP BY semana
        ORDER BY semana DESC
    """)


# ── Dashboard 2 — Conversion & Cost Performance ───────────────────────────────

def cost_per_workflow() -> list[dict]:
    """Costo total en USD y tokens por workflow, ordenado por más reciente."""
    return fetch_all("""
        SELECT
            w.id                                    AS workflow_id,
            w.type                                  AS tipo,
            w.topic                                 AS tema,
            w.city                                  AS ciudad,
            w.status                                AS estado,
            ROUND(SUM(s.cost_usd), 4)               AS costo_usd,
            SUM(s.token_input + s.token_output)     AS tokens_totales,
            COUNT(s.id)                             AS steps,
            strftime('%d/%m/%Y %H:%M', w.started_at) AS iniciado
        FROM workflows w
        LEFT JOIN steps s ON s.workflow_id = w.id
        GROUP BY w.id
        ORDER BY w.started_at DESC
    """)


def monthly_cost_report() -> list[dict]:
    """Costo mensual por tipo de workflow (workflows completados)."""
    return fetch_all("""
        SELECT
            strftime('%Y-%m', w.started_at)   AS mes,
            w.type                            AS tipo_workflow,
            COUNT(DISTINCT w.id)              AS workflows_completados,
            ROUND(SUM(s.cost_usd), 4)         AS costo_usd_total,
            ROUND(AVG(s.cost_usd), 4)         AS costo_usd_promedio_step
        FROM workflows w
        LEFT JOIN steps s ON s.workflow_id = w.id
        WHERE w.status = 'completed'
        GROUP BY mes, w.type
        ORDER BY mes DESC, costo_usd_total DESC
    """)


def performance_metrics_summary() -> list[dict]:
    """
    Resumen de métricas de performance reales importadas.
    (Se populará cuando se integre Google Analytics / Search Console.)
    """
    return fetch_all("""
        SELECT
            w.type                              AS tipo_workflow,
            w.topic                             AS tema,
            SUM(pm.page_views)                  AS vistas_totales,
            ROUND(AVG(pm.avg_time_on_page), 1)  AS tiempo_promedio_seg,
            ROUND(AVG(pm.bounce_rate) * 100, 1) AS tasa_rebote_pct,
            SUM(pm.conversions)                 AS conversiones_totales,
            ROUND(SUM(pm.revenue_generated), 0) AS ingresos_clp,
            strftime('%d/%m/%Y', pm.recorded_at) AS registrado
        FROM performance_metrics pm
        JOIN workflows w ON w.id = pm.workflow_id
        GROUP BY w.id
        ORDER BY ingresos_clp DESC
    """)


# ── Dashboard 3 — Agent Efficiency ───────────────────────────────────────────

def agent_efficiency() -> list[dict]:
    """Tokens promedio, costo y duración por agente de marketing."""
    return fetch_all("""
        SELECT
            agent_name                                      AS agente,
            COUNT(*)                                        AS total_steps,
            ROUND(AVG(token_input + token_output), 0)       AS tokens_promedio,
            ROUND(SUM(cost_usd), 4)                         AS costo_usd_total,
            ROUND(AVG(cost_usd), 4)                         AS costo_usd_promedio,
            ROUND(AVG(duration_ms) / 1000.0, 1)             AS duracion_promedio_seg,
            SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) AS fallos
        FROM steps
        WHERE agent_name IS NOT NULL
        GROUP BY agent_name
        ORDER BY costo_usd_total DESC
    """)


def step_performance_by_workflow_type() -> list[dict]:
    """Duración y costo promedio de cada step, desglosado por tipo de workflow."""
    return fetch_all("""
        SELECT
            w.type                                  AS tipo_workflow,
            s.step_name                             AS step,
            COUNT(*)                                AS ejecuciones,
            ROUND(AVG(s.token_input),  0)           AS tokens_entrada_prom,
            ROUND(AVG(s.token_output), 0)           AS tokens_salida_prom,
            ROUND(AVG(s.cost_usd), 4)               AS costo_usd_prom,
            ROUND(AVG(s.duration_ms) / 1000.0, 1)   AS duracion_prom_seg,
            SUM(CASE WHEN s.status='failed' THEN 1 ELSE 0 END) AS fallos
        FROM steps s
        JOIN workflows w ON w.id = s.workflow_id
        GROUP BY w.type, s.step_name
        ORDER BY w.type, s.step_name
    """)


def workflow_success_rate() -> list[dict]:
    """Tasa de éxito de workflows por tipo."""
    return fetch_all("""
        SELECT
            type                                               AS tipo,
            COUNT(*)                                           AS total,
            SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) AS completados,
            SUM(CASE WHEN status='failed'    THEN 1 ELSE 0 END) AS fallidos,
            SUM(CASE WHEN status='running'   THEN 1 ELSE 0 END) AS en_progreso,
            ROUND(
                100.0 * SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) / COUNT(*),
                1
            )                                                  AS tasa_exito_pct
        FROM workflows
        GROUP BY type
        ORDER BY tasa_exito_pct DESC
    """)


# ── Utilidad de impresión ─────────────────────────────────────────────────────

def print_report(title: str, rows: list[dict], max_col_width: int = 30) -> None:
    """
    Imprime una tabla formateada en consola.

    Args:
        title:         Título del reporte
        rows:          Lista de dicts (output de cualquier query)
        max_col_width: Ancho máximo de columna para truncar valores largos
    """
    if not rows:
        print(f"\n── {title} ──\n  (sin datos)\n")
        return

    headers = list(rows[0].keys())

    # Calcular anchos de columna (limitado por max_col_width)
    col_widths = {}
    for h in headers:
        max_val = max(len(str(r.get(h, "") or "")) for r in rows)
        col_widths[h] = min(max_col_width, max(len(h), max_val))

    total_width = sum(col_widths.values()) + len(headers) * 3

    # Imprimir encabezado
    print(f"\n{'─' * 4} {title} {'─' * max(0, total_width - len(title) - 6)}")
    header_row = "  ".join(h.ljust(col_widths[h]) for h in headers)
    print(header_row)
    print("─" * len(header_row))

    # Imprimir filas
    for row in rows:
        cells = []
        for h in headers:
            val = str(row.get(h, "") or "")
            if len(val) > max_col_width:
                val = val[: max_col_width - 1] + "…"
            cells.append(val.ljust(col_widths[h]))
        print("  ".join(cells))

    print(f"  ({len(rows)} fila{'s' if len(rows) != 1 else ''})\n")


# ── CLI básico ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print_report("Score Promedio por Tipo de Contenido", avg_seo_scores_by_type())
    print_report("Costo por Workflow",                  cost_per_workflow())
    print_report("Top 5 Contenidos",                    top_performing_content(5))
    print_report("Eficiencia por Agente",               agent_efficiency())
    print_report("Tasa de Éxito por Tipo",              workflow_success_rate())
