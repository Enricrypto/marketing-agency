# Phase 2 — Local Infrastructure & Python Setup

Objetivo: habilitar la ejecución de los 23 agentes de marketing usando Python y la API de Claude.

## Dependencias
- anthropic
- google-api-python-client, google-auth, google-auth-oauthlib, google-auth-httplib2
- gspread
- python-dotenv

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# → Editar .env con ANTHROPIC_API_KEY real
```

## Uso del runner
```bash
# Activar entorno primero
source .venv/bin/activate

# Ejecutar un agente
python runner.py --agent copywriting \
  --task "Escribe copy para landing page de fitness en Santiago"

# Con output tipo sheet
python runner.py --agent social-content \
  --task "Post para Instagram sobre vida saludable" \
  --output-type doc \
  --extra '{"keywords": ["fitness", "Santiago"]}'

# Especificar modelo
python runner.py --agent email-sequence \
  --task "Secuencia de bienvenida para nuevo usuario" \
  --model claude-sonnet-4-6
```

## Estructura de output
Cada ejecución guarda el output en:
- /outputs/docs/   → --output-type doc
- /outputs/sheets/ → --output-type sheet
- /outputs/drive/  → --output-type drive

Nombre de archivo: {agente}_{YYYYMMDD_HHMMSS}.txt

## Pendiente — Phase 3
- Integración real con Google Docs API (subir output a Drive)
- Integración con Google Sheets API (guardar datos tabulares)
