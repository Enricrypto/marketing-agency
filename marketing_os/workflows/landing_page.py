"""
Marketing OS — Landing Page Workflow (Phase 4)
WashDog — Peluquería Canina, Santiago, Chile

Genera landing pages de servicios optimizadas para conversión.

Steps:
    1. market_positioning  — Propuesta de valor, objeciones y señales de confianza
    2. copy_generation     — Copy completo de la página en Markdown
    3. conversion_scoring  — Evaluación automática de calidad
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from workflows.base import WorkflowRunner
from evaluations.scorer import score_content


_BUSINESS_CONTEXT = """
WashDog es una peluquería canina premium en Santiago, Chile.
Servicios disponibles:
  - Baño completo (incluye secado y perfume)
  - Corte de pelo canino (todas las razas)
  - Tratamiento antipulgas y garrapatas
  - Deslanado (doble capa)
  - Corte y lima de uñas
Diferenciadores: atención personalizada, productos premium hipoalergénicos, agenda online.
CTA principal: "Reserva tu hora" (WhatsApp o formulario web).
Precio promedio: $25.000–$45.000 CLP según tamaño del perro.
"""


def run_landing_page(
    service: str,
    location: str,
    promotion: str = "",
    model: str = "claude-sonnet-4-6",
) -> dict:
    """
    Genera una landing page de servicio para WashDog.

    Args:
        service:    Nombre del servicio (ej: "baño antipulgas", "corte de pelo canino")
        location:   Ubicación o comuna (ej: "Providencia", "Las Condes")
        promotion:  Promoción activa (ej: "20% descuento primera visita") — opcional
        model:      Modelo Claude a usar

    Returns:
        dict con:
            workflow_id, title, content, positioning, scores
    """
    wf = WorkflowRunner("landing_page", service, service, location)

    try:
        # ── Step 1: Market positioning ────────────────────────────────────────
        positioning = wf.run_step(
            step_name  = "market_positioning",
            agent_name = "page-cro",
            model      = model,
            prompt     = f"""Eres un experto en CRO y copywriting para mercado chileno.

{_BUSINESS_CONTEXT}

Estás creando la estrategia de posicionamiento para una landing page de WashDog.

Servicio:   {service}
Ubicación:  {location}, Santiago, Chile
Promoción:  {promotion or 'Sin promoción activa en este momento'}

Genera en formato de lista:

1. PROPUESTA DE VALOR PRINCIPAL (1 frase de máx 10 palabras)

2. OBJECIONES PRINCIPALES (3 objeciones reales de dueños de perros en {location} y cómo resolverlas)

3. SEÑALES DE CONFIANZA (3 elementos: experiencia, garantía, reseñas, certificaciones)

4. ÁNGULO EMOCIONAL (por qué le importa a un dueño de perro en {location})

5. DIFERENCIADORES vs competencia local

Todo en español chileno.""",
        )

        # ── Step 2: Full landing page copy ────────────────────────────────────
        page_copy = wf.run_step(
            step_name  = "copy_generation",
            agent_name = "copywriting",
            model      = model,
            prompt     = f"""Escribe el copy completo para una landing page de WashDog.

{_BUSINESS_CONTEXT}

Servicio:   {service}
Ubicación:  {location}, Santiago, Chile
Promoción:  {promotion or 'Sin promoción activa'}

Estrategia de posicionamiento:
{positioning}

Estructura requerida (Markdown, lista para implementar en web):

# [Headline principal — beneficio claro, máx 8 palabras]
## [Subheadline — refuerza el beneficio con detalle]

---

### ¿Qué incluye el {service}?
[Lista de 4–6 puntos con íconos de emoji, beneficios no características]

---

### ¿Por qué WashDog en {location}?
[3 razones con título bold y descripción de 1–2 líneas cada una]

---

### Lo que dicen nuestros clientes en {location}
[2 testimonios realistas con nombre, raza del perro y puntuación ⭐]

---

### Precios {service} en {location}
[Tabla de precios por tamaño: Pequeño / Mediano / Grande — valores en CLP]
{f'🎉 Promoción: {promotion}' if promotion else ''}

---

### ¿Listo para darle lo mejor a tu perro?
[CTA principal + descripción breve del proceso de reserva]
[Botón: "Reserva tu hora por WhatsApp →"]
[CTA secundario: "Ver disponibilidad online"]

---

Requisitos:
✓ Mencionar {location} y comunas aledañas de forma natural
✓ Precios en CLP
✓ Tono: profesional, cálido, orientado a conversión
✓ Máximo 600 palabras (landing page, no artículo)
✓ Incluir keyword "{service} {location}" en el H1 y al menos 2 veces en el cuerpo""",
        )

        title = f"WashDog {service} en {location} — Peluquería Canina Premium Santiago"

        # ── Guardar contenido ─────────────────────────────────────────────────
        wf.save_content(
            content_type = "landing",
            title        = title,
            content      = page_copy,
        )

        # ── Evaluación automática ─────────────────────────────────────────────
        scores = score_content(
            workflow_id  = wf.workflow_id,
            content      = page_copy,
            content_type = "landing",
            keyword      = f"{service} {location}",
            city         = location,
            model        = "claude-haiku-4-5",
        )

        wf.complete()

        return {
            "workflow_id":  wf.workflow_id,
            "title":        title,
            "content":      page_copy,
            "positioning":  positioning,
            "scores":       scores,
        }

    except Exception as e:
        wf.fail(str(e))
        raise
