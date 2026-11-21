import io
import os
import re
import shutil

import pymupdf
import pytesseract
from docx import Document
from PIL import Image

from app.core.config import settings


def extract_pdf_text(content: bytes, max_pages: int = 30) -> str:
    try:
        document = pymupdf.open(stream=content, filetype="pdf")
    except Exception as exc:
        raise ValueError("The PDF is corrupted or could not be read") from exc
    if document.page_count > max_pages:
        raise ValueError(f"The PDF exceeds the {max_pages}-page resume limit")
    if settings.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
    extracted_pages = []
    for page in document:
        text = page.get_text().strip()
        if text:
            extracted_pages.append(text)
            continue
        if not settings.ocr_enabled:
            raise ValueError("This scanned PDF needs OCR, which is disabled on this server")
        if not (settings.tesseract_cmd and os.path.isfile(settings.tesseract_cmd)) and not shutil.which("tesseract"):
            raise ValueError("This scanned PDF needs OCR. Install Tesseract OCR and restart the API to parse image-only pages.")
        try:
            rect = page.rect
            scale = min(180 / 72, 3000 / max(rect.width, rect.height))
            pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), colorspace=pymupdf.csRGB, alpha=False)
            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
            text = pytesseract.image_to_string(image, lang=settings.ocr_language).strip()
        except pytesseract.TesseractNotFoundError as exc:
            raise ValueError("Tesseract OCR is configured but its executable could not be started") from exc
        except Exception as exc:
            raise ValueError("OCR could not read a scanned PDF page") from exc
        if text:
            extracted_pages.append(text)
    result = "\n".join(extracted_pages).strip()
    if not result:
        raise ValueError("No readable text was found in this PDF, even after OCR")
    return result


def parse_resume(filename: str, content: bytes) -> tuple[str, dict]:
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix == "pdf":
        text = extract_pdf_text(content)
    elif suffix == "docx":
        try:
            doc = Document(io.BytesIO(content))
            text = "\n".join(paragraph.text for paragraph in doc.paragraphs).strip()
        except Exception as exc:
            raise ValueError("The DOCX file is corrupted or could not be read") from exc
        if not text:
            raise ValueError("The document contains no readable text")
    else:
        raise ValueError("Only PDF and DOCX resumes are supported")

    email = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
    phone = re.search(r"(?:\+?\d[\d\s().-]{7,}\d)", text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    skills_dictionary = ["Python", "Java", "JavaScript", "TypeScript", "C++", "React", "SQL", "PostgreSQL", "Machine Learning", "TensorFlow", "PyTorch", "FastAPI", "Django", "Node.js", "AWS", "Azure", "Docker", "Kubernetes"]
    found = [skill for skill in skills_dictionary if re.search(rf"(?<!\w){re.escape(skill)}(?!\w)", text, re.I)]
    def section(*names):
        pattern = re.compile(rf"(?:{'|'.join(names)})\s*:?\s*(.*?)(?=\n[A-Z][A-Za-z /&-]{{2,30}}\s*:?[\n]|\Z)", re.I | re.S)
        match = pattern.search(text)
        return [line.strip(" •-\t") for line in match.group(1).splitlines() if line.strip()] if match else []

    name = next((line for line in lines[:8] if not re.search(r"@|https?://|\+?\d[\d -]{7,}", line) and len(line.split()) in (2, 3, 4)), None)
    education_lines = section("education", "academics", "qualification")
    def labeled(*labels):
        match = re.search(rf"(?:{'|'.join(labels)})\s*[:=-]\s*([^\n]+)", text, re.I)
        return match.group(1).strip() if match else ""

    degree_match = re.search(r"\b(B\.?\s?Tech|M\.?\s?Tech|BCA|MCA|BSc|MSc|Bachelor(?:'s)?|Master(?:'s)?|Ph\.?D\.?)\b[^\n]*", text, re.I)
    cgpa_match = re.search(r"\b(?:CGPA|GPA)\s*[:=-]?\s*(\d{1,2}(?:\.\d+)?)", text, re.I)
    year_match = re.search(r"\b(?:graduat(?:ion|e)|class of|expected)\D{0,20}(20\d{2})\b", text, re.I)
    project_entries = [{"name": line[:200], "description": "", "technologies": []} for line in section("projects", "personal projects")]
    certification_entries = []
    for line in section("certifications", "certificates"):
        parts = re.split(r"\s+(?:at|[-–—|])\s+", line, maxsplit=1)
        certification_entries.append({"title": parts[0][:200], "issuer": parts[1][:160] if len(parts) > 1 else "", "issue_date": None, "credential_url": None})
    experience_entries = []
    for line in section("experience", "work experience", "internships"):
        parts = re.split(r"\s+(?:at|@|[-–—|])\s+", line, maxsplit=1)
        experience_entries.append({"title": parts[0][:160], "company": parts[1][:200] if len(parts) > 1 else "", "description": line, "start_date": None, "end_date": None})

    parsed = {"name": name, "email": email.group(0) if email else None, "phone": phone.group(0).strip() if phone else None,
              "education": education_lines, "education_details": {"university": labeled("university"), "college": labeled("college", "institution"),
                "degree": degree_match.group(0).strip() if degree_match else "", "branch": labeled("branch", "major", "specialization"),
                "cgpa": float(cgpa_match.group(1)) if cgpa_match else None, "graduation_year": int(year_match.group(1)) if year_match else None},
              "skills": found, "projects": project_entries, "experience": experience_entries, "certifications": certification_entries}
    return text, parsed
