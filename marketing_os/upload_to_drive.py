#!/usr/bin/env python3
"""
Marketing OS — Upload all WashDog assets to Google Drive

Creates this folder structure in Drive:

WashDog Marketing/
├── 📊 SEO & Analytics/
│   ├── Newsletters/          ← content/newsletter/*.md
│   └── Blog Posts/           ← outputs/blogs/ (if any)
├── 🎨 Social Media/
│   ├── Instagram Templates/  ← social_assets/templates/**
│   ├── Icons/                ← social_assets/icons/**
│   ├── Captions & Hashtags/  ← captions + hashtags
│   └── Style Guide/          ← styles/
└── 🖨️ Print Materials/
    └── Posters & Banners/    ← outputs/posters/

Usage:
    cd marketing_os
    .venv/bin/python upload_to_drive.py
    .venv/bin/python upload_to_drive.py --dry-run
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", override=True)

sys.path.insert(0, str(Path(__file__).parent))

from workspace.api import get_or_create_folder, upload_file_to_drive

# ── MIME type map ──────────────────────────────────────────────────────────────
_MIME = {
    ".html": "text/html",
    ".css":  "text/css",
    ".svg":  "image/svg+xml",
    ".pdf":  "application/pdf",
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".json": "application/json",
    ".md":   "text/markdown",
    ".txt":  "text/plain",
    ".sh":   "text/plain",
}

_BASE = Path(__file__).parent


def mime(path: Path) -> str:
    return _MIME.get(path.suffix.lower(), "application/octet-stream")


def upload(path: Path, folder_id: str, dry_run: bool) -> None:
    if not path.is_file():
        return
    # Skip hidden files, __pycache__, compiled files
    if path.name.startswith(".") or path.name.startswith("__") or path.suffix in (".pyc",):
        return
    if dry_run:
        print(f"  [dry-run] Would upload: {path.name}")
        return
    upload_file_to_drive(str(path), folder_id=folder_id, mime_type=mime(path))


def upload_dir(directory: Path, folder_id: str, dry_run: bool, recursive: bool = False) -> None:
    """Upload all files in a directory to a Drive folder."""
    if not directory.exists():
        print(f"  [skip] Directory not found: {directory}")
        return
    for f in sorted(directory.iterdir()):
        if f.is_file():
            upload(f, folder_id, dry_run)
        elif f.is_dir() and recursive and not f.name.startswith("."):
            sub_id = get_or_create_folder(f.name, parent_id=folder_id) if not dry_run else folder_id
            upload_dir(f, sub_id, dry_run, recursive=True)


def main():
    parser = argparse.ArgumentParser(description="Upload WashDog assets to Google Drive")
    parser.add_argument("--dry-run", action="store_true", help="Preview without uploading")
    args = parser.parse_args()

    dry = args.dry_run
    if dry:
        print("[drive] DRY RUN — no files will be uploaded\n")

    # ── Root folder ─────────────────────────────────────────────────────────
    print("📁 Creating folder structure...")
    root = get_or_create_folder("WashDog Marketing") if not dry else "root"

    # ── SEO & Analytics ─────────────────────────────────────────────────────
    seo_folder      = get_or_create_folder("📊 SEO & Analytics",    root) if not dry else root
    newsletter_fold = get_or_create_folder("Newsletters",           seo_folder) if not dry else root
    blog_fold       = get_or_create_folder("Blog Posts",            seo_folder) if not dry else root

    # ── Social Media ────────────────────────────────────────────────────────
    social_folder   = get_or_create_folder("🎨 Social Media",       root) if not dry else root
    tmpl_folder     = get_or_create_folder("Instagram Templates",   social_folder) if not dry else root
    icons_folder    = get_or_create_folder("Icons",                 social_folder) if not dry else root
    hl_icons_folder = get_or_create_folder("Highlight Icons",       icons_folder) if not dry else root
    ct_icons_folder = get_or_create_folder("Content Icons",         icons_folder) if not dry else root
    capt_folder     = get_or_create_folder("Captions & Hashtags",   social_folder) if not dry else root
    style_folder    = get_or_create_folder("Style Guide",           social_folder) if not dry else root

    # ── Post templates subfolders ────────────────────────────────────────────
    post_folder     = get_or_create_folder("Posts",                 tmpl_folder) if not dry else root
    carousel_folder = get_or_create_folder("Carousels",             tmpl_folder) if not dry else root

    # ── Print Materials ──────────────────────────────────────────────────────
    print_folder    = get_or_create_folder("🖨️ Print Materials",    root) if not dry else root
    posters_folder  = get_or_create_folder("Posters & Banners",     print_folder) if not dry else root

    print("\n📤 Uploading files...\n")

    # ── Newsletters ──────────────────────────────────────────────────────────
    nl_src = _BASE.parent.parent / "washdog-website" / "content" / "newsletter"
    if nl_src.exists():
        print("  → Newsletters")
        upload_dir(nl_src, newsletter_fold, dry)
    else:
        print("  [skip] No newsletter content found")

    # ── Blog Posts ───────────────────────────────────────────────────────────
    blog_src = _BASE / "outputs" / "blogs"
    if blog_src.exists():
        print("  → Blog Posts")
        upload_dir(blog_src, blog_fold, dry)
    else:
        print("  [skip] No blog outputs found")

    # ── Instagram Post Templates ─────────────────────────────────────────────
    print("  → Instagram Post Templates")
    upload_dir(_BASE / "social_assets" / "templates" / "post",     post_folder,     dry)
    upload_dir(_BASE / "social_assets" / "templates" / "carousel", carousel_folder, dry)

    # ── Icons ────────────────────────────────────────────────────────────────
    print("  → Highlight Icons")
    upload_dir(_BASE / "social_assets" / "icons" / "highlight-icons", hl_icons_folder, dry)

    print("  → Content Icons")
    upload_dir(_BASE / "social_assets" / "icons" / "content-icons", ct_icons_folder, dry)

    # ── Captions & Hashtags ──────────────────────────────────────────────────
    print("  → Captions & Hashtags")
    upload_dir(_BASE / "social_assets" / "captions",  capt_folder, dry)
    upload_dir(_BASE / "social_assets" / "hashtags",  capt_folder, dry)

    # ── Style Guide ──────────────────────────────────────────────────────────
    print("  → Style Guide")
    upload_dir(_BASE / "social_assets" / "styles",    style_folder, dry)
    readme = _BASE / "social_assets" / "README.md"
    upload(readme, style_folder, dry)

    # ── Posters & Banners ────────────────────────────────────────────────────
    print("  → Posters & Banners")
    upload_dir(_BASE / "outputs" / "posters", posters_folder, dry)

    print("\n✅ Done!")
    if not dry:
        print("🔗 Find everything in Google Drive → 'WashDog Marketing'")


if __name__ == "__main__":
    main()
