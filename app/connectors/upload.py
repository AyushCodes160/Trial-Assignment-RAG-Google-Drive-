import logging
import os
import shutil
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

DOWNLOAD_DIR = "data/downloaded_files"

def sync_uploaded_files(uploaded_files, progress_callback=None) -> list[dict]:
    """
    Saves Streamlit UploadedFile objects to the data directory 
    and returns a list of document dicts.
    """
    if not uploaded_files:
        return []
        
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    documents = []
    
    total = len(uploaded_files)
    
    for i, file in enumerate(uploaded_files):
        if progress_callback:
            progress_callback(i, total, f"Saving {file.name}...")
            
        # Create a unique ID for the file
        doc_id = f"upload_{uuid.uuid4().hex[:8]}"
        safe_name = file.name.replace("/", "_").replace("\\", "_")
        local_path = os.path.join(DOWNLOAD_DIR, f"{doc_id}_{safe_name}")
        
        try:
            with open(local_path, "wb") as f:
                f.write(file.getbuffer())
                
            doc = {
                "doc_id": doc_id,
                "file_name": file.name,
                "mime_type": file.type,
                "modifiedTime": datetime.now().isoformat() + "Z",
                "local_path": local_path,
                "source": "upload"
            }
            documents.append(doc)
            logger.info(f"Saved uploaded file: {file.name}")
            
        except Exception as e:
            logger.error(f"Failed to save uploaded file {file.name}: {e}")
            
    if progress_callback:
        progress_callback(total, total, "Uploads processed.")
        
    return documents
