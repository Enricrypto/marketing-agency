"""
Marketing OS — Cliente Google Sheets
Crea hojas de cálculo y escribe filas de datos usando la Sheets API v4.
"""

from googleapiclient.discovery import build
from .auth import get_credentials


def _build_service():
    """Construye el cliente de Google Sheets."""
    return build("sheets", "v4", credentials=get_credentials())


def create_sheet(sheet_name: str, rows: list[list], folder_id: str | None = None) -> dict:
    """
    Crea una nueva Google Sheet con el nombre y filas dados.

    Args:
        sheet_name: Nombre de la hoja (título del Spreadsheet).
        rows:       Lista de filas [[col1, col2, ...], ...].
                    La primera fila se usa como encabezado.
        folder_id:  ID de carpeta en Drive (opcional).

    Returns:
        dict con 'sheet_id' y 'url'.
    """
    service = _build_service()

    # 1. Crear el spreadsheet con el nombre dado
    spreadsheet = service.spreadsheets().create(
        body={
            "properties": {"title": sheet_name},
            "sheets": [{"properties": {"title": sheet_name}}],
        }
    ).execute()

    sheet_id = spreadsheet["spreadsheetId"]

    # 2. Escribir filas en la primera hoja
    if rows:
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"{sheet_name}!A1",
            valueInputOption="RAW",
            body={"values": rows},
        ).execute()

    # 3. Mover a carpeta si se especificó folder_id
    if folder_id:
        from .drive_client import move_file
        move_file(sheet_id, folder_id)

    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
    print(f"[sheets] Hoja creada: {sheet_name} ({len(rows)} filas)")
    print(f"[sheets] URL: {url}")

    return {"sheet_id": sheet_id, "url": url, "sheet_name": sheet_name}


def append_rows(sheet_id: str, sheet_name: str, rows: list[list]) -> dict:
    """
    Agrega filas al final de una hoja existente.

    Args:
        sheet_id:   ID del spreadsheet.
        sheet_name: Nombre de la hoja (pestaña).
        rows:       Filas a agregar [[col1, col2, ...], ...].

    Returns:
        dict con 'sheet_id', 'url' y cantidad de filas agregadas.
    """
    service = _build_service()

    service.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range=f"{sheet_name}!A1",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": rows},
    ).execute()

    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
    print(f"[sheets] {len(rows)} filas agregadas a: {sheet_name}")
    return {"sheet_id": sheet_id, "url": url, "rows_added": len(rows)}
