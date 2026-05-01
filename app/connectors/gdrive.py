import io
import json
import logging
import os
from pathlib import Path
from typing import Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
SUPPORTED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.google-apps.document": ".pdf",                  
    "text/plain": ".txt",
}
METADATA_CACHE_FILE = "data/metadata_cache.json"
DOWNLOAD_DIR = "data/downloaded_files"

def _load_metadata_cache() -> dict:
    if os.path.exists(METADATA_CACHE_FILE):
        with open(METADATA_CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

def _save_metadata_cache(cache: dict) -> None:
    Path(METADATA_CACHE_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(METADATA_CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

def _build_drive_service(service_account_path: str):
    import os, json as _json
    if not os.path.exists(service_account_path):
        import streamlit as st
        if "GOOGLE_SERVICE_ACCOUNT_JSON" in st.secrets:
            raw = st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"]
            # Streamlit may parse TOML tables as AttrDict — convert directly
            if hasattr(raw, "to_dict"):
                info = raw.to_dict()
            elif isinstance(raw, dict):
                info = dict(raw)
            else:
                # Raw string — fix doubly-escaped newlines in private_key before parsing
                info = _json.loads(str(raw).replace("\\n", "\n"))
            creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
            return build("drive", "v3", credentials=creds, cache_discovery=False)
        raise FileNotFoundError(
            "Service account not found. Add GOOGLE_SERVICE_ACCOUNT_JSON to Streamlit secrets."
        )
    creds = service_account.Credentials.from_service_account_file(
        service_account_path, scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)

def list_drive_files(
    service_account_path: str,
    folder_id: Optional[str] = None,
) -> list[dict]:
    service = _build_drive_service(service_account_path)
    query_parts = ["trashed = false"]

    mime_filter = " or ".join(
        [f"mimeType = '{m}'" for m in SUPPORTED_MIME_TYPES]
    )
    query_parts.append(f"({mime_filter})")

    if folder_id:
        query_parts.append(f"'{folder_id}' in parents")

    query = " and ".join(query_parts)
    files = []
    page_token = None

    while True:
        resp = (
            service.files()
            .list(
                q=query,
                spaces="drive",
                fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
                pageToken=page_token,
            )
            .execute()
        )
        files.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    logger.info("Found %d supported files in Google Drive.", len(files))
    return [f for f in files if f.get("name")]

def download_file(
    service_account_path: str,
    file_id: str,
    mime_type: str,
    file_name: str,
) -> str:
    service = _build_drive_service(service_account_path)
    Path(DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)
    ext = SUPPORTED_MIME_TYPES.get(mime_type, ".bin")
    safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in file_name)
    local_path = os.path.join(DOWNLOAD_DIR, f"{file_id}_{safe_name}{ext if not safe_name.endswith(ext) else ''}")

    buffer = io.BytesIO()
    if mime_type == "application/vnd.google-apps.document":
        request = service.files().export_media(
            fileId=file_id, mimeType="application/pdf"
        )
    else:
        request = service.files().get_media(fileId=file_id)

    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    with open(local_path, "wb") as f:
        f.write(buffer.getvalue())

    logger.info("Downloaded '%s' → %s", file_name, local_path)
    return local_path

def sync_google_drive(
    service_account_path: str,
    folder_id: Optional[str] = None,
    progress_callback=None,
) -> list[dict]:
    cache = _load_metadata_cache()
    drive_files = list_drive_files(service_account_path, folder_id)
    new_files = []

    for idx, file_info in enumerate(drive_files):
        fid = file_info["id"]
        modified = file_info.get("modifiedTime", "")

        if fid in cache and cache[fid].get("modifiedTime") == modified:
            logger.debug("Skipping unchanged file: %s", file_info["name"])
            if progress_callback:
                progress_callback(idx + 1, len(drive_files), file_info["name"], skipped=True)
            continue

        try:
            local_path = download_file(
                service_account_path,
                fid,
                file_info["mimeType"],
                file_info["name"],
            )
            metadata = {
                "doc_id": fid,
                "file_name": file_info["name"],
                "mime_type": file_info["mimeType"],
                "modifiedTime": modified,
                "local_path": local_path,
                "source": "gdrive",
            }
            cache[fid] = metadata
            new_files.append(metadata)
        except Exception as exc:
            logger.error("Failed to download '%s': %s", file_info["name"], exc)

        if progress_callback:
            progress_callback(idx + 1, len(drive_files), file_info["name"], skipped=False)

    _save_metadata_cache(cache)
    logger.info("Sync complete. %d new/updated files.", len(new_files))
    return new_files

def get_all_cached_files() -> list[dict]:
    cache = _load_metadata_cache()
    return list(cache.values())
