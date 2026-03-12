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

def _as_int(val: Any, default: int) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default

def _normalize_resume_filters(filters: Optional[dict]) -> dict:
    raw = filters if isinstance(filters, dict) else {}
    return {
        "show_summary": _as_bool(raw.get("show_summary"), True),
        "show_bullets": _as_bool(raw.get("show_bullets"), True),
        "show_education": _as_bool(raw.get("show_education"), True),
        "show_awards": _as_bool(raw.get("show_awards"), True),
        "show_metadata": _as_bool(raw.get("show_metadata"), True),
        "show_project_profile": _as_bool(raw.get("show_project_profile"), True),
        "max_bullets": _as_int(raw.get("max_bullets"), 5),
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

    # --- Metadata ---
    if opts["show_metadata"]:
        res_id = resume_item.get("resume_id") or "unknown"
        elements.append(Paragraph(f"Resume Item ID: {res_id}", styles["Normal"]))
        elements.append(Spacer(1, 12))

    # --- Project Profile ---
    if opts["show_project_profile"] and (opts["show_summary"] or opts["show_bullets"]):
        elements.append(Paragraph("<b>Project Profile</b>", styles["Heading2"]))
        elements.append(Spacer(1, 6))

    # --- Project Summary & Related Sections ---
    if opts["show_summary"]:
        summary = content.get("summary_text") or resume_item.get("summary_text")
        if summary:
            elements.append(Paragraph("<b>Summary</b>", styles["Heading3"]))
            elements.append(Paragraph(str(summary), styles["Normal"]))
            elements.append(Spacer(1, 12))

        # Git Metrics
        metrics = content.get("metrics") or resume_item.get("metrics")
        if metrics:
            elements.append(Paragraph("<b>Git Metrics</b>", styles["Heading3"]))
            total = metrics.get("total_commits", 0)
            user = metrics.get("user_commits", 0)
            team = metrics.get("contributor_count", 1)
            metrics_str = f"Total Commits: {total} | Your Commits: {user} | Team Size: {team}"
            elements.append(Paragraph(metrics_str, styles["Normal"]))
            elements.append(Spacer(1, 12))

        # Tech Stack (Fix: Ensure empty list if key is None)
        signals = content.get("signals") or {}
        parser_data = signals.get("parser") or {}
        ml_data = signals.get("local_ml") or {}
        
        # Adding 'or []' inside the comprehension source to handle explicit nulls in JSON
        langs = [l.get("language") for l in (parser_data.get("top_languages") or []) if isinstance(l, dict) and l.get("language")]
        skills = [s.get("skill") for s in (ml_data.get("top_skills") or []) if isinstance(s, dict) and s.get("skill")]
        
        if langs or skills:
            elements.append(Paragraph("<b>Tech Stack</b>", styles["Heading3"]))
            if langs:
                elements.append(Paragraph(f"Languages: {', '.join(langs)}", styles["Normal"]))
            if skills:
                elements.append(Paragraph(f"Skills: {', '.join(skills)}", styles["Normal"]))
            elements.append(Spacer(1, 12))

        # Evidence Highlights
        evidence = project.get("evidence_json") or {}
        if evidence:
            elements.append(Paragraph("<b>Evidence Highlights</b>", styles["Heading3"]))
            latency = evidence.get("metrics", {}).get("latency_ms_p95")
            feedback = evidence.get("feedback")
            eval_score = evidence.get("evaluation", {}).get("overall")
            
            if latency: elements.append(Paragraph(f"- P95 Latency: {latency}ms", styles["Normal"]))
            if eval_score: elements.append(Paragraph(f"- Overall Evaluation: {eval_score.capitalize()}", styles["Normal"]))
            if feedback: elements.append(Paragraph(f"- Feedback: {feedback}", styles["Normal"]))
            elements.append(Spacer(1, 12))

    # --- Resume Bullets ---
    if opts["show_bullets"]:
        bullets = content.get("resume_bullets") or resume_item.get("resume_bullets") or []
        if bullets:
            elements.append(Paragraph("<b>Resume Bullets</b>", styles["Heading3"]))
            for b in bullets[:opts["max_bullets"]]:
                elements.append(Paragraph(f"- {b}", styles["Normal"]))
            elements.append(Spacer(1, 12))

    # --- EDUCATION SECTION ---
    education = resume_item.get("education") or []
    if opts["show_education"] and education:
        elements.append(Paragraph("<b>Education</b>", styles["Heading2"]))
        elements.append(Spacer(1, 4))
        for edu in education:
            inst = edu.get("institution", "Unknown Institution")
            elements.append(Paragraph(f"<b>{inst}</b>", styles["Normal"]))
            elements.append(Spacer(1, 8))

    # --- AWARDS SECTION ---
    awards = resume_item.get("awards") or []
    if opts["show_awards"] and awards:
        elements.append(Paragraph("<b>Awards & Honors</b>", styles["Heading2"]))
        elements.append(Spacer(1, 4))
        for award in awards:
            elements.append(Paragraph(f"- <b>{award.get('title', 'Award')}</b>", styles["Normal"]))
        elements.append(Spacer(1, 12))

    # --- Embed Image ---
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
    if not isinstance(portfolio_summary, dict):
        portfolio_summary = {}
    doc = SimpleDocTemplate(filename, pagesize=LETTER)
    styles = getSampleStyleSheet()
    elements = [Paragraph("Top Ranked Projects", styles["Title"])]
    for project in portfolio_summary.get("top_projects", []):
        elements.append(Paragraph(f"<b>{project.get('project_name')}</b>", styles["Heading2"]))
        for b in project.get("resume_bullets", []):
            elements.append(Paragraph(f"- {b}", styles["Normal"]))
        elements.append(Spacer(1, 12))
    doc.build(elements)
    return filename