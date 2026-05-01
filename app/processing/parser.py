import logging
import re

logger = logging.getLogger(__name__)

def _extract_pdf_pymupdf(path: str) -> str:
    import fitz           

    text_parts = []
    with fitz.open(path) as doc:
        for page in doc:
            text_parts.append(page.get_text("text"))
    return "\n".join(text_parts)

def _extract_pdf_pdfplumber(path: str) -> str:
    import pdfplumber

    text_parts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
    return "\n".join(text_parts)

def _clean_text(text: str) -> str:

    text = text.replace("\xa0", " ").replace("\t", " ")

    text = re.sub(r" {2,}", " ", text)

    text = text.replace("\r\n", "\n").replace("\r", "\n")

    text = re.sub(r"\n{3,}", "\n\n", text)

    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)
    return text.strip()

def extract_text(local_path: str, mime_type: str = "") -> str:
    path_lower = local_path.lower()

    if path_lower.endswith(".pdf") or "pdf" in mime_type:
        try:
            raw = _extract_pdf_pymupdf(local_path)
            logger.debug("Extracted PDF (PyMuPDF): %s", local_path)
        except Exception as e:
            logger.warning("PyMuPDF failed (%s), trying pdfplumber…", e)
            try:
                raw = _extract_pdf_pdfplumber(local_path)
                logger.debug("Extracted PDF (pdfplumber): %s", local_path)
            except Exception as e2:
                logger.error("pdfplumber also failed: %s", e2)
                return ""

    elif path_lower.endswith(".txt") or "text/plain" in mime_type:
        try:
            with open(local_path, "r", encoding="utf-8", errors="replace") as f:
                raw = f.read()
            logger.debug("Read TXT: %s", local_path)
        except Exception as e:
            logger.error("Failed to read TXT file: %s", e)
            return ""

    else:
        logger.warning("Unsupported file type for: %s", local_path)
        return ""

    cleaned = _clean_text(raw)
    logger.info("Extracted %d chars from: %s", len(cleaned), local_path)
    return cleaned
