#!/usr/bin/env python3
"""
Marketing OS — Scheduler (Phase 5 / Phase 6)
Ejecuta agentes según el calendario semanal definido en context/schedule_config.json.

Uso:
    python scheduler.py                  → Ejecutar agentes de hoy
    python scheduler.py --dry-run        → Simular sin gastar tokens
    python scheduler.py --day thursday   → Ejecutar día específico
    python scheduler.py --run-week       → Ejecutar semana completa (L–V) con gates
    python scheduler.py --budget-report  → Reporte de presupuesto mensual
    python scheduler.py --preview-week   → Ver qué agentes corren cada día
"""

import os
import json
import argparse
from datetime import datetime, date
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

# ──────────────────────────────────────────────
# CONFIGURACIÓN
# ──────────────────────────────────────────────

BASE_DIR    = Path(__file__).parent
CONTEXT_DIR = BASE_DIR / "context"
LOGS_DIR    = BASE_DIR / "outputs" / "logs"

DAYS_ES = {
    "monday": "lunes", "tuesday": "martes", "wednesday": "miércoles",
    "thursday": "jueves", "friday": "viernes", "saturday": "sábado", "sunday": "domingo",
}
DAYS_EN = {v: k for k, v in DAYS_ES.items()}

# Mapeo Python weekday() → nombre en inglés
WEEKDAY_MAP = {0: "monday", 1: "tuesday", 2: "wednesday", 3: "thursday",
               4: "friday", 5: "saturday", 6: "sunday"}


# ──────────────────────────────────────────────
# CARGA DE CONFIGURACIÓN
# ──────────────────────────────────────────────

def load_schedule_config() -> dict:
    """Carga context/schedule_config.json."""
    path = CONTEXT_DIR / "schedule_config.json"
    if not path.exists():
        raise FileNotFoundError(f"[scheduler] schedule_config.json no encontrado: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ──────────────────────────────────────────────
# RESOLUCIÓN DE AGENDA
# ──────────────────────────────────────────────

def get_week_of_month(d: date) -> int:
    """Retorna la semana del mes (1–5) para una fecha dada."""
    return (d.day - 1) // 7 + 1


def apply_budget_policy(agents: list[dict], spent_pct: float,
                        model_defaults: dict) -> list[dict]:
    """
    Aplica la política de presupuesto dinámico:
    - 80–90% gastado → downgrade modelos "important" y "support" a haiku
    - 90–100% gastado → eliminar agentes de prioridad "support"
    - >100% gastado   → bloquear todo (manejado antes de llamar esta función)

    Args:
        agents:        Lista de agentes del día.
        spent_pct:     Porcentaje del presupuesto mensual ya gastado (0–100).
        model_defaults: Modelos por prioridad desde schedule_config.json.

    Returns:
        Lista de agentes con modelos y prioridades ajustados.
    """
    haiku = "claude-haiku-4-5"
    result = []

    for a in agents:
        a = dict(a)  # copia para no mutar el original

        if spent_pct >= 90:
            # Prioridad crítica: downgrade a sonnet. Support: omitir.
            if a["priority"] == "support":
                print(f"[scheduler] Presupuesto >90% — omitiendo agente de apoyo: {a['agent']}")
                continue
            if a["priority"] == "important":
                a["model"] = haiku
                print(f"[scheduler] Presupuesto >90% — downgrade a haiku: {a['agent']}")
            if a["priority"] == "critical":
                a["model"] = model_defaults.get("important", "claude-sonnet-4-6")
                print(f"[scheduler] Presupuesto >90% — downgrade a sonnet: {a['agent']}")

        elif spent_pct >= 80:
            # Downgrade support e important a haiku
            if a["priority"] in ("support", "important"):
                a["model"] = haiku
                print(f"[scheduler] Presupuesto >80% — downgrade a haiku: {a['agent']}")

        result.append(a)

    return result


def agents_for_day(day_name: str, config: dict, ref_date: date | None = None) -> list[dict]:
    """
    Retorna lista de agentes programados para el día dado.

    Args:
        day_name:  Día en inglés (monday, tuesday, …).
        config:    Contenido de schedule_config.json.
        ref_date:  Fecha de referencia para calcular semana del mes (default: hoy).

    Returns:
        Lista de dicts con agent, task_template, output_type, model, batch_size.
    """
    if ref_date is None:
        ref_date = date.today()

    week_num = get_week_of_month(ref_date)
    schedule = config.get("schedule", {})
    model_defaults = config.get("model_defaults", {})
    result = []

    for agent_name, cfg in schedule.items():
        frequency = cfg.get("frequency", "on-demand")
        days      = cfg.get("days", [])
        priority  = cfg.get("priority", "support")

        if day_name not in days:
            continue

        # Verificar semana del mes para frecuencia bi-semanal y mensual
        if frequency == "biweekly":
            allowed_weeks = cfg.get("weeks", [1, 3])
            if week_num not in allowed_weeks:
                continue
        elif frequency == "monthly":
            allowed_weeks = cfg.get("weeks", [1])
            if week_num not in allowed_weeks:
                continue
        elif frequency == "on-demand":
            continue  # Los on-demand no se programan automáticamente

        batch_size = cfg.get("batch_size", 1)
        task_template = cfg.get("task_template", "Ejecutar tarea del agente.")
        task_description = task_template.replace("{batch_size}", str(batch_size))

        result.append({
            "agent": agent_name,
            "priority": priority,
            "frequency": frequency,
            "task_description": task_description,
            "output_type": cfg.get("output_type", "doc"),
            "model": model_defaults.get(priority, "claude-sonnet-4-6"),
            "batch_size": batch_size,
        })

    # Ordenar: critical primero, luego important, luego support
    priority_order = {"critical": 0, "important": 1, "support": 2}
    result.sort(key=lambda x: priority_order.get(x["priority"], 9))
    return result


# ──────────────────────────────────────────────
# ESTIMACIÓN DE COSTO (sin llamar a Claude)
# ──────────────────────────────────────────────

# Tokens estimados promedio por llamada según modelo y tipo de agente
_AVG_TOKENS: dict[str, tuple[int, int]] = {
    "claude-opus-4-6":   (3000, 1500),
    "claude-sonnet-4-6": (3000, 1500),
    "claude-haiku-4-5":  (3000, 1000),
}

_MODEL_PRICING: dict[str, tuple[float, float]] = {
    "claude-opus-4-6":   (15.00, 75.00),
    "claude-sonnet-4-6": ( 3.00, 15.00),
    "claude-haiku-4-5":  ( 0.25,  1.25),
}


def estimate_call_cost(model: str) -> float:
    """Estima el costo USD de una llamada típica al modelo dado."""
    tokens_in, tokens_out = _AVG_TOKENS.get(model, (3000, 1500))
    price_in, price_out   = _MODEL_PRICING.get(model, (15.00, 75.00))
    return (tokens_in * price_in + tokens_out * price_out) / 1_000_000


# ──────────────────────────────────────────────
# REPORTE DE PRESUPUESTO
# ──────────────────────────────────────────────

def load_monthly_cost() -> tuple[float, int]:
    """
    Lee runner.log y suma el costo del mes actual.
    Retorna (costo_total_usd, número_de_ejecuciones).
    """
    log_path = LOGS_DIR / "runner.log"
    if not log_path.exists():
        return 0.0, 0

    now = datetime.now()
    total_cost = 0.0
    count = 0

    with open(log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                ts = datetime.fromisoformat(entry.get("timestamp", ""))
                if ts.year == now.year and ts.month == now.month:
                    total_cost += entry.get("cost_usd", 0.0)
                    count += 1
            except (json.JSONDecodeError, ValueError):
                continue

    return total_cost, count


def print_budget_report(config: dict) -> None:
    """Imprime un reporte del uso del presupuesto mensual."""
    budget_cfg   = config.get("budget", {})
    monthly_usd  = budget_cfg.get("monthly_usd", 20.0)
    weekly_usd   = budget_cfg.get("weekly_budget_usd", 5.0)
    alert_pct    = budget_cfg.get("alert_threshold_pct", 80)

    spent_usd, runs = load_monthly_cost()
    remaining   = monthly_usd - spent_usd
    used_pct    = (spent_usd / monthly_usd * 100) if monthly_usd > 0 else 0
    week_num    = get_week_of_month(date.today())

    print("\n── Reporte de Presupuesto — Marketing OS ─────────────────")
    print(f"  Mes           : {datetime.now().strftime('%B %Y')}")
    print(f"  Semana        : {week_num} / 4")
    print(f"  Ejecuciones   : {runs} este mes")
    print(f"  Gastado       : ${spent_usd:.4f} USD  ({used_pct:.1f}%)")
    print(f"  Restante      : ${remaining:.4f} USD")
    print(f"  Presupuesto   : ${monthly_usd:.2f} USD/mes  (${weekly_usd:.2f} USD/semana)")

    if used_pct >= 100:
        print(f"\n  ⚠️  PRESUPUESTO AGOTADO — pausar ejecuciones hasta el próximo mes.")
    elif used_pct >= alert_pct:
        print(f"\n  ⚠️  Alerta: uso supera el {alert_pct}% del presupuesto mensual.")
    else:
        print(f"\n  ✓  Dentro del presupuesto.")
    print()


# ──────────────────────────────────────────────
# PREVIEW SEMANAL
# ──────────────────────────────────────────────

def print_week_preview(config: dict) -> None:
    """Imprime qué agentes corren cada día de la semana actual."""
    today     = date.today()
    week_num  = get_week_of_month(today)
    all_days  = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    print(f"\n── Preview Semanal — Semana {week_num} del mes ────────────────────")
    total_cost = 0.0

    for day in all_days:
        agents = agents_for_day(day, config, ref_date=today)
        marker = " ← HOY" if WEEKDAY_MAP[today.weekday()] == day else ""
        if agents:
            day_cost = sum(estimate_call_cost(a["model"]) for a in agents)
            total_cost += day_cost
            print(f"\n  {DAYS_ES[day].upper()}{marker}  (~${day_cost:.4f} USD)")
            for a in agents:
                cost = estimate_call_cost(a["model"])
                print(f"    [{a['priority']:9s}] {a['agent']:<28} {a['model']:<22} ~${cost:.4f}")
        else:
            print(f"\n  {DAYS_ES[day].upper()}{marker}  — sin tareas programadas")

    print(f"\n  Costo estimado semana: ~${total_cost:.4f} USD")
    print(f"  Presupuesto semanal  : ${config.get('budget', {}).get('weekly_budget_usd', 5.0):.2f} USD")
    print()


# ──────────────────────────────────────────────
# EJECUCIÓN DE AGENTES
# ──────────────────────────────────────────────

def run_scheduled_agents(agents: list[dict], dry_run: bool = False,
                         spent_usd: float = 0.0, monthly_usd: float = 20.0) -> list[dict]:
    """
    Ejecuta la lista de agentes del día con gate de presupuesto por llamada.

    Antes de cada agente verifica que el gasto acumulado no supere el presupuesto.
    Si lo supera en medio del día, detiene la ejecución y reporta cuántos se completaron.

    Args:
        agents:      Lista de agentes del día.
        dry_run:     Si True, simula sin llamar a Claude.
        spent_usd:   Gasto acumulado del mes al inicio del día.
        monthly_usd: Presupuesto mensual máximo.

    Returns:
        Lista de resultados por agente ejecutado.
    """
    from runner import run_agent

    results = []
    accumulated = spent_usd  # rastrear gasto en tiempo real durante el día

    for a in agents:
        # Gate de presupuesto por llamada: parar si ya superamos el límite
        if accumulated >= monthly_usd and not dry_run:
            print(f"\n[scheduler] Presupuesto agotado durante ejecución del día.")
            print(f"[scheduler] Agente omitido: {a['agent']} — ${accumulated:.4f} / ${monthly_usd:.2f} USD")
            break

        print(f"\n{'[DRY-RUN] ' if dry_run else ''}── {a['agent']}  [{a['priority']}]  {a['model']}")

        if dry_run:
            call_cost = estimate_call_cost(a["model"])
            result = {
                "agent": a["agent"],
                "output_type": a["output_type"],
                "saved_path": "[dry-run]",
                "google": None,
                "content": "[dry-run — contenido simulado]",
                "tokens": {"input": 3000, "output": 1500, "cost_usd": call_cost},
            }
            accumulated += call_cost
            print(f"  Tarea     : {a['task_description'][:80]}")
            print(f"  Costo est.: ~${call_cost:.4f} USD  |  Acumulado: ~${accumulated:.4f} USD")
        else:
            task_input = {
                "agent":            a["agent"],
                "task_description": a["task_description"],
                "output_type":      a["output_type"],
            }
            result = run_agent(a["agent"], task_input, model=a["model"])
            call_cost = (result.get("tokens") or {}).get("cost_usd", 0.0)
            accumulated += call_cost

        results.append(result)

    return results


def run_full_week(config: dict, dry_run: bool = False) -> dict:
    """
    Ejecuta todos los días programados de la semana actual (lunes a domingo)
    con gate de presupuesto dinámico entre días.

    Después de cada día verifica el gasto acumulado y aplica política de modelo
    para los días siguientes si el uso supera umbrales de alerta.

    Returns:
        Dict con resultados por día y resumen de costo total.
    """
    all_days     = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    today        = date.today()
    budget_cfg   = config.get("budget", {})
    monthly_usd  = budget_cfg.get("monthly_usd", 20.0)
    model_defaults = config.get("model_defaults", {})

    weekly_results: dict = {}
    spent_usd, _ = load_monthly_cost()

    print(f"\n── Ejecución Semanal {'[DRY-RUN] ' if dry_run else ''}────────────────────────────")
    print(f"  Semana    : {get_week_of_month(today)} / 4")
    print(f"  Inicio    : ${spent_usd:.4f} USD gastado este mes")
    print(f"  Límite    : ${monthly_usd:.2f} USD/mes")
    print()

    for day in all_days:
        agents = agents_for_day(day, config, ref_date=today)
        if not agents:
            continue

        # Calcular % gastado para aplicar política de presupuesto
        spent_pct = (spent_usd / monthly_usd * 100) if monthly_usd > 0 else 0

        if spent_pct >= 100 and not dry_run:
            print(f"\n[scheduler] Presupuesto agotado — deteniendo semana en {DAYS_ES[day]}.")
            break

        # Aplicar degradación de modelos si corresponde
        agents = apply_budget_policy(agents, spent_pct, model_defaults)
        if not agents:
            print(f"\n  {DAYS_ES[day].upper()} — todos los agentes omitidos por presupuesto.")
            continue

        day_cost_est = sum(estimate_call_cost(a["model"]) for a in agents)
        print(f"\n── {DAYS_ES[day].upper()}  ({len(agents)} agente{'s' if len(agents) > 1 else ''}"
              f"  ~${day_cost_est:.4f} USD) ────────────────")

        results = run_scheduled_agents(agents, dry_run=dry_run,
                                       spent_usd=spent_usd, monthly_usd=monthly_usd)

        day_actual_cost = sum((r.get("tokens") or {}).get("cost_usd", 0.0) for r in results)
        spent_usd += day_actual_cost
        weekly_results[day] = {"agents": len(results), "cost_usd": day_actual_cost, "results": results}

        print(f"  Día completado: ${day_actual_cost:.4f} USD  |  Total mes: ${spent_usd:.4f} USD")

    total_week_cost = sum(d["cost_usd"] for d in weekly_results.values())
    print(f"\n── Semana completada ──────────────────────────────────────")
    print(f"  Días ejecutados  : {len(weekly_results)}")
    print(f"  Costo semana     : ${total_week_cost:.4f} USD")
    print(f"  Total mes        : ${spent_usd:.4f} / ${monthly_usd:.2f} USD")
    print()

    return {"days": weekly_results, "total_cost_usd": total_week_cost}


# ──────────────────────────────────────────────
# CLI ENTRY POINT
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Marketing OS Scheduler — Ejecuta agentes según agenda semanal"
    )
    parser.add_argument(
        "--day", default=None,
        help="Día a ejecutar en inglés (monday…sunday). Default: hoy."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Simula la ejecución sin llamar a Claude ni gastar tokens."
    )
    parser.add_argument(
        "--budget-report", action="store_true",
        help="Muestra el reporte de uso del presupuesto mensual."
    )
    parser.add_argument(
        "--preview-week", action="store_true",
        help="Muestra qué agentes corren cada día de la semana actual."
    )
    parser.add_argument(
        "--run-week", action="store_true",
        help="Ejecuta todos los días de la semana (L–D) con gates de presupuesto automáticos."
    )

    args = parser.parse_args()
    config = load_schedule_config()

    # Modo reporte de presupuesto
    if args.budget_report:
        print_budget_report(config)
        return

    # Modo preview semanal
    if args.preview_week:
        print_week_preview(config)
        return

    # Modo semana completa
    if args.run_week:
        run_full_week(config, dry_run=args.dry_run)
        return

    # Resolver día a ejecutar
    today_en = WEEKDAY_MAP[date.today().weekday()]
    day_name = (args.day or today_en).lower()

    # Aceptar nombre en español también
    if day_name in DAYS_EN:
        day_name = DAYS_EN[day_name]

    if day_name not in WEEKDAY_MAP.values():
        print(f"[error] Día no válido: '{day_name}'")
        print(f"Días válidos: {', '.join(WEEKDAY_MAP.values())}")
        raise SystemExit(1)

    # Verificar presupuesto antes de ejecutar
    budget_cfg  = config.get("budget", {})
    monthly_usd = budget_cfg.get("monthly_usd", 20.0)
    alert_pct   = budget_cfg.get("alert_threshold_pct", 80)
    spent_usd, _ = load_monthly_cost()

    if spent_usd >= monthly_usd and not args.dry_run:
        print(f"[scheduler] ⚠️  Presupuesto mensual agotado (${spent_usd:.4f} / ${monthly_usd:.2f}).")
        print("[scheduler] Usa --dry-run para simular o ajusta el presupuesto en schedule_config.json.")
        raise SystemExit(1)

    if (spent_usd / monthly_usd * 100) >= alert_pct and not args.dry_run:
        print(f"[scheduler] ⚠️  Alerta de presupuesto: {spent_usd:.4f} / {monthly_usd:.2f} USD gastado.")

    # Obtener agentes del día y aplicar política de presupuesto dinámico
    agents = agents_for_day(day_name, config)
    day_es = DAYS_ES.get(day_name, day_name)

    if not agents:
        print(f"[scheduler] No hay agentes programados para el {day_es}.")
        return

    spent_pct = (spent_usd / monthly_usd * 100) if monthly_usd > 0 else 0
    model_defaults = config.get("model_defaults", {})
    agents = apply_budget_policy(agents, spent_pct, model_defaults)

    if not agents:
        print(f"[scheduler] Todos los agentes de {day_es} omitidos por política de presupuesto.")
        return

    estimated_total = sum(estimate_call_cost(a["model"]) for a in agents)
    mode_label = "[DRY-RUN] " if args.dry_run else ""
    print(f"\n{mode_label}── Scheduler — {day_es.upper()} ──────────────────────────────")
    print(f"  Agentes : {len(agents)}")
    print(f"  Costo   : ~${estimated_total:.4f} USD estimado")
    print(f"  Gastado : ${spent_usd:.4f} / ${monthly_usd:.2f} USD este mes")
    print()

    results = run_scheduled_agents(agents, dry_run=args.dry_run,
                                   spent_usd=spent_usd, monthly_usd=monthly_usd)

    # Resumen final
    actual_cost = sum((r.get("tokens") or {}).get("cost_usd", 0.0) for r in results)
    print(f"\n── Resumen ────────────────────────────────────────────────")
    print(f"  Agentes ejecutados : {len(results)}")
    print(f"  Costo real         : ${actual_cost:.4f} USD")
    print(f"  Total mes          : ${spent_usd + actual_cost:.4f} / ${monthly_usd:.2f} USD")
    print()


if __name__ == "__main__":
    main()
