"""
Marketing OS — Newsletter Workflow
WashDog — "Santiago a Cuatro Patas" weekly newsletter

Genera el borrador semanal de la newsletter dog-friendly de Santiago.

Steps:
    1. content_curation   — Curación de lugar, evento y tip dog-friendly en Santiago
    2. subject_lines      — 5 variantes de asunto optimizadas (copywriting agent)
    3. newsletter_draft   — Ensamblaje del borrador completo en Markdown
"""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from workflows.base import WorkflowRunner

_AGENTS_DIR = Path(__file__).parent.parent / "agents"

def _load_skill(agent_name: str) -> str:
    """Loads the SKILL.md for an agent to use as context."""
    skill_path = _AGENTS_DIR / agent_name / "SKILL.md"
    if skill_path.exists():
        return skill_path.read_text(encoding="utf-8")
    return ""


_BUSINESS_CONTEXT = """
WashDog es una peluquería canina premium en Ñuñoa, Santiago, Chile.
Servicios: baño completo, corte de pelo, tratamiento antipulgas, deslanado, corte de uñas.
Ubicación: Av. Irarrázaval 2086 B, Ñuñoa · Lunes a domingo 10:00–20:00
Web: https://www.washdog.cl
Instagram: @washdogexpress
"""

_NEWSLETTER_NAME    = "Santiago a Cuatro Patas"
_NEWSLETTER_TAGLINE = "La guía semanal para vivir Santiago con tu perro"

# Ofertas WashDog rotativas por número de edición
_OFERTAS = [
    ("20% off en baño completo esta semana",             "bano-perros"),
    ("Corte + baño al precio del corte",                 "corte-perros"),
    ("Tratamiento antipulgas gratis con cualquier servicio", "bano-perros"),
    ("Deslanado especial verano — cupos limitados",      "bano-perros"),
]


def run_newsletter(
    issue_number: int,
    focus_commune: str = "Ñuñoa",
    model: str = "claude-sonnet-4-6",
) -> dict:
    """
    Genera el borrador completo de la newsletter semanal.

    Args:
        issue_number:   Número de edición (para tracking y rotación de ofertas)
        focus_commune:  Comuna principal de esta edición
        model:          Modelo Claude a usar

    Returns:
        dict con: workflow_id, issue_number, subject_line, preview_text,
                  body (markdown sin encabezado), sections (dict curado), full_draft
    """
    wf = WorkflowRunner(
        "newsletter",
        f"Edición #{issue_number} — {focus_commune}",
        target_keyword=f"perros {focus_commune} Santiago",
        city=focus_commune,
    )

    try:
        # ── Step 1: Curación de contenido ──────────────────────────────────────
        curated_raw = wf.run_step(
            step_name  = "content_curation",
            agent_name = "copywriting",
            model      = model,
            prompt     = f"""Eres el curador de "{_NEWSLETTER_NAME}", una newsletter semanal para dueños de perros en Santiago, Chile.

{_BUSINESS_CONTEXT}

Esta edición (#{issue_number}) tiene foco en la comuna de {focus_commune}.

Genera el contenido específico para cada sección. Tono: cálido, positivo y práctico — sin política, sin controversia, solo contenido útil y divertido para dueños de perros santiaguinos.

Retorna SOLO un JSON con esta estructura exacta:

{{
  "lugar": {{
    "nombre": "Nombre real o verosímil de un café, parque o espacio dog-friendly en Santiago (preferiblemente cerca de {focus_commune})",
    "descripcion": "2-3 oraciones concretas: si tiene agua para perros, sombra, espacio para correr, si el local tiene bowl de agua, si es tranquilo, etc.",
    "direccion": "Dirección o intersección aproximada",
    "por_que": "Una frase corta tipo 'ideal para después del baño del sábado'"
  }},
  "evento": {{
    "nombre": "Nombre de un evento, meetup o actividad dog-friendly en Santiago este mes",
    "descripcion": "2 oraciones sobre el evento",
    "cuando": "Día y hora aproximada (ej: 'Sábados 10:00–12:00')",
    "donde": "Lugar o barrio"
  }},
  "tip": {{
    "titulo": "Título del tip semanal (máx 60 caracteres, accionable)",
    "contenido": "3-4 oraciones de consejo práctico sobre cuidado canino relevante para Santiago (calor de verano, smog, pelaje, hidratación, paseos). Menciona de forma natural cuándo el grooming profesional ayuda."
  }},
  "dato_curioso": "Un dato curioso o estadística sobre perros o cultura pet-friendly en Chile (1-2 oraciones, con fuente estimada si aplica)"
}}""",
        )

        # Parsear con fallback
        try:
            raw = curated_raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1].lstrip("json").strip()
            sections = json.loads(raw)
        except json.JSONDecodeError:
            sections = {
                "lugar":        {"nombre": "Parque Bicentenario", "descripcion": "Amplio parque con zonas verdes.", "direccion": "Av. Bicentenario, Vitacura", "por_que": "Perfecto para un paseo largo"},
                "evento":       {"nombre": "Meetup canino semanal", "descripcion": "Encuentro informal de perros y dueños.", "cuando": "Sábados 10:00", "donde": "Parque local"},
                "tip":          {"titulo": "Hidratación en verano", "contenido": "Lleva agua fresca en tus paseos. En días de calor intenso, el grooming profesional ayuda a regular la temperatura."},
                "dato_curioso": "Chile tiene una de las tasas de adopción de mascotas más altas de Latinoamérica.",
            }

        # ── Step 2: Subject line optimization (copywriting agent) ─────────────
        lugar  = sections.get("lugar", {})
        evento = sections.get("evento", {})
        tip    = sections.get("tip", {})
        dato   = sections.get("dato_curioso", "")

        copywriting_skill = _load_skill("copywriting")

        subjects_raw = wf.run_step(
            step_name  = "subject_lines",
            agent_name = "copywriting",
            model      = model,
            prompt     = f"""{copywriting_skill}

---

Eres un experto en email marketing para audiencias latinoamericanas.
Newsletter: "{_NEWSLETTER_NAME}" — {_NEWSLETTER_TAGLINE}
Edición: #{issue_number} | Foco: {focus_commune}

Contenido de esta edición:
- Lugar: {lugar.get('nombre')} — {lugar.get('por_que')}
- Evento: {evento.get('nombre')}
- Tip: {tip.get('titulo')}

Genera 5 subject lines en español para este email. Reglas:
1. Máximo 50 caracteres
2. Un emoji al inicio (varía el tipo)
3. Intrigante pero claro — el receptor debe querer abrirlo
4. NO clickbait exagerado — tono cálido y local
5. Menciona implícitamente {focus_commune} o "Santiago" en al menos 2

Retorna SOLO las 5 líneas, una por línea, sin numeración ni explicación.""",
        )

        # Pick the first subject line as default
        subject_candidates = [s.strip() for s in subjects_raw.strip().split("\n") if s.strip()]
        best_subject = subject_candidates[0] if subject_candidates else f"🐾 {_NEWSLETTER_NAME} #{issue_number}"

        oferta_text, oferta_slug = _OFERTAS[issue_number % len(_OFERTAS)]

        draft = wf.run_step(
            step_name  = "newsletter_draft",
            agent_name = "copywriting",
            model      = model,
            prompt     = f"""Ensambla el borrador completo de la edición #{issue_number} de "{_NEWSLETTER_NAME}".
Tagline: {_NEWSLETTER_TAGLINE} — by WashDog

Usa este contenido curado:

LUGAR DOG-FRIENDLY SEMANAL:
- Nombre: {lugar.get('nombre')}
- Descripción: {lugar.get('descripcion')}
- Dirección: {lugar.get('direccion')}
- Por qué ir: {lugar.get('por_que')}

EVENTO / ACTIVIDAD:
- Nombre: {evento.get('nombre')}
- Descripción: {evento.get('descripcion')}
- Cuándo: {evento.get('cuando')}
- Dónde: {evento.get('donde')}

TIP DE LA SEMANA:
- Título: {tip.get('titulo')}
- Contenido: {tip.get('contenido')}

DATO CURIOSO: {dato}

OFERTA WASHDOG DE LA SEMANA: {oferta_text}
URL: https://www.washdog.cl/servicios/{oferta_slug}

─────────────────────────────────────
INSTRUCCIONES DE FORMATO:

1. Empieza con estas dos líneas (antes del cuerpo, separadas con ---):
   SUBJECT: {best_subject}
   PREVIEW: [preview text de 90 caracteres, complementa el subject sin repetirlo]
   ---

2. Cuerpo de la newsletter en Markdown:
   - Saludo breve y personal al inicio (ej: "Hola 🐾, aquí va tu dosis semanal de Santiago perruno.")
   - Secciones en este orden:
     • 📍 Lugar de la Semana
     • 🗓️ Evento / Actividad
     • 💡 Tip de la Semana
     • 📸 Perro de la Semana — incluye este placeholder exacto:
       > *Esta sección es tuya. Mándanos la foto de tu perro por DM a [@washdogexpress](https://www.instagram.com/washdogexpress/) con el hashtag #SantiagoCuatroPatas y aparece aquí la semana siguiente.*
     • 🐶 Oferta WashDog — la oferta debe sentirse útil, no publicitaria
   - Dato curioso integrado naturalmente (puede ir entre secciones)
   - Cierre cálido + firma: "— El equipo WashDog 🐶"
   - Link de baja discreta al final: *¿No quieres recibirla más? [Cancelar suscripción](#)*

3. Tono: español chileno natural ("ustedes", nunca "vosotros"), cálido, sin exagerar
4. Emojis: máx 1-2 por sección como marcadores visuales, no decorativos
5. La newsletter debe sentirse como contenido de valor primero. WashDog aparece como facilitador, no como anunciante
6. Formato Markdown limpio listo para pegar en Beehiiv o MailerLite""",
        )

        # Extraer subject y preview del encabezado
        subject_line = f"{_NEWSLETTER_NAME} #{issue_number}"
        preview_text = ""
        body_lines   = draft.strip().split("\n")
        body_start   = 0

        for i, line in enumerate(body_lines):
            if line.strip() == "---":
                body_start = i + 1
                break
            if line.startswith("SUBJECT:"):
                subject_line = line.replace("SUBJECT:", "").strip()
            elif line.startswith("PREVIEW:"):
                preview_text = line.replace("PREVIEW:", "").strip()

        body = "\n".join(body_lines[body_start:]).strip()

        wf.save_content(
            content_type     = "newsletter",
            title            = f"{_NEWSLETTER_NAME} #{issue_number} — {focus_commune}",
            content          = draft,
            meta_description = preview_text,
        )

        wf.complete()

        return {
            "workflow_id":        wf.workflow_id,
            "issue_number":       issue_number,
            "subject_line":       subject_line,
            "preview_text":       preview_text,
            "body":               body,
            "sections":           sections,
            "full_draft":         draft,
            "subject_candidates": subject_candidates,
        }

    except Exception as e:
        wf.fail(str(e))
        raise
