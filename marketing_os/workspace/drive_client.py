"""
Marketing OS — Cliente Google Drive
Gestiona carpetas y archivos en Drive usando la Drive API v3.
"""

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from .auth import get_credentials


def _build_service():
    """Construye el cliente de Google Drive."""
    return build("drive", "v3", credentials=get_credentials())


def get_or_create_folder(folder_name: str, parent_id: str | None = None) -> str:
    """
    Busca una carpeta por nombre en Drive. Si no existe, la crea.

    Args:
        folder_name: Nombre de la carpeta.
        parent_id:   ID de carpeta padre (opcional).

    Returns:
        ID de la carpeta encontrada o creada.
    """
    service = _build_service()

    # Construir query de búsqueda
    query = (
        f"name='{folder_name}' "
        f"and mimeType='application/vnd.google-apps.folder' "
        f"and trashed=false"
    )
    if parent_id:
        query += f" and '{parent_id}' in parents"

    results = service.files().list(
        q=query,
        spaces="drive",
        fields="files(id, name)",
    ).execute()

    files = results.get("files", [])
    if files:
        folder_id = files[0]["id"]
        print(f"[drive] Carpeta existente: {folder_name} ({folder_id})")
        return folder_id

    # No existe: crear carpeta
    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        metadata["parents"] = [parent_id]

    folder = service.files().create(
        body=metadata,
        fields="id",
    ).execute()

    folder_id = folder["id"]
    print(f"[drive] Carpeta creada: {folder_name} ({folder_id})")
    return folder_id


def move_file(file_id: str, folder_id: str) -> None:
    """
    Mueve un archivo (Doc, Sheet, etc.) a una carpeta de Drive.

    Args:
        file_id:   ID del archivo a mover.
        folder_id: ID de la carpeta destino.
    """
    service = _build_service()

    # Obtener padres actuales del archivo
    file = service.files().get(fileId=file_id, fields="parents").execute()
    current_parents = ",".join(file.get("parents", []))

    # Mover: agregar nueva carpeta y quitar las anteriores
    service.files().update(
        fileId=file_id,
        addParents=folder_id,
        removeParents=current_parents,
        fields="id, parents",
    ).execute()

    print(f"[drive] Archivo {file_id} movido a carpeta {folder_id}")


def upload_file(local_path: str, drive_filename: str, folder_id: str | None = None,
                mime_type: str = "text/plain") -> dict:
    """
    Sube un archivo local a Google Drive.

    Args:
        local_path:     Ruta local del archivo a subir.
        drive_filename: Nombre que tendrá en Drive.
        folder_id:      ID de carpeta destino (opcional).
        mime_type:      Tipo MIME del archivo (default: text/plain).

    Returns:
        dict con 'file_id' y 'url'.
    """
    service = _build_service()

    metadata = {"name": drive_filename}
    if folder_id:
        metadata["parents"] = [folder_id]

    media = MediaFileUpload(local_path, mimetype=mime_type)

    file = service.files().create(
        body=metadata,
        media_body=media,
        fields="id",
    ).execute()

    file_id = file["id"]
    url = f"https://drive.google.com/file/d/{file_id}/view"
    print(f"[drive] Archivo subido: {drive_filename} ({file_id})")
    return {"file_id": file_id, "url": url}


def list_folder(folder_id: str) -> list[dict]:
    """
    Lista los archivos dentro de una carpeta de Drive.

    Returns:
        Lista de dicts con 'id', 'name' y 'mimeType'.
    """
    service = _build_service()

    results = service.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        spaces="drive",
        fields="files(id, name, mimeType)",
    ).execute()

    return results.get("files", [])
