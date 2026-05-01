import logging
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)

def sync_web_link(url: str, progress_callback=None) -> list[dict]:
    """
    Fetches a web page, extracts text using BeautifulSoup,
    and returns a document dict.
    """
    if not url or not url.startswith("http"):
        raise ValueError(f"Invalid URL: {url}")
        
    if progress_callback:
        progress_callback(0, 1, f"Fetching {url[:40]}...")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.extract()
            
        text = soup.get_text(separator=' ')
        
        # Clean text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        if not text:
            logger.warning(f"No text extracted from {url}")
            return []
            
        title = soup.title.string if soup.title else url.split("/")[-1]
        
        if progress_callback:
            progress_callback(1, 1, f"Scraped {title[:40]}")
            
        doc_id = f"web_{hash(url)}"
        
        doc = {
            "doc_id": doc_id,
            "file_name": title,
            "mime_type": "text/html",
            "modifiedTime": datetime.now().isoformat() + "Z",
            "local_path": "memory", # Pass directly via 'text' key
            "source": "web",
            "text": text
        }
        
        logger.info(f"Successfully scraped {url} ({len(text)} chars)")
        return [doc]
        
    except Exception as e:
        logger.error(f"Failed to scrape {url}: {e}")
        raise
