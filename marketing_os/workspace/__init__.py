"""
Marketing OS — Google Workspace Package
Importa las funciones principales desde api.py.
"""

from .api import (
    create_doc,
    append_to_sheet,
    upload_file_to_drive,
    get_or_create_folder,
)

__all__ = [
    "create_doc",
    "append_to_sheet",
    "upload_file_to_drive",
    "get_or_create_folder",
]
