"""
Marketing OS — Autenticación Google Workspace
Carga credenciales desde service_account.json usando Service Account.
"""

import os
from pathlib import Path
from google.oauth2 import service_account

# Alcances necesarios para Docs, Sheets y Drive
SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

BASE_DIR = Path(__file__).parent.parent


def get_credentials():
    """
    Retorna credenciales de Google usando Service Account.

    Busca el archivo JSON en:
    1. Variable de entorno GOOGLE_APPLICATION_CREDENTIALS
    2. Ruta por defecto: google/service_account.json
    """
    credentials_path = os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS",
        str(BASE_DIR / "google" / "service_account.json"),
    )

    creds_file = Path(credentials_path)
    if not creds_file.exists():
        raise FileNotFoundError(
            f"[error] Archivo de credenciales no encontrado: {creds_file}\n"
            "Descarga el JSON de tu Service Account desde Google Cloud Console\n"
            "y guárdalo en: google/service_account.json"
        )

    credentials = service_account.Credentials.from_service_account_file(
        str(creds_file),
        scopes=SCOPES,
    )
    return credentials
