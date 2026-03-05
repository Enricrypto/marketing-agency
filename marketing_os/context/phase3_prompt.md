# Phase 3 — Google Workspace Integration

Objetivo: subir outputs de los agentes directamente a Google Docs, Sheets y Drive.

## APIs habilitadas en Google Cloud Console
- Google Drive API ✅
- Google Docs API ✅
- Google Sheets API ✅

## Service Account
- Crear en: Google Cloud Console → IAM → Service Accounts
- Rol requerido: Editor
- Descargar JSON de credenciales → guardar en: `workspace/service_account.json`
- Agregar en .env: `GOOGLE_APPLICATION_CREDENTIALS=workspace/service_account.json`

> ⚠️ La carpeta se llama `workspace/` (no `google/`) para evitar conflicto de
> namespace con las librerías instaladas google-auth y google-api-python-client.

## Estructura de archivos

```
workspace/
├── api.py        → create_doc(), append_to_sheet(), upload_file_to_drive()
├── auth.py       → (legacy — reemplazado por api.py)
├── __init__.py   → Exporta funciones de api.py
└── service_account.json  ← NO subir a git
```

## Carpeta en Drive (creada automáticamente)

```
MarketingOS/
  ├── docs/    ← Google Docs (output_type: doc)
  ├── sheets/  ← Google Sheets (output_type: sheet)
  └── drive/   ← Archivos .txt (output_type: drive)
```

## Uso CLI

```bash
source .venv/bin/activate

# Doc → crea Google Doc en Drive/MarketingOS/docs/
python runner.py --agent copywriting \
  --task "Escribe copy para landing page de fitness en Santiago"

# Sheet → crea Google Sheet en Drive/MarketingOS/sheets/
python runner.py --agent social-content \
  --task "Calendario de contenido Instagram — Marzo 2026" \
  --output-type sheet

# Drive → sube .txt a Drive/MarketingOS/drive/
python runner.py --agent marketing-ideas \
  --task "Ideas de marketing para gym en Santiago" \
  --output-type drive

# Con título personalizado
python runner.py --agent email-sequence \
  --task "Secuencia bienvenida 5 emails" \
  --extra '{"title": "Email Bienvenida — Clientes Nuevos"}'
```

## Comportamiento sin credenciales
Si `workspace/service_account.json` no existe, el runner:
- Guarda el output solo localmente en `/outputs/`
- Muestra `[workspace] No disponible: ...` pero NO falla
- Retorna `{"google": null, "saved_path": "...", "content": "..."}`

## Para probar la integración

```bash
# Test rápido sin gastar tokens de Claude
python -c "
from workspace.api import get_or_create_folder
folder_id = get_or_create_folder('MarketingOS_Test')
print('OK — folder_id:', folder_id)
"
```
