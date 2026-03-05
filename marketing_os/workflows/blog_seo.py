"""
Marketing OS — Blog SEO Workflow (Phase 4)
WashDog — Peluquería Canina, Santiago, Chile

Genera artículos SEO completos sobre cuidado canino orientados al mercado chileno.

Steps:
    1. keyword_research    — Expansión de keywords long-tail para Chile
    2. outline_generation  — Estructura del artículo con título y meta description
    3. article_writing     — Artículo completo en Markdown (800–1.200 palabras)
    4. seo_evaluation      — Score automático de calidad
"""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from workflows.base import WorkflowRunner
from evaluations.scorer import score_content


_BUSINESS_CONTEXT = """
WashDog es una peluquería canina premium en Santiago, Chile.
Servicios: baño completo, corte de pelo, tratamiento antipulgas, deslanado, corte de uñas.
Diferenciadores: atención personalizada, productos premium, agenda online fácil.
Tono de marca: experto, cercano, apasionado por las mascotas.
Audiencia: dueños de perros, clase media-alta, comunas como Providencia, Las Condes, Ñuñoa, La Reina.
"""


def run_blog_seo(
    topic: str,
    target_keyword: str,
    city: str = "Santiago",
    model: str = "claude-sonnet-4-6",
) -> dict:
    """
    Ejecuta el workflow completo de Blog SEO para WashDog.

    Args:
        topic:            Tema del artículo (ej: "cuidado del pelaje en verano")
        target_keyword:   Keyword principal (ej: "peluquería canina Santiago")
        city:             Ciudad objetivo para SEO local (default: Santiago)
        model:            Modelo Claude a usar

    Returns:
        dict con:
            workflow_id, title, meta_description, content,
            keywords (lista expandida), scores (dict de evaluación)
    """
    wf = WorkflowRunner("blog_post", topic, target_keyword, city)

    try:
        # ── Step 1: Keyword research ──────────────────────────────────────────
        keywords_text = wf.run_step(
            step_name  = "keyword_research",
            agent_name = "seo-audit",
            model      = model,
            prompt     = f"""Eres un experto SEO especializado en el mercado chileno.

{_BUSINESS_CONTEXT}

Tu tarea es expandir la keyword principal en variaciones long-tail para Chile.

Keyword principal: {target_keyword}
Tema del artículo: {topic}
Ciudad objetivo:   {city}

Genera 10 keywords relacionadas que incluyan:
- Variaciones long-tail (ej: "peluquería canina económica Providencia")
- Keywords con intención local (ciudad, barrios, "cerca de mí")
- Keywords de baja competencia con buena intención de búsqueda
- Sinónimos chilenos naturales

Formato: lista numerada, una keyword por línea, sin explicaciones adicionales.""",
        )

        # ── Step 2: Outline ───────────────────────────────────────────────────
        outline_raw = wf.run_step(
            step_name  = "outline_generation",
            agent_name = "copywriting",
            model      = model,
            prompt     = f"""Crea el outline SEO para un artículo de blog de WashDog.

{_BUSINESS_CONTEXT}

Datos del artículo:
- Tema:              {topic}
- Keyword principal: {target_keyword}
- Ciudad:            {city}
- Keywords relacionadas:
{keywords_text}

Retorna SOLO un JSON con esta estructura exacta:
{{
  "title": "Título SEO optimizado (máx 60 caracteres, incluye keyword)",
  "meta_description": "Meta description con keyword y CTA (máx 155 caracteres)",
  "headings": [
    "H2: ...",
    "H2: ...",
    "H3: ...",
    "H2: ..."
  ]
}}""",
        )

        # Parsear outline con fallback seguro
        try:
            raw = outline_raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1].lstrip("json").strip()
            outline = json.loads(raw)
        except json.JSONDecodeError:
            outline = {
                "title":            f"{topic} en {city} | WashDog",
                "meta_description": f"Descubre todo sobre {topic}. Servicios de peluquería canina en {city}.",
                "headings":         [],
            }

        title    = outline.get("title",            f"{topic} — WashDog {city}")
        meta     = outline.get("meta_description", "")
        headings = outline.get("headings",         [])

        # ── Step 3: Article writing ───────────────────────────────────────────
        article = wf.run_step(
            step_name  = "article_writing",
            agent_name = "copywriting",
            model      = model,
            prompt     = f"""Escribe un artículo SEO completo para el blog de WashDog.

{_BUSINESS_CONTEXT}

Título:            {title}
Keyword principal: {target_keyword}
Ciudad:            {city}
Estructura:
{chr(10).join(f"  {h}" for h in headings)}

Requisitos obligatorios:
✓ 900–1.200 palabras
✓ Español chileno natural (evitar "vosotros", usar "ustedes")
✓ Keyword principal en: primer párrafo, título H1, meta y 2–3 veces en el cuerpo
✓ Mencionar {city} y barrios como Providencia, Las Condes, Ñuñoa o La Reina cuando sea natural
✓ Al menos 1 CTA al final invitando a reservar con WashDog
✓ Incluir 2–3 sugerencias de links internos (formato: [texto del link](URL relativa))
✓ Tono: experto pero cercano, como un groomer apasionado hablando con el dueño del perro

Formato de entrega: Markdown completo listo para publicar.""",
        )

        # ── Guardar contenido ─────────────────────────────────────────────────
        wf.save_content(
            content_type     = "blog",
            title            = title,
            content          = article,
            meta_description = meta,
        )

        # ── Step 4: Evaluación automática ─────────────────────────────────────
        scores = score_content(
            workflow_id  = wf.workflow_id,
            content      = article,
            content_type = "blog",
            keyword      = target_keyword,
            city         = city,
            model        = "claude-haiku-4-5",  # haiku para ahorrar costo en eval
        )

        wf.complete()

        return {
            "workflow_id":      wf.workflow_id,
            "title":            title,
            "meta_description": meta,
            "content":          article,
            "keywords":         keywords_text,
            "scores":           scores,
        }

    except Exception as e:
        wf.fail(str(e))
        raise
