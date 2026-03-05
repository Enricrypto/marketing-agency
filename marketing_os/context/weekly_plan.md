# Phase 6 — Plan de Ejecución Semanal

> Referencia operacional para el Marketing OS.
> El scheduler lee `schedule_config.json` y ejecuta automáticamente con `scheduler.py`.

---

## Calendario Semanal — Semana 1 y 3 del mes

| Día | Agentes | Prioridad | Modelo | Batch | Output | Costo est. |
|-----|---------|-----------|--------|-------|--------|-----------|
| **Lunes** | analytics-tracking | critical | opus-4-6 | 1 | Sheet | ~$0.16 |
| | seo-audit | important | sonnet-4-6 | 1 | Sheet | ~$0.03 |
| **Martes** | copywriting | critical | opus-4-6 | 2 posts | Doc | ~$0.16 |
| **Miércoles** | social-content | critical | opus-4-6 | 5 posts | Doc | ~$0.16 |
| **Jueves** | paid-ads | critical | opus-4-6 | 3 anuncios | Sheet | ~$0.16 |
| | page-cro | important | sonnet-4-6 | 1 | Doc | ~$0.03 |
| **Viernes** | email-sequence | critical | opus-4-6 | 1 campaña | Doc | ~$0.16 |
| **Sábado** | marketing-ideas | support | haiku-4-5 | 5 ideas | Sheet | ~$0.002 |
| | onboarding-cro | support | haiku-4-5 | 1 | Doc | ~$0.002 |
| **Domingo** | — Human Review — | — | — | — | — | $0 |

**Costo estimado semana 1/3: ~$0.85 USD**

---

## Calendario Semanal — Semana 2 y 4 del mes

| Día | Agentes | Prioridad | Modelo | Batch | Output | Costo est. |
|-----|---------|-----------|--------|-------|--------|-----------|
| **Lunes** | analytics-tracking | critical | opus-4-6 | 1 | Sheet | ~$0.16 |
| **Martes** | copywriting | critical | opus-4-6 | 2 posts | Doc | ~$0.16 |
| | schema-markup | important | sonnet-4-6 | 1 | Doc | ~$0.03 |
| **Miércoles** | social-content | critical | opus-4-6 | 5 posts | Doc | ~$0.16 |
| | popup-cro | important | sonnet-4-6 | 1 | Doc | ~$0.03 |
| **Jueves** | paid-ads | critical | opus-4-6 | 3 anuncios | Sheet | ~$0.16 |
| | form-cro | important | sonnet-4-6 | 1 | Doc | ~$0.03 |
| **Viernes** | email-sequence | critical | opus-4-6 | 1 campaña | Doc | ~$0.16 |
| | ab-test-setup | important | sonnet-4-6 | 1 | Doc | ~$0.03 |
| **Sábado** | launch-strategy | support | haiku-4-5 | 1 | Doc | ~$0.002 |
| **Domingo** | — Human Review — | — | — | — | — | $0 |

**Costo estimado semana 2/4: ~$0.95 USD**

---

## Costo Mensual Estimado

| Concepto | Costo USD |
|----------|-----------|
| 2× semana 1/3 (~$0.85) | ~$1.70 |
| 2× semana 2/4 (~$0.95) | ~$1.90 |
| **Total mensual estimado** | **~$3.60 USD** |
| Presupuesto disponible | $20.00 USD |
| Margen restante | ~$16.40 USD |

> Este margen permite agregar agentes on-demand (competitor-alternatives, referral-program,
> pricing-strategy) sin preocuparse por el límite.

---

## Política de Presupuesto Dinámico

El scheduler aplica automáticamente la siguiente política según el % del presupuesto mensual gastado:

| % gastado | Acción automática |
|-----------|-------------------|
| 0–80% | Ejecución normal con modelos configurados |
| 80–90% | Downgrade a `claude-haiku-4-5` para agentes `support` e `important` |
| 90–100% | Omitir agentes `support`, downgrade a sonnet para `critical` |
| >100% | Bloquear toda ejecución hasta el próximo mes |

---

## Snippet Python — Ejecución Semanal Automatizada

Listo para copiar en cualquier script, cron job o automatización:

```python
# ── Marketing OS — Ejecución Semanal Automatizada ──────────────────────────
# Ejecutar desde: /marketing_os/
# Requiere: .venv activo, ANTHROPIC_API_KEY en .env

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from scheduler import load_schedule_config, run_full_week

# Cargar configuración
config = load_schedule_config()

# Modo real (gasta tokens)
run_full_week(config, dry_run=False)

# Modo simulación (no gasta tokens — útil para verificar agenda)
# run_full_week(config, dry_run=True)
```

---

## Snippet Python — Ejecutar Día Específico

```python
from datetime import date
from scheduler import (
    load_schedule_config, agents_for_day, apply_budget_policy,
    run_scheduled_agents, load_monthly_cost, WEEKDAY_MAP
)

config       = load_schedule_config()
today        = date.today()
day_name     = WEEKDAY_MAP[today.weekday()]   # ej: "tuesday"
spent_usd, _ = load_monthly_cost()
monthly_usd  = config["budget"]["monthly_usd"]
spent_pct    = (spent_usd / monthly_usd * 100)

# Obtener y filtrar agentes del día según presupuesto
agents = agents_for_day(day_name, config, ref_date=today)
agents = apply_budget_policy(agents, spent_pct, config["model_defaults"])

# Ejecutar (dry_run=True para simular)
results = run_scheduled_agents(agents, dry_run=False,
                                spent_usd=spent_usd, monthly_usd=monthly_usd)

for r in results:
    print(f"  ✓ {r['agent']}  →  {r.get('saved_path', '')}")
    if r.get("google"):
        print(f"    Google: {r['google']['url']}")
```

---

## Snippet Python — Agente On-Demand

Para ejecutar cualquier agente fuera del calendario (sin tocar scheduler.py):

```python
from runner import run_agent

resultado = run_agent(
    agent_name  = "competitor-alternatives",
    task_input  = {
        "task_description": "Crea estructura para página vs competidor principal en fitness Santiago",
        "output_type": "doc",
        "title": "Alternativas a [Competidor] — Fitness Santiago",
    },
    model = "claude-sonnet-4-6",   # sonnet para ahorrar vs opus
)

print(resultado["content"])
print(f"Guardado en: {resultado['saved_path']}")
print(f"Costo: ${resultado['tokens']['cost_usd']:.4f} USD")
```

---

## Comandos de Referencia

```bash
cd marketing_os && source .venv/bin/activate

# Ver plan de la semana
python scheduler.py --preview-week

# Simular semana completa (sin gastar tokens)
python scheduler.py --run-week --dry-run

# Ejecutar semana completa (real)
python scheduler.py --run-week

# Ejecutar solo hoy
python scheduler.py

# Ejecutar día específico
python scheduler.py --day tuesday

# Ver presupuesto gastado
python scheduler.py --budget-report

# Ejecutar agente único desde runner
python runner.py --agent social-content \
  --task "5 posts Instagram para gym en Santiago esta semana"
```

---

## Human Review Loop (Domingo)

1. Abrir Google Drive → carpeta `MarketingOS/`
2. Revisar `docs/` → aprobar o editar posts, copy, emails
3. Revisar `sheets/` → validar métricas, keywords, anuncios
4. Publicar contenido aprobado en los canales correspondientes
5. Anotar feedback en `context/business_context.md` para mejorar próximas ejecuciones
