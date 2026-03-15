from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import Image, SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import os
import tempfile
import base64
import logging
from io import BytesIO
from typing import Any, Optional

logger = logging.getLogger(__name__)

# --- Utility Helpers ---

def materialize_blob_to_tempfile(blob: Any, default_ext: str = ".png") -> str:
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

def _as_int(val: Any, default: int, lo: int = 0, hi: int = 20) -> int:
    try:
        n = int(val)
        return max(lo, min(hi, n))
    except (TypeError, ValueError):
        return default

def _normalize_resume_filters(filters: Optional[dict]) -> dict:
    raw = filters if isinstance(filters, dict) else {}
    out = {
        "show_summary": _as_bool(raw.get("show_summary"), True),
        "show_bullets": _as_bool(raw.get("show_bullets"), True),
        "show_education": _as_bool(raw.get("show_education"), True),
        "show_awards": _as_bool(raw.get("show_awards"), True),
        "show_metadata": _as_bool(raw.get("show_metadata"), True),
        "show_project_profile": _as_bool(raw.get("show_project_profile"), True),
        "show_metrics": _as_bool(raw.get("show_metrics"), True),
        "show_tech_stack": _as_bool(raw.get("show_tech_stack"), True),
        "show_evidence": _as_bool(raw.get("show_evidence"), True),
        "max_bullets": _as_int(raw.get("max_bullets"), 6),
    }
    new_keys = {"show_project_profile", "show_metrics", "show_tech_stack", "show_evidence"}
    if not any(k in raw for k in new_keys) and not out["show_summary"] and not out["show_bullets"]:
        for k in new_keys: out[k] = False
    return out

# --- Main Export Functions ---

def export_resume_item_pdf_bytes(resume_item: dict, filters: dict = None) -> bytes:
    if not isinstance(resume_item, dict): resume_item = {}
    opts = _normalize_resume_filters(filters)
    content = resume_item.get("content") or {}
    project = content.get("project") or resume_item.get("project") or {}
    
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    title = project.get("name") or project.get("display_name") or "Project Showcase"
    elements.append(Paragraph(f"<b>{title}</b>", styles["Title"]))
    elements.append(Spacer(1, 12))

    if opts["show_metadata"]:
        elements.append(Paragraph(f"Resume Item ID: {resume_item.get('resume_id', 'unknown')}", styles["Normal"]))
        elements.append(Paragraph(f"Generated at: {content.get('generated_at', 'unknown')}", styles["Normal"]))
        elements.append(Spacer(1, 12))

    if opts["show_project_profile"]:
        role = str(project.get("user_role") or "").strip()
        collab = str(project.get("collaboration_type") or "").strip()
        snapshot = str(content.get("latest_snapshot_id") or "").strip()
        if role or collab or snapshot:
            elements.append(Paragraph("<b>Project Profile</b>", styles["Heading2"]))
            if role: elements.append(Paragraph(f"Role: {role}", styles["Normal"]))
            if collab: elements.append(Paragraph(f"Collaboration: {collab}", styles["Normal"]))
            if snapshot: elements.append(Paragraph(f"Latest Snapshot: {snapshot}", styles["Normal"]))
            elements.append(Spacer(1, 12))

    # Image
    thumb = content.get("thumbnail_blob")
    if thumb:
        try:
            path = materialize_blob_to_tempfile(thumb)
            img = Image(path, width=2.5*72, height=1.5*72)
            elements.append(img)
            elements.append(Spacer(1, 12))
        except Exception: pass

    if opts["show_summary"]:
        summary = str(content.get("summary_text") or "").strip()
        if summary:
            elements.append(Paragraph("<b>Summary</b>", styles["Heading2"]))
            elements.append(Paragraph(summary.replace(". ", ".<br/>"), styles["Normal"]))
            elements.append(Spacer(1, 12))

    if opts["show_bullets"]:
        bullets = content.get("resume_bullets") or []
        if bullets:
            elements.append(Paragraph("<b>Resume Bullets</b>", styles["Heading2"]))
            for b in bullets[:opts["max_bullets"]]:
                if str(b).strip(): 
                    # Standard hyphen for pytest compatibility
                    elements.append(Paragraph(f"- {b}", styles["Normal"]))
            elements.append(Spacer(1, 12))

    if opts["show_metrics"]:
        m = content.get("metrics") or {}
        if isinstance(m, dict) and any(m.get(k) for k in ["total_commits", "user_commits"]):
            elements.append(Paragraph("<b>Git Metrics</b>", styles["Heading2"]))
            elements.append(Paragraph(f"Total Commits: {m.get('total_commits', 0)}", styles["Normal"]))
            elements.append(Paragraph(f"Your Commits: {m.get('user_commits', 0)}", styles["Normal"]))
            elements.append(Spacer(1, 12))

    if opts["show_tech_stack"]:
        sig = content.get("signals") or {}
        p = sig.get("parser") or {}
        ml = sig.get("local_ml") or {}
        langs = [l.get("language") for l in (p.get("top_languages") or []) if isinstance(l, dict) and l.get("language")]
        skills = [s.get("skill") for s in (ml.get("top_skills") or []) if isinstance(s, dict) and s.get("skill")]
        if langs or skills:
            elements.append(Paragraph("<b>Tech Stack</b>", styles["Heading2"]))
            if langs: elements.append(Paragraph(f"Languages: {', '.join(langs[:4])}", styles["Normal"]))
            if skills: elements.append(Paragraph(f"Skills: {', '.join(skills[:6])}", styles["Normal"]))
            elements.append(Spacer(1, 12))

    if opts["show_evidence"]:
        ev = project.get("evidence_json") or {}
        if ev:
            elements.append(Paragraph("<b>Evidence Highlights</b>", styles["Heading2"]))
            met = ev.get("metrics") or {}
            for k, v in list(met.items())[:3]: elements.append(Paragraph(f"{k}: {v}", styles["Normal"]))
            elements.append(Spacer(1, 12))

    if opts["show_education"]:
        edu_list = resume_item.get("education") or []
        if edu_list:
            elements.append(Paragraph("<b>Education</b>", styles["Heading2"]))
            for edu in edu_list:
                inst = edu.get('institution', 'Unknown Institution')
                degree = edu.get('degree') or edu.get('subtitle') or ""
                header = f"- <b>{inst}</b>" + (f" — {degree}" if degree else "")
                elements.append(Paragraph(header, styles["Normal"]))
                
                # Fetching Year Data
                s_year = edu.get('start_year') or edu.get('year_start') or ""
                e_year = edu.get('end_year') or edu.get('year_end') or "Present"
                
                if s_year:
                    elements.append(Paragraph(f"<i>{s_year} — {e_year}</i>", styles["Normal"]))
                
                desc = edu.get('description') or ""
                if desc:
                    elements.append(Paragraph(desc, styles["Normal"]))
                
                elements.append(Spacer(1, 6))
            elements.append(Spacer(1, 6))

    if opts["show_awards"]:
        awd_list = resume_item.get("awards") or []
        if awd_list:
            elements.append(Paragraph("<b>Awards & Honors</b>", styles["Heading2"]))
            for a in awd_list:
                title = a.get('title', 'Award')
                elements.append(Paragraph(f"- <b>{title}</b>", styles["Normal"]))
                
                # Fetching Issuer and Year
                issuer = a.get('issuer') or a.get('organization') or ""
                year = a.get('awarded_year') or a.get('year') or ""
                
                meta = ""
                if issuer and year: meta = f"{issuer}, {year}"
                elif issuer: meta = issuer
                elif year: meta = year
                
                if meta:
                    elements.append(Paragraph(f"<i>{meta}</i>", styles["Normal"]))
                
                desc = a.get('description') or ""
                if desc:
                    elements.append(Paragraph(desc, styles["Normal"]))
                
                elements.append(Spacer(1, 6))
            elements.append(Spacer(1, 6))

    doc.build(elements)
    return buf.getvalue()

def export_portfolio_top_projects_pdf(portfolio_summary: dict, filename: str = "portfolio.pdf") -> str:
    if not isinstance(portfolio_summary, dict): portfolio_summary = {}
    doc = SimpleDocTemplate(filename, pagesize=LETTER)
    styles = getSampleStyleSheet()
    elements = [Paragraph("Portfolio: Top Ranked Project Summaries", styles["Title"]), Spacer(1, 12)]
    
    top = portfolio_summary.get("top_projects") or []
    for item in top:
        elements.append(Paragraph(f"<b>{item.get('project_name', 'Project')}</b>", styles["Heading2"]))
        elements.append(Paragraph(str(item.get("summary_text", "")), styles["Normal"]))
        for b in (item.get("resume_bullets") or [])[:5]:
            elements.append(Paragraph(f"- {b}", styles["Normal"]))
        elements.append(Spacer(1, 12))
    
    doc.build(elements)
    return filename

# --- Legacy Compatibility Functions ---

def export(data, llm_response=None, filename="report.pdf", consent="y"):
    doc = SimpleDocTemplate(filename, pagesize=LETTER)
    styles = getSampleStyleSheet()
    elements = [Paragraph("Code-to-Skills Prediction Report", styles["Title"]), Spacer(1, 12)]
    
    preds = data.get("predictions", [])
    if preds:
        table_data = [["Skill", "Confidence"]]
        for s, c in preds: table_data.append([str(s), f"{c:.2f}"])
        t = Table(table_data)
        t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.lightgrey), ('GRID', (0,0), (-1,-1), 1, colors.black)]))
        elements.append(t)
    
    if llm_response:
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("<b>LLM Analysis:</b>", styles["Heading2"]))
        elements.append(Paragraph(llm_response, styles["Normal"]))

    doc.build(elements)

def collect_predictions(parsed_folder):
    all_preds = []
    for file_summary in (parsed_folder or []):
        file_name = file_summary.get("file", "Unknown")
        skills = file_summary.get("skills") or file_summary.get("predictions") or []
        for s, p in skills: all_preds.append([f"{file_name}: {s}", p])
    return all_preds