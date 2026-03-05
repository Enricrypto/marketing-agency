"""
Marketing OS — Seasonal Campaign Workflow (Phase 4)
WashDog — Peluquería Canina, Santiago, Chile

Genera campañas estacionales multi-canal con copy para todos los canales
y proyección de ROI en CLP.

Steps:
    1. campaign_angle      — Concepto creativo, hook emocional y disparadores
    2. multichannel_copy   — Copy para Instagram, WhatsApp, Google Ads, Email
    3. roi_projection      — Proyección de ingresos y ROI en 3 escenarios
    4. campaign_evaluation — Evaluación automática de calidad
"""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from workflows.base import WorkflowRunner
from evaluations.scorer import score_content


_BUSINESS_CONTEXT = """
WashDog es una peluquería canina premium en Santiago, Chile.
Servicios: baño completo, corte de pelo, antipulgas, deslanado, uñas.
Canales activos: Instagram, WhatsApp Business, Google Ads, Email marketing.
Ticket promedio: $25.000–$45.000 CLP según tamaño del perro.
Temporadas clave: verano (dic–feb), vuelta al cole (mar), invierno (jun–ago),
                  Fiestas Patrias (sep), Navidad (dic).
"""


def run_seasonal_campaign(
    campaign_name: str,
    season: str,
    offer: str = "",
    model: str = "claude-sonnet-4-6",
) -> dict:
    """
    Genera una campaña estacional completa multi-canal para WashDog.

    Args:
        campaign_name:  Nombre descriptivo (ej: "Campaña Verano 2026 — Antipulgas")
        season:         Temporada (ej: "verano", "fiestas patrias", "invierno", "navidad")
        offer:          Oferta de la campaña (ej: "2x1 en baño hasta el 28 de febrero")
        model:          Modelo Claude a usar

    Returns:
        dict con:
            workflow_id, campaign_name, angle, copy_assets (dict por canal),
            roi_projection, scores
    """
    wf = WorkflowRunner("seasonal_campaign", campaign_name, season, "Santiago")

    try:
        # ── Step 1: Campaign angle ────────────────────────────────────────────
        angle = wf.run_step(
            step_name  = "campaign_angle",
            agent_name = "marketing-ideas",
            model      = model,
            prompt     = f"""Eres estratega de marketing para WashDog, peluquería canina en Santiago.

{_BUSINESS_CONTEXT}

Desarrolla la estrategia creativa para esta campaña:

Campaña:   {campaign_name}
Temporada: {season}
Oferta:    {offer or 'Definir oferta de temporada atractiva'}

Genera:

1. CONCEPTO CREATIVO (big idea de la campaña — 1 frase memorable)

2. HOOK EMOCIONAL PRINCIPAL
   (por qué los dueños de perros en Santiago van a actuar AHORA, en esta temporada)

3. TRES ÁNGULOS DE CAMPAÑA
   (ej: ángulo humor / ángulo beneficio / ángulo urgencia — cada uno en 2–3 líneas)

4. DISPARADOR DE URGENCIA
   (fecha límite, cupos limitados, precio especial por tiempo limitado)

5. MENSAJE CENTRAL
   (frase de 10–15 palabras que resume la campaña para todos los canales)

Todo en español chileno natural.""",
        )

        # ── Step 2: Multi-channel copy ────────────────────────────────────────
        copy_raw = wf.run_step(
            step_name  = "multichannel_copy",
            agent_name = "social-content",
            model      = model,
            prompt     = f"""Genera el copy completo multi-canal para la campaña de WashDog.

{_BUSINESS_CONTEXT}

Campaña:         {campaign_name}
Temporada:       {season}
Oferta:          {offer or 'Crear oferta de temporada atractiva en CLP'}
Concepto y angle:
{angle}

Retorna SOLO un JSON válido con exactamente esta estructura:
{{
  "instagram_post": "Caption completo para feed de Instagram. Incluir emojis, storytelling, hashtags relevantes (#WashDog #PeluqueriaCanina #Santiago #[temporada]). 150–200 palabras.",
  "instagram_story": "Texto corto y visual para Instagram Stories. Máx 60 palabras. CTA claro (swipe up o DM). Incluir la oferta.",
  "whatsapp_broadcast": "Mensaje de difusión para lista de WhatsApp Business. Tono cercano. Incluir oferta, fecha límite y link de reserva. 80–120 palabras.",
  "google_ads_headline_1": "Headline Google Ads (máx 30 chars con keyword)",
  "google_ads_headline_2": "Headline Google Ads alternativo (máx 30 chars)",
  "google_ads_headline_3": "Headline Google Ads urgencia (máx 30 chars)",
  "google_ads_description_1": "Description Google Ads con beneficio (máx 90 chars)",
  "google_ads_description_2": "Description Google Ads con oferta y CTA (máx 90 chars)",
  "email_subject": "Asunto de email (máx 50 chars, genera apertura)",
  "email_preview_text": "Preview text del email (máx 90 chars, complementa el asunto)",
  "email_body_intro": "Párrafo de apertura del email (2–3 oraciones, gancho emocional + oferta)"
}}

Todo en español chileno. Incluir la oferta: {offer or 'oferta de temporada atractiva'}.""",
        )

        # Parsear copy_assets con fallback
        try:
            raw = copy_raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1].lstrip("json").strip()
            copy_assets = json.loads(raw)
        except json.JSONDecodeError:
            copy_assets = {"raw_copy": copy_raw}

        # ── Step 3: ROI projection ────────────────────────────────────────────
        roi_projection = wf.run_step(
            step_name  = "roi_projection",
            agent_name = "analytics-tracking",
            model      = model,
            prompt     = f"""Genera una proyección de ROI para esta campaña de WashDog.

{_BUSINESS_CONTEXT}

Campaña: {campaign_name}
Oferta:  {offer or 'Descuento de temporada'}

SUPUESTOS BASE (peluquería canina típica en Santiago):
- Ticket promedio:          $30.000 CLP
- Margen bruto estimado:    60% del ticket
- Costo campaña digital:    $50.000–$150.000 CLP (dependiendo del canal)
- Capacidad adicional:      hasta 15 turnos extra/semana en temporada

Proyecta la siguiente tabla Markdown con 3 escenarios:

| Métrica | Conservador | Realista | Optimista |
|---------|-------------|----------|-----------|
| Turnos extra/semana | 8 | 18 | 30 |
| Duración campaña | 4 semanas | 4 semanas | 4 semanas |
| Turnos extra totales | ... | ... | ... |
| Ingresos adicionales (CLP) | ... | ... | ... |
| Costo campaña (CLP) | $80.000 | $100.000 | $120.000 |
| Ganancia neta (CLP) | ... | ... | ... |
| ROI % | ... | ... | ... |
| Payback (semanas) | ... | ... | ... |

Luego agrega 3 recomendaciones concretas para maximizar ROI.
Todo en español, cifras en CLP.""",
        )

        # ── Armar contenido completo para almacenar ───────────────────────────
        full_content = (
            f"# {campaign_name}\n\n"
            f"## Concepto y Ángulo Creativo\n{angle}\n\n"
            f"## Copy Multi-Canal\n{copy_raw}\n\n"
            f"## Proyección de ROI\n{roi_projection}"
        )

        wf.save_content(
            content_type = "campaign",
            title        = campaign_name,
            content      = full_content,
        )

        # ── Evaluación automática ─────────────────────────────────────────────
        scores = score_content(
            workflow_id  = wf.workflow_id,
            content      = full_content,
            content_type = "campaign",
            keyword      = season,
            city         = "Santiago",
            model        = "claude-haiku-4-5",
        )

        wf.complete()

        return {
            "workflow_id":   wf.workflow_id,
            "campaign_name": campaign_name,
            "angle":         angle,
            "copy_assets":   copy_assets,
            "roi_projection": roi_projection,
            "scores":        scores,
        }

    except Exception as e:
        wf.fail(str(e))
        raise
