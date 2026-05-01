import logging
import os
import shutil
import tempfile
from datetime import datetime
import uuid
import git

logger = logging.getLogger(__name__)

SUPPORTED_CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", 
    ".java", ".cpp", ".c", ".h", ".go", 
    ".rs", ".rb", ".php", ".html", ".css", 
    ".md", ".json", ".yaml", ".yml", ".txt", ".sh"
}

def sync_github_repo(repo_url: str, progress_callback=None) -> list[dict]:
    """
    Clones a repo locally, reads supported code/text files, 
    and returns a list of document dicts ready for chunking.
    """
    if not repo_url or not repo_url.startswith("http"):
        raise ValueError(f"Invalid repository URL: {repo_url}")

    documents = []
    
    # Create a unique temp directory
    temp_dir = tempfile.mkdtemp(prefix="repo_clone_")
    
    try:
        logger.info(f"Cloning {repo_url} into {temp_dir}...")
        if progress_callback:
            progress_callback(0, 1, "Cloning repository...")
            
        git.Repo.clone_from(repo_url, temp_dir, depth=1)
        
        # Traverse the cloned directory
        all_files = []
        for root, dirs, files in os.walk(temp_dir):
            # Skip hidden directories like .git
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if not file.startswith('.'):
                    all_files.append(os.path.join(root, file))
        
        total_files = len(all_files)
        processed = 0
        
        for file_path in all_files:
            processed += 1
            rel_path = os.path.relpath(file_path, temp_dir)
            ext = os.path.splitext(file_path)[1].lower()
            
            if progress_callback:
                progress_callback(processed, total_files, rel_path, skipped=(ext not in SUPPORTED_CODE_EXTENSIONS))
            
            if ext not in SUPPORTED_CODE_EXTENSIONS:
                continue
                
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read().strip()
                    
                if content:
                    # Treat the file content like a downloaded text document
                    # but skip writing it to data/downloaded_files to save space,
                    # just pass it directly as a document dict with 'text' populated.
                    repo_name = repo_url.rstrip("/").split("/")[-1]
                    doc_id = f"github_{repo_name}_{rel_path}"
                    
                    doc = {
                        "doc_id": doc_id,
                        "file_name": f"{repo_name}/{rel_path}",
                        "mime_type": "text/plain",
                        "modifiedTime": datetime.now().isoformat() + "Z",
                        "local_path": "memory", # Flag that it doesn't need external parsing
                        "source": "github",
                        "text": content # We inject text here directly so pipeline.py doesn't use parser
                    }
                    documents.append(doc)
            except Exception as e:
                logger.warning(f"Failed to read {rel_path}: {e}")
                
    finally:
        # Cleanup
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            logger.error(f"Failed to clean up temp dir {temp_dir}: {e}")

    logger.info(f"Extracted {len(documents)} supported files from repo.")
    return documents
