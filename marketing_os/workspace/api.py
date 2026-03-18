"""
Marketing OS — Google Workspace API (Phase 3b — OAuth)
Funciones unificadas para crear Docs, actualizar Sheets y subir archivos a Drive.

Autenticación: OAuth 2.0 (Desktop App) — compatible con políticas de org que
prohíben claves de Service Account.

Primer uso:
    Abre el navegador → inicia sesión con tu cuenta Google → otorga acceso.
    El token se guarda en workspace/token.json para ejecuciones posteriores.

Requiere:
    - workspace/credentials.json  (OAuth client ID descargado de Google Cloud Console)
    - APIs habilitadas: Google Drive, Google Docs, Google Sheets

Uso:
    from workspace.api import create_doc, append_to_sheet, upload_file_to_drive
"""

import os
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ──────────────────────────────────────────────
# AUTENTICACIÓN — OAuth 2.0
# ──────────────────────────────────────────────

_BASE_DIR = Path(__file__).parent.parent
_WORKSPACE_DIR = Path(__file__).parent

# drive.file → solo archivos creados por esta app (política más restrictiva y segura)
_SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/webmasters",          # full access — needed for sitemap submission
    "https://www.googleapis.com/auth/business.manage",     # Google Business Profile API
    "https://www.googleapis.com/auth/indexing",            # Web Search Indexing API — request URL indexing
]


def _get_credentials() -> Credentials:
    """
    Obtiene credenciales OAuth 2.0 para Google Workspace.

    Flujo:
    1. Si existe workspace/.token.json con token válido → lo usa directamente.
    2. Si el token expiró pero hay refresh_token → lo renueva automáticamente.
    3. Si no hay token → abre el navegador para autenticación inicial.
       El token resultante se guarda en workspace/.token.json para futuros usos.

    Requiere: workspace/credentials.json (OAuth client ID tipo Desktop App)
    Env var:  GOOGLE_OAUTH_CREDENTIALS (opcional, sobreescribe la ruta por defecto)
    """
    # Ruta de credenciales: env var > default
    creds_env        = os.environ.get("GOOGLE_OAUTH_CREDENTIALS", "")
    credentials_path = (
        Path(creds_env) if Path(creds_env).is_absolute()
        else (_BASE_DIR / creds_env if creds_env else _WORKSPACE_DIR / "credentials.json")
    )
    # Token con punto para ocultarlo por convención (no subir a git)
    token_path = _WORKSPACE_DIR / ".token.json"

    if not credentials_path.exists():
        raise FileNotFoundError(
            f"[workspace] credentials.json no encontrado: {credentials_path}\n"
            "Descárgalo desde Google Cloud Console:\n"
            "  APIs & Services → Credentials → OAuth 2.0 Client IDs → Desktop app → Download JSON\n"
            "Guárdalo en: workspace/credentials.json\n"
            "O define GOOGLE_OAUTH_CREDENTIALS en tu .env"
        )

    creds = None

    # Cargar token existente
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), _SCOPES)

    # Renovar token expirado o iniciar flujo de login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            print("[workspace] Token OAuth renovado automáticamente.")
        else:
            print("[workspace] Iniciando autenticación OAuth — se abrirá el navegador...")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path), _SCOPES
            )
            creds = flow.run_local_server(port=0)
            print("[workspace] Autenticación exitosa.")

        # Guardar token para la próxima ejecución (oculto con punto)
        token_path.write_text(creds.to_json(), encoding="utf-8")
        print(f"[workspace] Token guardado en: {token_path}")

    return creds


def _docs():
    return build("docs", "v1", credentials=_get_credentials())


def _sheets():
    return build("sheets", "v4", credentials=_get_credentials())


def _drive():
    return build("drive", "v3", credentials=_get_credentials())


# ──────────────────────────────────────────────
# GOOGLE DOCS
# ──────────────────────────────────────────────

def create_doc(title: str, content: str, folder_id: str | None = None) -> str:
    """
    Crea un nuevo Google Doc con el título y contenido dados.

    Args:
        title:     Título del documento.
        content:   Texto plano a insertar (output de Claude).
        folder_id: ID de carpeta en Drive donde guardar el Doc (opcional).

    Returns:
        doc_id (str) — ID del documento creado.
    """
    service = _docs()

    # Crear documento vacío con el título
    doc = service.documents().create(body={"title": title}).execute()
    doc_id = doc["documentId"]

    # Insertar contenido en el índice 1 (inicio del cuerpo)
    service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": [{"insertText": {"location": {"index": 1}, "text": content}}]},
    ).execute()

    # Mover a carpeta si se especificó
    if folder_id:
        _move_to_folder(doc_id, folder_id)

    print(f"[workspace] Doc creado: '{title}'")
    print(f"[workspace] URL: https://docs.google.com/document/d/{doc_id}/edit")
    return doc_id


# ──────────────────────────────────────────────
# GOOGLE SHEETS
# ──────────────────────────────────────────────

def append_to_sheet(sheet_name: str, values: list[list], folder_id: str | None = None) -> str:
    """
    Agrega filas a una Google Sheet. La crea automáticamente si no existe en Drive.

    Args:
        sheet_name: Nombre del Spreadsheet (también nombre de la pestaña).
        values:     Lista de filas [[col1, col2, ...], ...].
                    La primera fila se usa como encabezado si la hoja es nueva.
        folder_id:  ID de carpeta en Drive (opcional).

    Returns:
        sheet_id (str) — ID del spreadsheet creado o actualizado.
    """
    service = _sheets()

    # Buscar spreadsheet existente por nombre en Drive
    sheet_id = _find_sheet_by_name(sheet_name)

    if sheet_id:
        # Agregar filas al final de la hoja existente
        service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range=f"{sheet_name}!A1",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": values},
        ).execute()
        print(f"[workspace] {len(values)} fila(s) agregadas a: '{sheet_name}'")
    else:
        # Crear spreadsheet nuevo y escribir desde el inicio
        spreadsheet = service.spreadsheets().create(
            body={
                "properties": {"title": sheet_name},
                "sheets": [{"properties": {"title": sheet_name}}],
            }
        ).execute()
        sheet_id = spreadsheet["spreadsheetId"]

        if values:
            service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range=f"{sheet_name}!A1",
                valueInputOption="RAW",
                body={"values": values},
            ).execute()

        if folder_id:
            _move_to_folder(sheet_id, folder_id)

        print(f"[workspace] Sheet creada: '{sheet_name}' ({len(values)} filas)")

    print(f"[workspace] URL: https://docs.google.com/spreadsheets/d/{sheet_id}/edit")
    return sheet_id


def _find_sheet_by_name(name: str) -> str | None:
    """Busca un Spreadsheet por nombre en Drive. Retorna su ID o None."""
    service = _drive()
    results = service.files().list(
        q=(
            f"name='{name}' "
            f"and mimeType='application/vnd.google-apps.spreadsheet' "
            f"and trashed=false"
        ),
        spaces="drive",
        fields="files(id)",
    ).execute()
    files = results.get("files", [])
    return files[0]["id"] if files else None


# ──────────────────────────────────────────────
# GOOGLE DRIVE
# ──────────────────────────────────────────────

def upload_file_to_drive(file_path: str, folder_id: str | None = None,
                         mime_type: str = "text/plain") -> str:
    """
    Sube un archivo local a Google Drive.

    Args:
        file_path: Ruta local del archivo a subir.
        folder_id: ID de carpeta destino en Drive (opcional).
        mime_type: Tipo MIME del archivo (default: text/plain).

    Returns:
        file_id (str) — ID del archivo subido a Drive.
    """
    service = _drive()
    path = Path(file_path)

    metadata: dict = {"name": path.name}
    if folder_id:
        metadata["parents"] = [folder_id]

    media = MediaFileUpload(str(path), mimetype=mime_type)
    file = service.files().create(
        body=metadata,
        media_body=media,
        fields="id",
    ).execute()

    file_id = file["id"]
    print(f"[workspace] Archivo subido: '{path.name}'")
    print(f"[workspace] URL: https://drive.google.com/file/d/{file_id}/view")
    return file_id


def get_or_create_folder(folder_name: str, parent_id: str | None = None) -> str:
    """
    Busca una carpeta en Drive por nombre. La crea si no existe.

    Args:
        folder_name: Nombre de la carpeta.
        parent_id:   ID de carpeta padre (opcional).

    Returns:
        ID de la carpeta.
    """
    service = _drive()

    query = (
        f"name='{folder_name}' "
        f"and mimeType='application/vnd.google-apps.folder' "
        f"and trashed=false"
    )
    if parent_id:
        query += f" and '{parent_id}' in parents"

    results = service.files().list(
        q=query, spaces="drive", fields="files(id, name)"
    ).execute()
    files = results.get("files", [])

    if files:
        return files[0]["id"]

    # Crear carpeta nueva
    metadata: dict = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        metadata["parents"] = [parent_id]

    folder = service.files().create(body=metadata, fields="id").execute()
    print(f"[workspace] Carpeta creada: '{folder_name}'")
    return folder["id"]


def _move_to_folder(file_id: str, folder_id: str) -> None:
    """Mueve un archivo a la carpeta especificada en Drive."""
    service = _drive()
    file = service.files().get(fileId=file_id, fields="parents").execute()
    current_parents = ",".join(file.get("parents", []))
    service.files().update(
        fileId=file_id,
        addParents=folder_id,
        removeParents=current_parents,
        fields="id, parents",
    ).execute()


# ──────────────────────────────────────────────
# GOOGLE BUSINESS PROFILE
# ──────────────────────────────────────────────

def _gbp_accounts():
    """Google Business Profile — Account Management API."""
    return build(
        "mybusinessaccountmanagement", "v1",
        credentials=_get_credentials(),
        discoveryServiceUrl="https://mybusinessaccountmanagement.googleapis.com/$discovery/rest?version=v1",
        static_discovery=False,
    )


def _gbp_posts(account_name: str, location_name: str):
    """Google Business Profile — Posts API (scoped to a location)."""
    return build(
        "mybusinessposts", "v1",
        credentials=_get_credentials(),
        discoveryServiceUrl="https://mybusinessposts.googleapis.com/$discovery/rest?version=v1",
        static_discovery=False,
    )


def _gbp_info():
    """Google Business Profile — Business Information API."""
    return build(
        "mybusinessbusinessinformation", "v1",
        credentials=_get_credentials(),
        discoveryServiceUrl="https://mybusinessbusinessinformation.googleapis.com/$discovery/rest?version=v1",
        static_discovery=False,
    )


def gbp_get_location() -> tuple[str, str]:
    """
    Returns (account_name, location_name) for the first GBP location found.
    Caches result in env var GBP_LOCATION_NAME / GBP_ACCOUNT_NAME.

    Example:
        account_name  = "accounts/123456789"
        location_name = "accounts/123456789/locations/987654321"
    """
    cached_loc     = os.environ.get("GBP_LOCATION_NAME", "")
    cached_account = os.environ.get("GBP_ACCOUNT_NAME", "")
    if cached_loc and cached_account:
        return cached_account, cached_loc

    svc = _gbp_accounts()
    accounts = svc.accounts().list().execute().get("accounts", [])
    if not accounts:
        raise RuntimeError("[GBP] No se encontraron cuentas de Google Business Profile.")

    account_name = accounts[0]["name"]
    print(f"[GBP] Cuenta: {account_name}")

    info_svc   = _gbp_info()
    locations  = info_svc.locations().list(
        parent=account_name,
        readMask="name,title",
    ).execute().get("locations", [])

    if not locations:
        raise RuntimeError(f"[GBP] No se encontraron ubicaciones para {account_name}.")

    location_name = locations[0]["name"]
    print(f"[GBP] Ubicación: {location_name} — {locations[0].get('title', '')}")
    return account_name, location_name


def gbp_create_post(
    text: str,
    call_to_action_type: str = "LEARN_MORE",
    cta_url: str | None = None,
    location_name: str | None = None,
) -> dict:
    """
    Publica un post en Google Business Profile.

    Args:
        text:                 Texto del post (máx 1,500 caracteres).
        call_to_action_type:  "LEARN_MORE" | "BOOK" | "ORDER" | "CALL" | None
        cta_url:              URL para el botón CTA (si aplica).
        location_name:        "accounts/xxx/locations/yyy" — si None, auto-detecta.

    Returns:
        Respuesta de la API con el post creado.
    """
    if location_name is None:
        _, location_name = gbp_get_location()

    text = text[:1500]  # GBP limit

    post_body: dict = {
        "languageCode": "es",
        "summary":      text,
        "topicType":    "STANDARD",
    }

    if call_to_action_type and cta_url:
        post_body["callToAction"] = {
            "actionType": call_to_action_type,
            "url":        cta_url,
        }

    svc    = _gbp_posts(location_name, location_name)
    result = svc.locations().localPosts().create(
        parent=location_name,
        body=post_body,
    ).execute()

    print(f"[GBP] Post publicado: {result.get('name', '')}")
    return result
