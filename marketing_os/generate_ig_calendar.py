"""
WashDog — Instagram Content Calendar Generator
===============================================
Generates 3 months of Instagram posts (4/week) using Claude.
Outputs a Google Sheet with: Date, Category, Template, Caption, Hashtags, Status.

Usage:
    .venv/bin/python generate_ig_calendar.py
"""

import os
import sys
import time
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
sys.path.insert(0, os.path.dirname(__file__))

import anthropic
from workspace.api import get_or_create_folder, append_to_sheet

# ── Config ─────────────────────────────────────────────────────────────────
START_DATE   = date(2026, 3, 9)   # Today
WEEKS        = 13                  # 3 months
POSTS_PER_WEEK = 4
POST_DAYS    = [0, 2, 4, 6]       # Mon, Wed, Fri, Sun

SITE_URL     = "https://www.washdog.cl"
NEWSLETTER_URL = f"{SITE_URL}/newsletter"
IG_HANDLE    = "@washdogexpress"

# ── Hashtag sets ───────────────────────────────────────────────────────────
HASHTAGS = {
    "A": "#perrossantiago #santiagoconperros #nunoa #peluqueriacanina #cuidadocanino #tipcanino #consejocanino #saludcanina #perrosfelices #doglovers #washdog",
    "B": "#perrossantiago #dogfriendlysantiago #santiagodechile #santiagoacuatropatas #parquesperros #vidaconperros #perroschile #duenosdeperros #nunoa #washdog #santiagoconperros",
    "C": "#peluqueriacaninasantiago #banocanino #groomingcanino #autolavadoperros #esteticacanina #perrossantiago #nunoa #cuidadocanino #dogsofinstagram #washdog #mascotas",
}

# ── Content pool ────────────────────────────────────────────────────────────
TIPS = [
    "frecuencia de baño según tipo de pelo (corto vs largo)",
    "cómo proteger las almohadillas en el asfalto caliente de Santiago en verano",
    "señales de que tu perro necesita un corte de pelo urgente",
    "cómo cepillar correctamente según la raza",
    "por qué el shampoo humano hace daño al perro",
    "cómo limpiar las orejas de tu perro en casa",
    "cuándo empezar a llevar al cachorro al peluquero",
    "cómo reducir la muda de pelo en casa",
    "hidratación: cuánta agua necesita tu perro según su tamaño",
    "señales de estrés en el peluquero y cómo evitarlas",
    "diferencia entre deslanado y corte normal",
    "cómo cuidar el pelo de tu perro entre visitas al peluquero",
    "parasitosis: cómo detectarla durante el baño",
]

PARKS = [
    {"nombre": "Parque Inés de Suárez", "comuna": "Providencia", "detalle": "zona habilitada para perros, pasto bien mantenido, fácil acceso desde metro"},
    {"nombre": "Parque Bicentenario", "comuna": "Vitacura", "detalle": "laguna, zona de perros cercada, muy amplio, ideal para razas grandes"},
    {"nombre": "Parque Bustamante", "comuna": "Providencia", "detalle": "céntrico, con sombra, popular entre dueños de perros de la zona"},
    {"nombre": "Parque Forestal", "comuna": "Santiago Centro", "detalle": "a orillas del Mapocho, largo y sombreado, ideal para paseos largos"},
    {"nombre": "Parque Las Américas", "comuna": "Ñuñoa", "detalle": "a pasos de WashDog, ideal para llevar al perro después del baño"},
    {"nombre": "Parque Intercomunal La Reina", "comuna": "La Reina", "detalle": "uno de los más grandes de Santiago, con zonas de corrida sin correa"},
    {"nombre": "Parque Araucano", "comuna": "Las Condes", "detalle": "muy frecuentado por familias con perros, bien equipado y con áreas verdes amplias"},
    {"nombre": "Parque Uruguay", "comuna": "Providencia", "detalle": "pequeño pero popular entre vecinos, ambiente tranquilo"},
    {"nombre": "Parque Metropolitano (Cerro San Cristóbal)", "comuna": "Recoleta", "detalle": "para los más aventureros, subida con tu perro y vistas increíbles"},
    {"nombre": "Parque Padre Hurtado", "comuna": "Santiago", "detalle": "grandes áreas verdes, tranquilo, ideal para perros que necesitan espacio"},
    {"nombre": "Parque Julio Valdés Cange", "comuna": "Macul", "detalle": "cerca de Ñuñoa, tranquilo y con buena sombra"},
    {"nombre": "Parque O'Higgins", "comuna": "Santiago Centro", "detalle": "enorme, con laguna artificial, eventos dog-friendly frecuentes"},
    {"nombre": "Parque Los Reyes", "comuna": "Santiago", "detalle": "a orillas del Mapocho, espacioso y con ciclovía adyacente"},
]

SERVICES = [
    {"servicio": "autolavado", "angulo": "tú bañas a tu perro con equipamiento profesional sin ensuciar tu casa"},
    {"servicio": "baño profesional", "angulo": "diferencia entre bañar en casa y bañar con shampoo hipoalergénico profesional"},
    {"servicio": "peluquería canina", "angulo": "corte adaptado a la raza, no todos los perros se cortan igual"},
    {"servicio": "corte higiénico", "angulo": "por qué el corte higiénico es importante para la salud, no solo la estética"},
    {"servicio": "peluquería para gatos", "angulo": "grooming felino especializado, diferente al canino"},
    {"servicio": "agenda online", "angulo": "reserva en 2 minutos desde el celular, sin llamar"},
    {"servicio": "baño profesional", "angulo": "productos premium vs shampoo de supermercado, la diferencia real"},
    {"servicio": "autolavado", "angulo": "ideal para perros grandes que no caben en la tina de la casa"},
    {"servicio": "peluquería canina", "angulo": "antes y después — la transformación de un Golden Retriever"},
    {"servicio": "corte de temporada", "angulo": "por qué en verano el corte correcto ayuda a regular la temperatura"},
    {"servicio": "deslanado", "angulo": "menos pelo en el sillón, más comodidad para el perro"},
    {"servicio": "primer baño del cachorro", "angulo": "cómo preparar al cachorro para su primera visita al peluquero"},
    {"servicio": "baño express", "angulo": "30-45 minutos y tu perro listo, sin cita previa en el autolavado"},
]

CLIENTS = [
    {"nombre_perro": "Luna", "raza": "Golden Retriever", "comuna": "Ñuñoa", "situacion": "llegó después de una tarde de parque llena de barro"},
    {"nombre_perro": "Simón", "raza": "Schnauzer miniatura", "comuna": "Providencia", "situacion": "primera visita después de 3 meses sin corte"},
    {"nombre_perro": "Mila", "raza": "Poodle", "comuna": "Las Condes", "situacion": "cliente fiel desde que abrimos, viene cada mes"},
    {"nombre_perro": "Thor", "raza": "Husky Siberiano", "comuna": "La Reina", "situacion": "deslanado completo antes del verano"},
    {"nombre_perro": "Coco", "raza": "Cocker Spaniel", "comuna": "Macul", "situacion": "pelo muy enredado, transformación increíble"},
    {"nombre_perro": "Nala", "raza": "Labrador", "comuna": "Peñalolén", "situacion": "usó el autolavado por primera vez con su dueño"},
    {"nombre_perro": "Max", "raza": "Border Collie", "comuna": "Ñuñoa", "situacion": "corte de verano para aguantar el calor de Santiago"},
    {"nombre_perro": "Bella", "raza": "Yorkshire Terrier", "comuna": "Vitacura", "situacion": "corte completo y arreglo de orejas"},
    {"nombre_perro": "Toby", "raza": "Beagle", "comuna": "San Miguel", "situacion": "llegó nervioso, salió tranquilo y feliz"},
    {"nombre_perro": "Lola", "raza": "Shih Tzu", "comuna": "Providencia", "situacion": "nunuito que viene con su abuela cada tres semanas"},
    {"nombre_perro": "Bruno", "raza": "Rottweiler", "comuna": "La Florida", "situacion": "baño de perro grande en el autolavado"},
    {"nombre_perro": "Kira", "raza": "Pastor Alemán", "comuna": "Macul", "situacion": "deslanado profesional, llegó con kilos de subpelo"},
    {"nombre_perro": "Pancho", "raza": "Perro mestizo", "comuna": "Ñuñoa", "situacion": "rescatado hace 2 meses, primer baño profesional"},
]

# ── Template rotation ───────────────────────────────────────────────────────
TEMPLATES = {
    "tip":     ["tip-1", "tip-2", "tip-3", "tip-4", "tip-5"],
    "park":    ["park-1", "park-2", "park-3", "park-4", "park-5"],
    "service": ["service-1", "service-2", "service-3", "service-4", "service-5"],
    "client":  ["client-1", "client-2", "client-3", "client-4", "client-5"],
}

CATEGORY_ORDER = ["tip", "park", "service", "client"]
HASHTAG_ORDER  = {"tip": "A", "park": "B", "service": "C", "client": "C"}

# ── Claude caption generator ────────────────────────────────────────────────
ai = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

def generate_caption(category: str, context: dict, week: int) -> str:
    if category == "tip":
        prompt = f"""Eres el community manager de WashDog, peluquería canina en Ñuñoa, Santiago.
Escribe un post de Instagram para enseñar este tip a dueños de perros en Santiago:

TEMA: {context['tema']}

REGLAS:
- Hook en la primera línea (máx 125 chars) que para el scroll
- 3-4 párrafos cortos de máx 3 líneas cada uno
- Específico para Santiago (menciona el calor, las comunas, el estilo de vida)
- Termina con CTA claro: suscribirse al newsletter o visitar washdog.cl
- Sin hashtags (van en primer comentario)
- Sin exclamaciones (!)
- Máx 250 palabras
- Escribe SOLO el texto del post, sin comillas ni explicaciones"""
    elif category == "park":
        prompt = f"""Eres el community manager de WashDog, peluquería canina en Ñuñoa, Santiago.
Escribe un post de Instagram recomendando este parque dog-friendly:

PARQUE: {context['nombre']}
COMUNA: {context['comuna']}
DETALLE: {context['detalle']}

REGLAS:
- Hook en la primera línea que pinte la escena
- Describe el parque con detalles específicos (qué tiene, por qué ir)
- Menciona cuándo ir (fin de semana, mañana, tarde)
- Termina con CTA al newsletter "Santiago a Cuatro Patas" donde compartimos uno cada semana
- Sin hashtags
- Sin exclamaciones
- Máx 200 palabras
- Escribe SOLO el texto del post"""
    elif category == "service":
        prompt = f"""Eres el community manager de WashDog, peluquería canina en Ñuñoa, Santiago.
Escribe un post de Instagram para este servicio:

SERVICIO: {context['servicio']}
ÁNGULO: {context['angulo']}

REGLAS:
- Hook que identifique el problema o situación que resuelve el servicio
- Explica el servicio de forma específica (pasos, qué incluye, cuánto tarda)
- Menciona el precio si es relevante (baño desde $10.000, peluquería desde $20.000, gatos $40.000)
- CTA: "Agenda en washdog.cl" o "Llega directo, sin cita previa"
- Sin hashtags
- Sin exclamaciones
- Máx 200 palabras
- Escribe SOLO el texto del post"""
    else:  # client
        prompt = f"""Eres el community manager de WashDog, peluquería canina en Ñuñoa, Santiago.
Escribe un post de Instagram presentando a este cliente:

NOMBRE DEL PERRO: {context['nombre_perro']}
RAZA: {context['raza']}
COMUNA: {context['comuna']}
SITUACIÓN: {context['situacion']}

REGLAS:
- Empieza con "Hoy conocimos a [nombre] 🐾" o variación
- Presenta al perro con personalidad, no solo datos
- Incluye una "cita" breve del dueño (inventada pero realista)
- Cierre cálido que invite a compartir fotos de sus perros por DM
- Sin hashtags
- Sin exclamaciones
- Máx 150 palabras
- Escribe SOLO el texto del post"""

    msg = ai.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


# ── Build calendar ──────────────────────────────────────────────────────────
def build_calendar():
    calendar = []
    tip_i = park_i = service_i = client_i = 0

    for week in range(WEEKS):
        week_start = START_DATE + timedelta(weeks=week)

        for slot, day_offset in enumerate(POST_DAYS):
            post_date = week_start + timedelta(days=day_offset)
            # Skip if date already passed
            if post_date < START_DATE:
                continue

            category = CATEGORY_ORDER[slot % 4]
            tmpl_idx = (week) % 5
            template = TEMPLATES[category][tmpl_idx]
            hashtag_set = HASHTAG_ORDER[category]
            hashtags = HASHTAGS[hashtag_set]

            # Get content for this category
            if category == "tip":
                ctx = {"tema": TIPS[tip_i % len(TIPS)]}
                tip_i += 1
            elif category == "park":
                ctx = PARKS[park_i % len(PARKS)]
                park_i += 1
            elif category == "service":
                ctx = SERVICES[service_i % len(SERVICES)]
                service_i += 1
            else:
                ctx = CLIENTS[client_i % len(CLIENTS)]
                client_i += 1

            calendar.append({
                "date":     post_date,
                "day":      post_date.strftime("%A"),
                "week":     week + 1,
                "category": category.capitalize(),
                "template": template,
                "context":  ctx,
                "hashtags": hashtags,
                "set":      hashtag_set,
            })

    return calendar


# ── Generate captions ───────────────────────────────────────────────────────
def generate_all_captions(calendar):
    print(f"Generando {len(calendar)} captions con Claude...")
    for i, post in enumerate(calendar):
        print(f"  [{i+1}/{len(calendar)}] {post['date']} — {post['category']}...")
        caption = generate_caption(
            post["category"].lower(),
            post["context"],
            post["week"],
        )
        post["caption"] = caption
        time.sleep(0.5)  # Rate limit buffer
    return calendar


# ── Push to Google Sheet ────────────────────────────────────────────────────
def push_to_sheet(calendar):
    SHEET_NAME = "WashDog — Instagram Calendar"

    header = [
        "Semana", "Fecha", "Día", "Categoría", "Template",
        "Caption", "Hashtags (1er comentario)", "Set", "Estado"
    ]

    rows = [header]
    for post in calendar:
        rows.append([
            f"Semana {post['week']}",
            post["date"].strftime("%d/%m/%Y"),
            post["day"],
            post["category"],
            post["template"],
            post["caption"],
            post["hashtags"],
            f"Set {post['set']}",
            "Pendiente",
        ])

    sheet_id = append_to_sheet(SHEET_NAME, rows)
    return sheet_id


# ── Main ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("📅 WashDog — Instagram Calendar Generator")
    print(f"   Período: {START_DATE} → {START_DATE + timedelta(weeks=WEEKS)}")
    print(f"   Posts: {WEEKS * POSTS_PER_WEEK} total\n")

    calendar = build_calendar()
    print(f"✅ Calendario armado: {len(calendar)} posts\n")

    calendar = generate_all_captions(calendar)
    print("\n✅ Captions generados\n")

    sheet_id = push_to_sheet(calendar)
    print(f"\n✅ Google Sheet creado:")
    print(f"   https://docs.google.com/spreadsheets/d/{sheet_id}")
