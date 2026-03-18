#!/usr/bin/env python3
"""
Marketing OS — SEO Tasks Sheet Creator
Creates (or resets) the "WashDog Plan de Acción" Google Sheet.

Tabs:
  1. Fichas en Directorios  — verificar y enviar fichas a directorios locales
  2. Directorios             — tabla de seguimiento por directorio
  3. Google Business Profile — crear y optimizar fichas en GBP / Maps
  4. Redes Sociales          — crear y configurar perfiles sociales
  5. Herramientas Google     — GSC y GA4
  6. Imágenes & Contenido    — imágenes, fotos y primeras publicaciones
  7. Reseñas & Alianzas      — reseñas, contactos locales y prensa

Usage:
    python create_seo_tasks_sheet.py          # crear (si no existe)
    python create_seo_tasks_sheet.py --reset  # limpiar y reescribir todo
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from workspace.api import _sheets, _find_sheet_by_name

SHEET_NAME = "WashDog Plan de Acción"

TASK_HEADERS = [
    "#", "Categoría", "Tarea", "Instrucciones detalladas",
    "URL / Objetivo", "Prioridad", "Estado", "Notas",
]

DIR_HEADERS = [
    "Directorio", "URL del directorio", "Acción requerida",
    "Estado", "URL de Ficha", "Fecha de envío", "Verificado", "Notas",
]

# ── Tab 1: Fichas en Directorios ──────────────────────────────────────────────

TASKS_DIRECTORIOS = [
    [1, "Revisión", "Revisar ficha en 2x3.cl",
     "Buscar 'WashDog Ñuñoa' en 2x3.cl. Si la ficha existe → anotar 'Reclamar existente'. Si no existe → anotar 'Crear nueva'. Actualizar pestaña Directorios.",
     "https://www.2x3.cl", "Alta", "Pendiente", ""],

    [2, "Revisión", "Revisar ficha en Yapo.cl",
     "Buscar 'WashDog Ñuñoa' en Yapo.cl. Si la ficha existe → anotar 'Reclamar existente'. Si no existe → anotar 'Crear nueva'. Actualizar pestaña Directorios.",
     "https://www.yapo.cl", "Alta", "Pendiente", ""],

    [3, "Revisión", "Revisar ficha en Amarillas.cl",
     "Buscar 'WashDog Ñuñoa' en Amarillas.cl. Si la ficha existe → anotar 'Reclamar existente'. Si no existe → anotar 'Crear nueva'. Actualizar pestaña Directorios.",
     "https://www.amarillas.cl", "Alta", "Pendiente", ""],

    [4, "Revisión", "Revisar ficha en AgendaPro",
     "Buscar 'WashDog' en AgendaPro. Si la ficha existe → anotar 'Reclamar existente'. Si no existe → anotar 'Crear nueva'. Actualizar pestaña Directorios.",
     "https://www.agendapro.com", "Alta", "Pendiente", ""],

    [5, "Revisión", "Revisar ficha en ChileAtiende",
     "Buscar 'WashDog Ñuñoa' en ChileAtiende. Si la ficha existe → anotar 'Reclamar existente'. Si no existe → anotar 'Crear nueva'. Actualizar pestaña Directorios.",
     "https://www.chileatiende.gob.cl", "Media", "Pendiente", ""],

    [6, "Revisión", "Revisar ficha en DoctorMascota",
     "Buscar 'WashDog Ñuñoa' en DoctorMascota. Si la ficha existe → anotar 'Reclamar existente'. Si no existe → anotar 'Crear nueva'. Actualizar pestaña Directorios.",
     "https://www.doctormascota.cl", "Media", "Pendiente", ""],

    [7, "Revisión", "Revisar ficha en VetChile",
     "Buscar 'WashDog Ñuñoa' en VetChile. Si la ficha existe → anotar 'Reclamar existente'. Si no existe → anotar 'Crear nueva'. Actualizar pestaña Directorios.",
     "https://www.vetchile.cl", "Media", "Pendiente", ""],

    [8, "Envío", "Enviar o reclamar cada ficha (instrucciones generales)",
     "Repetir para CADA directorio: "
     "(1) Ir al directorio e iniciar sesión o crear cuenta. "
     "(2) Si la ficha ya existe → buscarla y hacer clic en 'Reclamar este negocio'. Si no existe → 'Agregar negocio'. "
     "(3) Completar datos: Nombre: WashDog — Peluquería Canina Ñuñoa | Dirección: Av. Irarrázaval 2086, B, Ñuñoa, Santiago | Teléfono: +56 9 87230388 | Web: https://www.washdog.cl | Horario: Lunes a Domingo 10:00–20:00. "
     "(4) Subir logo + mínimo 2 fotos del local. "
     "(5) Agregar link al sitio web y al hub: https://www.washdog.cl/servicios/peluqueria-canina. "
     "(6) Guardar URL de la ficha en la pestaña Directorios.",
     "Ver pestaña Directorios", "Alta", "Pendiente", ""],

    [9, "Optimización", "Optimizar cada ficha una vez publicada",
     "(1) Nombre completo: 'WashDog — Peluquería Canina Ñuñoa'. "
     "(2) Seleccionar todas las categorías disponibles: peluquería canina, baño de mascotas, grooming, spa canino. "
     "(3) Descripción: copiarla de la hoja 'WashDog Master Directory Info' y modificar al menos una oración por directorio para evitar contenido duplicado. "
     "(4) Servicios: Peluquería canina, Baño de perros, Corte de pelo, Auto lavado, Peluquería de gatos, Spa canino. "
     "(5) Links: https://www.washdog.cl y https://www.washdog.cl/servicios/peluqueria-canina. "
     "(6) Imágenes: logo + 2–3 fotos de atención. Actualizar estado a 'Optimizado' en pestaña Directorios.",
     "Ver pestaña Directorios", "Alta", "Pendiente", ""],

    [10, "Verificación", "Verificar fichas y registrar URL final",
     "(1) Revisar correo de confirmación de cada directorio (puede tardar hasta 48 horas). "
     "(2) Si piden verificación por teléfono → tener disponible el número +56 9 87230388. "
     "(3) Si piden verificación por email → hacer clic en el link de confirmación. "
     "(4) Una vez publicada la ficha, copiar el URL y pegarlo en la columna 'URL de Ficha' en la pestaña Directorios. "
     "(5) Cambiar estado a 'Verificado'.",
     "Ver pestaña Directorios", "Alta", "Pendiente", ""],
]

# ── Tab 2: Directorios (tracking) ─────────────────────────────────────────────

DIRECTORIES = [
    ["2x3.cl",        "https://www.2x3.cl",              "Por definir", "Pendiente", "", "", "No", ""],
    ["Yapo.cl",       "https://www.yapo.cl",             "Por definir", "Pendiente", "", "", "No", ""],
    ["Amarillas.cl",  "https://www.amarillas.cl",        "Por definir", "Pendiente", "", "", "No", ""],
    ["AgendaPro",     "https://www.agendapro.com",       "Por definir", "Pendiente", "", "", "No", ""],
    ["ChileAtiende",  "https://www.chileatiende.gob.cl", "Por definir", "Pendiente", "", "", "No", ""],
    ["DoctorMascota", "https://www.doctormascota.cl",    "Por definir", "Pendiente", "", "", "No", ""],
    ["VetChile",      "https://www.vetchile.cl",         "Por definir", "Pendiente", "", "", "No", ""],
]

# ── Tab 3: Google Business Profile ────────────────────────────────────────────

TASKS_GBP = [
    [1, "Google Business Profile", "Crear o reclamar ficha principal en GBP",
     "WashDog tiene una sola ubicación física (Ñuñoa). Las otras comunas son áreas de servicio, NO ubicaciones separadas. "
     "(1) Ir a https://business.google.com e iniciar sesión con la cuenta de Google del negocio. "
     "(2) Buscar 'WashDog' para ver si ya existe una ficha. Si existe → 'Reclamar este negocio'. Si no → 'Agregar negocio'. "
     "(3) Nombre: WashDog | Categoría principal: Peluquería de animales.",
     "https://business.google.com", "Urgente", "Pendiente", ""],

    [2, "Google Business Profile", "Completar información del negocio",
     "(1) Dirección: Av. Irarrázaval 2086, B, Ñuñoa, Santiago. "
     "(2) Teléfono: +56 9 87230388. "
     "(3) Sitio web: https://www.washdog.cl. "
     "(4) Horario: Lunes a Domingo 10:00–20:00. "
     "(5) Descripción: 'WashDog es una peluquería canina profesional en Ñuñoa, Santiago. Ofrecemos baño de perros, corte de pelo, peluquería de gatos y spa canino con productos hipoalergénicos premium. Atención individual, sin estrés para tu mascota. Agenda online en www.washdog.cl.' "
     "(6) Categorías adicionales: Servicio de aseo de mascotas, Spa de mascotas.",
     "https://business.google.com", "Urgente", "Pendiente", ""],

    [3, "Google Business Profile", "Agregar servicios en GBP",
     "En el menú 'Servicios', agregar: "
     "Peluquería canina | Baño de perros | Corte de pelo canino | Auto lavado de perros | Peluquería para gatos | Spa canino | Tratamiento antipulgas | Deslanado | Corte y lima de uñas. "
     "Agregar descripción breve y precio referencial a cada uno (ver hoja 'WashDog Master Directory Info').",
     "https://business.google.com", "Alta", "Pendiente", ""],

    [4, "Google Business Profile", "Agregar áreas de servicio (comunas)",
     "En 'Información' → 'Área de servicio', agregar: Ñuñoa, Providencia, Las Condes, La Reina, Macul, Peñalolén, La Florida, Santiago Centro. "
     "Esto permite que WashDog aparezca en búsquedas de esas comunas aunque la dirección física sea Ñuñoa.",
     "https://business.google.com", "Alta", "Pendiente", ""],

    [5, "Google Business Profile", "Subir fotos al perfil de GBP",
     "Subir al menos 5 fotos: "
     "(1) Logo (categoría: Logo). (2) Foto exterior del local (categoría: Exterior). "
     "(3) Foto interior / sala de atención (categoría: Interior). "
     "(4) Foto de un perro siendo atendido (categoría: En el trabajo). "
     "(5) Foto del equipo o productos (categoría: En el trabajo). "
     "Más fotos = más visibilidad en Google Maps.",
     "https://business.google.com", "Alta", "Pendiente", ""],

    [6, "Google Business Profile", "Verificar el negocio en GBP",
     "Google requiere verificación antes de publicar la ficha. Opciones: "
     "(1) SMS o llamada al +56 9 87230388. "
     "(2) Email de la cuenta del negocio. "
     "(3) Tarjeta postal (5–14 días hábiles, llega a Av. Irarrázaval 2086, Ñuñoa). "
     "Elegir la opción más rápida disponible. Una vez verificado, marcar como Listo.",
     "https://business.google.com", "Urgente", "Pendiente", ""],

    [7, "Google Business Profile", "Activar mensajería y link de reserva",
     "(1) En la ficha de GBP, ir a 'Mensajes' y activar mensajes directos desde Google. "
     "(2) En 'Información' → 'URLs' → agregar link de reserva: https://www.washdog.cl. "
     "(3) Verificar que el botón 'Reservar' o 'Llamar' aparezca correctamente en Google Maps.",
     "https://business.google.com", "Media", "Pendiente", ""],
]

# ── Tab 4: Redes Sociales ─────────────────────────────────────────────────────

TASKS_SOCIAL = [
    [1, "Instagram", "Crear perfil de Instagram Business",
     "(1) Crear cuenta con el usuario @washdog.cl o @washdog_nunoa. "
     "(2) Cambiar a cuenta de empresa: Configuración → Cuenta → Cambiar a cuenta profesional → Empresa. "
     "(3) Perfil: Nombre: WashDog | Bio: 'Peluquería canina profesional en Ñuñoa 🐾 Baño · Corte · Spa · Gatos | Agenda online 👇' | Link: https://www.washdog.cl. "
     "(4) Subir logo como foto de perfil. Categoría: Peluquería para mascotas. "
     "(5) Activar botón de contacto con el número +56 9 87230388.",
     "https://www.instagram.com", "Alta", "Pendiente", ""],

    [2, "Facebook", "Crear página de Facebook",
     "(1) Ir a https://www.facebook.com/pages/create e iniciar sesión. "
     "(2) Nombre: WashDog — Peluquería Canina Ñuñoa | Categoría: Peluquería y estética de mascotas. "
     "(3) Subir foto de perfil (logo) y foto de portada (foto del local). "
     "(4) Completar: teléfono, horario, dirección y link al sitio web. "
     "(5) Agregar botón de llamada a la acción: 'Reservar' → https://www.washdog.cl.",
     "https://www.facebook.com/pages/create", "Alta", "Pendiente", ""],

    [3, "TikTok", "Crear cuenta de TikTok Business",
     "(1) Crear cuenta con el usuario @washdog.cl. "
     "(2) Cambiar a cuenta Business: Perfil → Administrar cuenta → Cuenta de empresa → Mascotas. "
     "(3) Bio: 'Peluquería canina profesional en Ñuñoa 🐾 | Baño · Corte · Spa | Santiago' + link a https://www.washdog.cl. "
     "(4) Subir logo como foto de perfil. "
     "Contenido ideal: videos de transformaciones (antes/después) y proceso de grooming.",
     "https://www.tiktok.com", "Media", "Pendiente", ""],

    [4, "YouTube", "Crear canal de YouTube",
     "(1) Iniciar sesión en Google con la cuenta del negocio → ir a https://www.youtube.com/create_channel. "
     "(2) Nombre: WashDog Peluquería Canina. "
     "(3) Descripción: 'Canal oficial de WashDog, peluquería canina en Ñuñoa, Santiago. Videos de grooming, consejos de cuidado y transformaciones antes/después.' "
     "(4) Subir logo y portada del canal. Agregar link al sitio web en 'Acerca de'.",
     "https://www.youtube.com", "Baja", "Pendiente", ""],

    [5, "Contenido inicial", "Publicar primeras 3 publicaciones en cada red social",
     "(1) Post de presentación: '¡Hola! Somos WashDog, la peluquería canina de Ñuñoa. [foto del local o logo]'. "
     "(2) Post de servicios: listado de servicios con precios. "
     "(3) Post de antes/después: foto de un perro antes y después del grooming. "
     "Publicar en Instagram y Facebook. Para TikTok: versión en video (30–60 segundos).",
     "", "Alta", "Pendiente", ""],

    [6, "Configuración", "Agregar link de reserva a todos los perfiles",
     "(1) Instagram: link en bio → https://www.washdog.cl. "
     "(2) Facebook: botón 'Reservar' configurado. "
     "(3) TikTok: link en bio. "
     "(4) YouTube: link en descripción del canal.",
     "https://www.washdog.cl", "Media", "Pendiente", ""],
]

# ── Tab 5: Herramientas Google ────────────────────────────────────────────────

TASKS_GOOGLE_TOOLS = [
    [1, "Google Search Console", "Agregar y verificar propiedad washdog.cl",
     "NOTA: Si ya está configurado, marcar como Listo. "
     "(1) Ir a https://search.google.com/search-console. "
     "(2) Hacer clic en 'Agregar propiedad' → ingresar https://www.washdog.cl. "
     "(3) Verificar usando Google Analytics (opción más fácil si GA4 ya está activo), archivo HTML o DNS. "
     "(4) Una vez verificado, esperar hasta 48 horas para que aparezcan los primeros datos.",
     "https://search.google.com/search-console", "Alta", "Pendiente", ""],

    [2, "Google Search Console", "Enviar sitemap",
     "(1) En GSC → menú lateral → 'Sitemaps'. "
     "(2) En 'Agregar un nuevo sitemap', ingresar: sitemap.xml y hacer clic en 'Enviar'. "
     "(3) Verificar que aparezca como 'Correcto' y muestre el número de URLs. "
     "Si aparece un error, reportar al equipo técnico.",
     "https://search.google.com/search-console/sitemaps", "Alta", "Pendiente", ""],

    [3, "Google Search Console", "Solicitar indexación de páginas clave",
     "Para cada URL, ir a GSC → Inspección de URL → pegar URL → 'Solicitar indexación'. "
     "Páginas a enviar: "
     "https://www.washdog.cl | "
     "https://www.washdog.cl/servicios/peluqueria-canina-nunoa | "
     "https://www.washdog.cl/servicios/auto-lavado-perros-nunoa | "
     "https://www.washdog.cl/servicios/peluqueria-gatos-nunoa | "
     "https://www.washdog.cl/servicios/precio-peluqueria-nunoa | "
     "https://www.washdog.cl/blog/peluqueria-canina-nunoa. "
     "Esperar 3–7 días.",
     "https://search.google.com/search-console", "Alta", "Pendiente", ""],

    [4, "Google Analytics", "Crear propiedad GA4 y agregar al sitio",
     "NOTA: Si GA4 ya está configurado, marcar como Listo. "
     "(1) Ir a https://analytics.google.com → 'Crear cuenta' o 'Agregar propiedad'. "
     "(2) Nombre: WashDog | Zona horaria: Chile | Moneda: CLP. "
     "(3) Obtener el ID de medición (formato G-XXXXXXXX). "
     "(4) Enviarlo al equipo técnico para que lo agregue al sitio web. "
     "(5) Verificar que los datos lleguen en GA4 → Informes → Tiempo real.",
     "https://analytics.google.com", "Alta", "Pendiente", ""],

    [5, "Google Analytics", "Vincular GA4 con Google Search Console",
     "(1) En GA4 → Administrar → Vínculos de Search Console. "
     "(2) Hacer clic en 'Vincular' y seleccionar la propiedad washdog.cl. "
     "(3) Confirmar. Esto permite ver las keywords de búsqueda orgánica en GA4.",
     "https://analytics.google.com", "Media", "Pendiente", ""],
]

# ── Tab 6: Imágenes & Contenido ───────────────────────────────────────────────

TASKS_IMAGES = [
    [1, "Imágenes", "Preparar logo en los formatos necesarios",
     "Formatos necesarios: "
     "(1) PNG con fondo transparente (para directorios y redes). "
     "(2) PNG cuadrado 400x400 px (foto de perfil en redes y GBP). "
     "(3) PNG rectangular 820x312 px (portada de Facebook). "
     "Si no tienes el logo en estos formatos, usar remove.bg para quitar el fondo y Canva para redimensionar.",
     "", "Alta", "Pendiente", ""],

    [2, "Imágenes", "Tomar o conseguir fotos del local",
     "Fotos mínimas necesarias: "
     "(1) Foto exterior del local (fachada de Av. Irarrázaval 2086, Ñuñoa). "
     "(2) Foto interior de la sala de atención. "
     "(3) Foto de un perro siendo bañado o cortado. "
     "(4) Foto de un perro antes y después del grooming. "
     "Calidad mínima: 1080x1080 px. Buena iluminación, sin filtros exagerados. "
     "Usar las mismas fotos en GBP, directorios y redes sociales.",
     "", "Alta", "Pendiente", ""],

    [3, "Imágenes", "Subir imágenes a Google Business Profile",
     "(1) En GBP → 'Fotos'. Subir: logo (Logo), foto exterior (Exterior), interior (Interior), fotos de trabajo (En el trabajo). "
     "(2) Mínimo 5 fotos. Más fotos = más visibilidad en Google Maps. "
     "(3) Usar títulos descriptivos como 'Peluquería canina WashDog Ñuñoa'.",
     "https://business.google.com", "Alta", "Pendiente", ""],

    [4, "Imágenes", "Subir imágenes a redes sociales y directorios",
     "Subir el set completo de imágenes a: "
     "(1) Instagram: foto de perfil (logo) + primeras publicaciones. "
     "(2) Facebook: foto de perfil (logo) + portada. "
     "(3) TikTok: foto de perfil (logo). "
     "(4) YouTube: foto de perfil (logo) + portada del canal. "
     "(5) Todos los directorios: logo + 2–3 fotos del local. "
     "Usar las mismas imágenes en todos los canales para consistencia de marca.",
     "", "Alta", "Pendiente", ""],
]

# ── Tab 7: Reseñas & Alianzas ─────────────────────────────────────────────────

TASKS_REVIEWS = [
    [1, "Reseñas Google", "Conseguir las primeras 10 reseñas en Google",
     "(1) En GBP → ficha de WashDog → 'Obtener más reseñas' → copiar el link. "
     "(2) Enviar a los primeros 5–10 clientes por WhatsApp: "
     "'Hola [nombre], gracias por visitar WashDog 🐾. Si quedaste contento, nos ayudaría mucho si puedes dejarnos una reseña en Google: [link]. ¡Solo toma 1 minuto, muchas gracias!' "
     "(3) Meta: 10 reseñas de 5 estrellas en los primeros 30 días.",
     "https://business.google.com", "Alta", "Pendiente", ""],

    [2, "Reseñas Google", "Responder todas las reseñas recibidas",
     "Responder dentro de 24–48 horas. "
     "Reseñas positivas: agradecer, mencionar el nombre del perro si lo recuerdas, invitar a volver. "
     "Ejemplo: 'Muchas gracias [nombre], fue un placer atender a [nombre del perro]. ¡Los esperamos de vuelta en WashDog!' "
     "Reseñas negativas: disculparse, ofrecer solución, pedir contacto privado. Nunca discutir en público. "
     "Responder reseñas mejora el ranking en Google Maps.",
     "https://business.google.com", "Alta", "Pendiente", ""],

    [3, "Alianzas locales", "Contactar clínicas veterinarias de Ñuñoa y comunas cercanas",
     "(1) Buscar clínicas veterinarias en Ñuñoa, Providencia y La Reina. "
     "(2) Contactar por email o WhatsApp: 'Hola, somos WashDog, peluquería canina en Ñuñoa. Nos gustaría explorar una alianza: nosotros recomendamos su clínica y ustedes nos recomiendan a sus clientes. ¿Podemos conversar?' "
     "(3) Si aceptan: pedir que incluyan un link a https://www.washdog.cl en su sitio web (mejora el SEO). "
     "(4) Registrar resultado en columna Notas.",
     "", "Media", "Pendiente", ""],

    [4, "Alianzas locales", "Contactar tiendas de mascotas (Pet shops)",
     "(1) Buscar pet shops en Ñuñoa y comunas cercanas. "
     "(2) Proponer alianza de recomendación mutua + opción de descuento del 10% para clientes referidos. "
     "(3) Pedir que incluyan link a https://www.washdog.cl en su sitio web. "
     "(4) Registrar resultado en columna Notas.",
     "", "Media", "Pendiente", ""],

    [5, "Alianzas locales", "Contactar entrenadores de perros en Santiago",
     "(1) Buscar entrenadores caninos en Santiago (especialmente sector oriente). "
     "(2) Proponer: 'Nosotros te recomendamos como entrenador, tú nos recomiendas como peluquería.' "
     "(3) Idea de contenido conjunto: video de un perro entrenando + su transformación en WashDog (ideal para Instagram y TikTok).",
     "", "Baja", "Pendiente", ""],

    [6, "Prensa & Influencers", "Contactar blogs y medios locales de mascotas",
     "(1) Buscar blogs chilenos de mascotas o cuidado animal en Santiago. "
     "(2) Proponer mención en artículo de 'mejores peluquerías caninas en Santiago' a cambio de servicio gratuito o descuento. "
     "(3) Un link desde un blog de mascotas mejora directamente el SEO de washdog.cl.",
     "", "Baja", "Pendiente", ""],

    [7, "Prensa & Influencers", "Contactar influencers de mascotas en Chile",
     "(1) Buscar en Instagram y TikTok cuentas con +5.000 seguidores de mascotas en Chile. "
     "(2) Proponer: grooming gratuito a cambio de publicación con tag @washdog.cl y link en bio. "
     "(3) Priorizar influencers en Santiago, Ñuñoa y Providencia.",
     "", "Media", "Pendiente", ""],

    [8, "Booking", "Verificar sistema de reservas en todos los canales",
     "(1) Abrir https://www.washdog.cl en el celular y verificar que el botón de agenda funcione. "
     "(2) Confirmar que el link de reserva esté visible y funcional en: GBP, Instagram (bio), Facebook (botón Reservar), TikTok (bio) y todos los directorios con ficha activa. "
     "(3) Si hay algún problema técnico, reportar al equipo técnico con detalle del error.",
     "https://www.washdog.cl", "Alta", "Pendiente", ""],
]

# ── All tabs ──────────────────────────────────────────────────────────────────

ALL_TABS = [
    ("Fichas en Directorios", TASK_HEADERS, TASKS_DIRECTORIOS),
    ("Google Business Profile", TASK_HEADERS, TASKS_GBP),
    ("Redes Sociales", TASK_HEADERS, TASKS_SOCIAL),
    ("Herramientas Google", TASK_HEADERS, TASKS_GOOGLE_TOOLS),
    ("Imágenes & Contenido", TASK_HEADERS, TASKS_IMAGES),
    ("Reseñas & Alianzas", TASK_HEADERS, TASKS_REVIEWS),
]

# ── Formatting ────────────────────────────────────────────────────────────────

def _apply_task_tab_formatting(service, sheet_id: str, tab_id: int) -> None:
    service.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body={"requests": [
            {"repeatCell": {
                "range": {"sheetId": tab_id, "startRowIndex": 0, "endRowIndex": 1},
                "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                "fields": "userEnteredFormat.textFormat.bold",
            }},
            {"updateSheetProperties": {
                "properties": {"sheetId": tab_id, "gridProperties": {"frozenRowCount": 1}},
                "fields": "gridProperties.frozenRowCount",
            }},
            {"updateDimensionProperties": {
                "range": {"sheetId": tab_id, "dimension": "COLUMNS", "startIndex": 2, "endIndex": 4},
                "properties": {"pixelSize": 300},
                "fields": "pixelSize",
            }},
            {"updateDimensionProperties": {
                "range": {"sheetId": tab_id, "dimension": "COLUMNS", "startIndex": 6, "endIndex": 7},
                "properties": {"pixelSize": 130},
                "fields": "pixelSize",
            }},
            {"setDataValidation": {
                "range": {"sheetId": tab_id, "startRowIndex": 1, "endRowIndex": 1000,
                          "startColumnIndex": 6, "endColumnIndex": 7},
                "rule": {
                    "condition": {"type": "ONE_OF_LIST", "values": [
                        {"userEnteredValue": "Pendiente"},
                        {"userEnteredValue": "Listo"},
                    ]},
                    "showCustomUi": True, "strict": True,
                },
            }},
        ]},
    ).execute()


def _apply_dir_tab_formatting(service, sheet_id: str, tab_id: int) -> None:
    service.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body={"requests": [
            {"repeatCell": {
                "range": {"sheetId": tab_id, "startRowIndex": 0, "endRowIndex": 1},
                "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                "fields": "userEnteredFormat.textFormat.bold",
            }},
            {"updateSheetProperties": {
                "properties": {"sheetId": tab_id, "gridProperties": {"frozenRowCount": 1}},
                "fields": "gridProperties.frozenRowCount",
            }},
            {"updateDimensionProperties": {
                "range": {"sheetId": tab_id, "dimension": "COLUMNS", "startIndex": 4, "endIndex": 5},
                "properties": {"pixelSize": 240},
                "fields": "pixelSize",
            }},
            {"setDataValidation": {
                "range": {"sheetId": tab_id, "startRowIndex": 1, "endRowIndex": 100,
                          "startColumnIndex": 2, "endColumnIndex": 3},
                "rule": {
                    "condition": {"type": "ONE_OF_LIST", "values": [
                        {"userEnteredValue": "Por definir"},
                        {"userEnteredValue": "Crear nueva"},
                        {"userEnteredValue": "Reclamar existente"},
                    ]},
                    "showCustomUi": True, "strict": True,
                },
            }},
            {"setDataValidation": {
                "range": {"sheetId": tab_id, "startRowIndex": 1, "endRowIndex": 100,
                          "startColumnIndex": 3, "endColumnIndex": 4},
                "rule": {
                    "condition": {"type": "ONE_OF_LIST", "values": [
                        {"userEnteredValue": "Pendiente"},
                        {"userEnteredValue": "Enviado"},
                        {"userEnteredValue": "Verificado"},
                        {"userEnteredValue": "Optimizado"},
                    ]},
                    "showCustomUi": True, "strict": True,
                },
            }},
            {"setDataValidation": {
                "range": {"sheetId": tab_id, "startRowIndex": 1, "endRowIndex": 100,
                          "startColumnIndex": 6, "endColumnIndex": 7},
                "rule": {
                    "condition": {"type": "ONE_OF_LIST", "values": [
                        {"userEnteredValue": "No"},
                        {"userEnteredValue": "Sí"},
                    ]},
                    "showCustomUi": True, "strict": True,
                },
            }},
        ]},
    ).execute()


# ── Sheet management ──────────────────────────────────────────────────────────

def _get_all_tabs(service, sheet_id: str) -> dict:
    meta = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    return {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta["sheets"]}


def _ensure_tabs_exist(service, sheet_id: str, needed: list[str]) -> dict:
    tabs = _get_all_tabs(service, sheet_id)
    adds = [{"addSheet": {"properties": {"title": t}}} for t in needed if t not in tabs]
    if adds:
        service.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id, body={"requests": adds}).execute()
        tabs = _get_all_tabs(service, sheet_id)
    return tabs


def _write_all_data(service, sheet_id: str, tabs: dict) -> None:
    for tab_name, headers, tasks in ALL_TABS:
        service.spreadsheets().values().clear(
            spreadsheetId=sheet_id, range=f"'{tab_name}'!A:Z").execute()
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id, range=f"'{tab_name}'!A1",
            valueInputOption="RAW",
            body={"values": [headers] + tasks}).execute()
        _apply_task_tab_formatting(service, sheet_id, tabs[tab_name])

    service.spreadsheets().values().clear(
        spreadsheetId=sheet_id, range="'Directorios'!A:Z").execute()
    service.spreadsheets().values().update(
        spreadsheetId=sheet_id, range="'Directorios'!A1",
        valueInputOption="RAW",
        body={"values": [DIR_HEADERS] + DIRECTORIES}).execute()
    _apply_dir_tab_formatting(service, sheet_id, tabs["Directorios"])


def create_or_reset_sheet(reset: bool = False) -> str:
    service  = _sheets()
    sheet_id = _find_sheet_by_name(SHEET_NAME)

    all_tab_names = [t[0] for t in ALL_TABS] + ["Directorios"]

    if sheet_id and not reset:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
        print("[INFO] La hoja ya existe. Usa --reset para sobreescribir.")
        print(f"       URL: {url}")
        return sheet_id

    if sheet_id and reset:
        tabs = _ensure_tabs_exist(service, sheet_id, all_tab_names)
        _write_all_data(service, sheet_id, tabs)
    else:
        spreadsheet = service.spreadsheets().create(body={
            "properties": {"title": SHEET_NAME},
            "sheets": [{"properties": {"title": t}} for t in all_tab_names],
        }).execute()
        sheet_id = spreadsheet["spreadsheetId"]
        tabs = {s["properties"]["title"]: s["properties"]["sheetId"]
                for s in spreadsheet["sheets"]}
        _write_all_data(service, sheet_id, tabs)

    total_tasks = sum(len(t[2]) for t in ALL_TABS)
    print(f"[OK] Hoja actualizada: {total_tasks} tareas en {len(ALL_TABS)} pestañas + tabla de seguimiento Directorios")
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
    print(f"     URL: {url}")
    return sheet_id


def main():
    parser = argparse.ArgumentParser(description="Crear hoja de tareas SEO para WashDog")
    parser.add_argument("--reset", action="store_true", help="Limpiar y reescribir toda la hoja")
    args = parser.parse_args()
    create_or_reset_sheet(reset=args.reset)


if __name__ == "__main__":
    main()
