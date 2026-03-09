from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import Image, SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import os
import tempfile
import base64
import logging
from io import BytesIO
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

def materialize_blob_to_tempfile(blob: Any, default_ext: str = ".png") -> str:
    """
    Takes a FileBlob row or dict and writes it to a temporary file.
    """
    suffix = default_ext
    mime = getattr(blob, "mime_type", None) or (blob.get("mime_type") if isinstance(blob, dict) else None)
    
    if mime and "/" in mime:
        suffix = "." + mime.split("/")[-1]

    data = getattr(blob, "data", None) or (blob.get("data") if isinstance(blob, dict) else None)
    if not data and isinstance(blob, dict) and "data_base64" in blob:
        data = base64.b64decode(blob["data_base64"])

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    if data:
        tmp.write(data)
    tmp.close()
    return tmp.name

def _as_bool(val: Any, default: bool) -> bool:
    if isinstance(val, bool): return val
    if isinstance(val, str):
        s = val.strip().lower()
        return s in {"1", "true", "yes", "y", "on"}
    return default

def _normalize_resume_filters(filters: Optional[dict]) -> dict:
    raw = filters if isinstance(filters, dict) else {}
    return {
        "show_summary": _as_bool(raw.get("show_summary"), True),
        "show_bullets": _as_bool(raw.get("show_bullets"), True),
        "show_education": _as_bool(raw.get("show_education"), True),
        "show_awards": _as_bool(raw.get("show_awards"), True),
    }

def export_resume_item_pdf_bytes(resume_item: dict, filters: dict = None) -> bytes:
    """
    Builds a PDF in-memory combining Project Artifacts with Education and Awards.
    """
    if not isinstance(resume_item, dict):
        resume_item = {}

    opts = _normalize_resume_filters(filters)
    content = resume_item.get("content") or {}
    project = content.get("project") or resume_item.get("project") or {}
    
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    styles = getSampleStyleSheet()
    elements = []

    # --- Header: Project Title ---
    title = project.get("name") or project.get("display_name") or "Project Showcase"
    elements.append(Paragraph(f"<b>{title}</b>", styles["Title"]))
    elements.append(Spacer(1, 12))

    # --- Project Summary & Bullets ---
    if opts["show_summary"]:
        summary = content.get("summary_text") or resume_item.get("summary_text")
        if summary:
            elements.append(Paragraph("<b>Project Overview</b>", styles["Heading2"]))
            elements.append(Paragraph(str(summary), styles["Normal"]))
            elements.append(Spacer(1, 12))

    if opts["show_bullets"]:
        bullets = content.get("resume_bullets") or resume_item.get("resume_bullets") or []
        if bullets:
            elements.append(Paragraph("<b>Key Contributions</b>", styles["Heading3"]))
            for b in bullets:
                elements.append(Paragraph(f"• {b}", styles["Normal"]))
            elements.append(Spacer(1, 12))

    # --- NEW: EDUCATION SECTION ---
    education = resume_item.get("education") or []
    if opts["show_education"] and education:
        elements.append(Paragraph("<b>Education</b>", styles["Heading2"]))
        elements.append(Spacer(1, 4))
        for edu in education:
            inst = edu.get("institution", "Unknown Institution")
            deg = edu.get("degree") or ""
            field = edu.get("field_of_study") or ""
            
            # Format: Institution | Degree in Field
            edu_header = f"<b>{inst}</b>"
            if deg: edu_header += f" — {deg}"
            if field: edu_header += f" ({field})"
            
            elements.append(Paragraph(edu_header, styles["Normal"]))
            
            # Dates
            start = edu.get("start_year")
            end = "Present" if edu.get("is_current") else edu.get("end_year")
            if start or end:
                elements.append(Paragraph(f"<i>{start} - {end}</i>", styles["Normal"]))
            
            if edu.get("description"):
                elements.append(Paragraph(edu["description"], styles["Normal"]))
            elements.append(Spacer(1, 8))

    # --- NEW: AWARDS SECTION ---
    awards = resume_item.get("awards") or []
    if opts["show_awards"] and awards:
        elements.append(Paragraph("<b>Awards & Honors</b>", styles["Heading2"]))
        elements.append(Spacer(1, 4))
        for award in awards:
            title = award.get("title", "Award")
            issuer = award.get("issuer")
            year = award.get("awarded_year")
            
            award_line = f"• <b>{title}</b>"
            if issuer: award_line += f", {issuer}"
            if year: award_line += f" ({year})"
            
            elements.append(Paragraph(award_line, styles["Normal"]))
            if award.get("description"):
                elements.append(Paragraph(f"<i>{award['description']}</i>", styles["Normal"]))
        elements.append(Spacer(1, 12))

    # --- Embed Image if present ---
    thumb = content.get("thumbnail_blob") or resume_item.get("thumbnail_blob")
    if thumb:
        try:
            img_path = materialize_blob_to_tempfile(thumb)
            img = Image(img_path, width=2.5*72, height=1.5*72)
            elements.append(Spacer(1, 12))
            elements.append(img)
        except Exception as e:
            logger.warning(f"Failed to embed image: {e}")

    doc.build(elements)
    return buf.getvalue()

def export_portfolio_top_projects_pdf(portfolio_summary: dict, filename: str = "portfolio.pdf") -> str:
    """
    Standard export for the top ranked projects.
    """
    doc = SimpleDocTemplate(filename, pagesize=LETTER)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Top Ranked Projects", styles["Title"]))
    
    for project in portfolio_summary.get("top_projects", []):
        elements.append(Paragraph(f"<b>{project.get('project_name')}</b>", styles["Heading2"]))
        elements.append(Paragraph(project.get("summary_text", ""), styles["Normal"]))
        for b in project.get("resume_bullets", []):
            elements.append(Paragraph(f"• {b}", styles["Normal"]))
        elements.append(Spacer(1, 12))

    doc.build(elements)
    return filename