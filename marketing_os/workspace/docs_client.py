"""
Marketing OS — Cliente Google Docs
Crea documentos y escribe contenido de texto plano usando la Docs API v1.
"""

from googleapiclient.discovery import build
from .auth import get_credentials


def _build_service():
    """Construye el cliente de Google Docs."""
    return build("docs", "v1", credentials=get_credentials())


def create_doc(title: str, content: str, folder_id: str | None = None) -> dict:
    """
    Crea un nuevo Google Doc con el título y contenido dados.

    Args:
        title:     Título del documento.
        content:   Contenido de texto plano a insertar.
        folder_id: ID de carpeta en Drive donde guardar el Doc (opcional).

    Returns:
        dict con 'doc_id' y 'url' del documento creado.
    """
    service = _build_service()

    # 1. Crear el documento con el título
    doc = service.documents().create(body={"title": title}).execute()
    doc_id = doc["documentId"]

    # 2. Insertar contenido de texto al final del documento
    requests = [
        {
            "insertText": {
                "location": {"index": 1},
                "text": content,
            }
        }
    ]
    service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": requests},
    ).execute()

    # 3. Mover a carpeta en Drive si se especificó folder_id
    if folder_id:
        from .drive_client import move_file
        move_file(doc_id, folder_id)

    url = f"https://docs.google.com/document/d/{doc_id}/edit"
    print(f"[docs] Documento creado: {title}")
    print(f"[docs] URL: {url}")

    return {"doc_id": doc_id, "url": url, "title": title}


def update_doc(doc_id: str, content: str) -> dict:
    """
    Reemplaza todo el contenido de un Doc existente.

    Args:
        doc_id:  ID del documento a actualizar.
        content: Nuevo contenido de texto plano.

    Returns:
        dict con 'doc_id' y 'url'.
    """
    service = _build_service()

    # Obtener longitud actual del documento para limpiar contenido
    doc = service.documents().get(documentId=doc_id).execute()
    body = doc.get("body", {})
    content_elements = body.get("content", [])

    # Calcular índice final del contenido actual (excluyendo el último \n obligatorio)
    end_index = 1
    if content_elements:
        last = content_elements[-1]
        end_index = last.get("endIndex", 1) - 1

    requests = []

    # Borrar contenido existente si hay algo
    if end_index > 1:
        requests.append({
            "deleteContentRange": {
                "range": {"startIndex": 1, "endIndex": end_index}
            }
        })

    # Insertar nuevo contenido
    requests.append({
        "insertText": {
            "location": {"index": 1},
            "text": content,
        }
    })

    service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": requests},
    ).execute()

    url = f"https://docs.google.com/document/d/{doc_id}/edit"
    print(f"[docs] Documento actualizado: {doc_id}")
    return {"doc_id": doc_id, "url": url}
