"""
Marketing OS — Evaluation Engine (Phase 4)

Evalúa automáticamente el contenido generado para WashDog usando Claude.
Scores: SEO, Readabilidad, Conversión, Relevancia Local.
Guarda resultados en la tabla `evaluations`.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from db import insert_row
from runner import call_claude


# ── Pesos del overall_score ───────────────────────────────────────────────────
_WEIGHTS = {
    "seo_score":             0.30,
    "readability_score":     0.20,
    "conversion_score":      0.30,
    "local_relevance_score": 0.20,
}

# Criterios por tipo de contenido (añadidos al prompt)
_TYPE_HINTS = {
    "blog": (
        "Es un artículo de blog SEO. Prioriza keyword density, estructura de headings "
        "H2/H3, meta description y presencia de links internos sugeridos."
    ),
    "landing": (
        "Es una landing page de servicio. Prioriza CTA claro, propuesta de valor arriba "
        "del fold, señales de confianza y estructura de conversión."
    ),
    "campaign": (
        "Es una campaña estacional multi-canal. Prioriza urgencia, oferta clara, "
        "coherencia de mensaje entre canales y proyección de ROI."
    ),
    "ad_copy": (
        "Es copy de anuncios pagados. Prioriza headline impactante, beneficio en "
        "la descripción y match con la intención de búsqueda."
    ),
}


def score_content(
    workflow_id: str,
    content: str,
    content_type: str,
    keyword: str = "",
    city: str = "Santiago",
    model: str = "claude-haiku-4-5",
) -> dict:
    """
    Evalúa un contenido generado y guarda los scores en la tabla `evaluations`.

    Args:
        workflow_id:   ID del workflow al que pertenece el contenido.
        content:       Texto completo a evaluar (se trunca a 3.000 chars).
        content_type:  "blog" | "landing" | "campaign" | "ad_copy"
        keyword:       Keyword principal objetivo.
        city:          Ciudad objetivo (para relevancia local).
        model:         Modelo Claude (haiku por defecto para minimizar costo).

    Returns:
        dict con seo_score, readability_score, conversion_score,
        local_relevance_score, overall_score, notes.
    """
    print(f"[evaluator] Evaluando {content_type} (keyword: '{keyword}', ciudad: {city})...")

    type_hint = _TYPE_HINTS.get(content_type, "")

    prompt = f"""Eres un evaluador experto de contenido de marketing digital para Chile.

CONTEXTO DEL NEGOCIO:
WashDog es una peluquería canina premium en Santiago, Chile.
Audiencia: dueños de mascotas, clase media-alta, Santiago Metropolitana.

TIPO DE CONTENIDO: {content_type}
{type_hint}

KEYWORD OBJETIVO: {keyword or '(no especificada)'}
CIUDAD OBJETIVO: {city}

CRITERIOS DE EVALUACIÓN (0–100 cada score):

seo_score:
  - Keyword en título, primer párrafo y headings
  - Densidad de keyword: 1–3% (más o menos = penalizar)
  - Meta description presente y dentro de 155 chars
  - Estructura de headings H2/H3 coherente
  - Mención de ciudad/barrios para SEO local

readability_score:
  - Frases cortas y párrafos de máx 4 líneas
  - Vocabulario apropiado para dueños de mascotas (no jerga técnica)
  - Tono amigable y cercano (como habla un groomer experto)
  - Uso de listas y viñetas para facilitar lectura

conversion_score:
  - CTA claro y visible (mínimo 1)
  - Beneficios explícitos sobre características
  - Urgencia o escasez presente cuando aplica
  - Oferta o propuesta de valor clara

local_relevance_score:
  - Menciones de Chile / Santiago / comunas específicas
  - Precios en CLP (o referencia a precios locales)
  - Tono culturalmente apropiado para Chile
  - Referencias a temporadas o contexto local (verano/invierno chileno)

CONTENIDO A EVALUAR:
---
{content[:3_000]}
---

Retorna SOLO un JSON válido con exactamente estas claves:
{{
  "seo_score": <int 0-100>,
  "readability_score": <int 0-100>,
  "conversion_score": <int 0-100>,
  "local_relevance_score": <int 0-100>,
  "notes": "<observaciones concretas en 1-2 oraciones>"
}}"""

    # Llamar a Claude para obtener scores
    try:
        result = call_claude(prompt, model=model)
        raw    = result["text"].strip()
        # Limpiar markdown code fences si vienen en la respuesta
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        scores = json.loads(raw.strip())
    except (json.JSONDecodeError, Exception) as e:
        print(f"[evaluator] ⚠ No se pudo parsear scores: {e}")
        scores = {
            "seo_score":             50,
            "readability_score":     50,
            "conversion_score":      50,
            "local_relevance_score": 50,
            "notes":                 "Evaluación automática no disponible.",
        }

    # Extraer valores con defaults seguros
    seo   = int(scores.get("seo_score",             0))
    read  = int(scores.get("readability_score",     0))
    conv  = int(scores.get("conversion_score",      0))
    local = int(scores.get("local_relevance_score", 0))
    notes = scores.get("notes", "")

    # Calcular overall ponderado
    overall = round(
        seo   * _WEIGHTS["seo_score"]
        + read  * _WEIGHTS["readability_score"]
        + conv  * _WEIGHTS["conversion_score"]
        + local * _WEIGHTS["local_relevance_score"],
        1,
    )

    # Guardar en base de datos
    insert_row("evaluations", {
        "id":                    str(uuid.uuid4()),
        "workflow_id":           workflow_id,
        "seo_score":             seo,
        "readability_score":     read,
        "conversion_score":      conv,
        "local_relevance_score": local,
        "overall_score":         overall,
        "notes":                 notes,
        "created_at":            datetime.now().isoformat(),
    })

    # Barra visual de calidad
    bar = "█" * (overall // 10) + "░" * (10 - overall // 10)
    print(
        f"[evaluator] [{bar}] {overall}/100  "
        f"SEO:{seo}  Read:{read}  Conv:{conv}  Local:{local}"
    )
    if notes:
        print(f"[evaluator] Notas: {notes}")

    return {
        "seo_score":             seo,
        "readability_score":     read,
        "conversion_score":      conv,
        "local_relevance_score": local,
        "overall_score":         overall,
        "notes":                 notes,
    }
