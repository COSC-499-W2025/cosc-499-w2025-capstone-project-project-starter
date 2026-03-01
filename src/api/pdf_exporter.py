from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import Image
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import os
import tempfile
import base64
import logging
from io import BytesIO

logger = logging.getLogger(__name__)


def materialize_blob_to_tempfile(blob, default_ext=".png"):
    """
    Takes a FileBlob row and writes it to a temporary file.
    Returns the file path.
    """
    suffix = default_ext

    # Try to infer extension from mime type
    if blob.mime_type and "/" in blob.mime_type:
        suffix = "." + blob.mime_type.split("/")[-1]

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(blob.data)
    tmp.close()

    return tmp.name



def export(data, llm_response=None,filename="report.pdf", consent="y"):
    """
    Exports a predictions dictionary to a formatted PDF file with a styled table.

    Args:
        ml_data (dict): Dictionary of predictions, e.g.:
                     {"predictions": [["Flask", 0.93], ["SQL", 0.71]]}
        llm_response (string): Response from LLM, conditional on user consent to use of LLM,
                    therefore defaults to None unless passed in
        filename (str): Output PDF filename.
    """

    # --- Validate incoming data ---
    if not isinstance(data, dict):
        data = {}

    predictions = data.get("predictions", [])
    if not isinstance(predictions, list):
        predictions = []

    # Clean + validate entries
    clean_predictions = []
    for item in predictions:
        if (
            isinstance(item, (list, tuple))
            and len(item) == 2
            and isinstance(item[0], str)
            and isinstance(item[1], (float, int))
        ):
            clean_predictions.append(item)

    # --- Build PDF ---
    doc = SimpleDocTemplate(filename, pagesize=LETTER)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph("Code-to-Skills Prediction Report", styles["Title"]))
    elements.append(Spacer(1, 12))

    # If no predictions
    if not clean_predictions:
        elements.append(Paragraph("No skills predicted.", styles["Normal"]))
        doc.build(elements)
        logger.info("PDF created without predictions: %s", filename)
        return

    # Section header
    elements.append(Paragraph("<b>Predicted Skills</b>", styles["Heading2"]))
    elements.append(Spacer(1, 6))

    # Display the model used in the analysis based on consent
    if str(consent).lower() in ("y", "yes"):
        elements.append(Paragraph("Model used: Ollama External Model", styles["Normal"]))
    elif str(consent).lower() in ("n", "no"):
        elements.append(Paragraph("Model used: Local Heuristic Model", styles["Normal"]))
    else:
        elements.append(Paragraph("Model used: (unknown)", styles["Normal"]))

    elements.append(Spacer(1, 6))

    # --- Table Construction ---
    table_data = [["Skill", "Confidence"]]
    for skill, confidence in clean_predictions:
        table_data.append([skill, f"{confidence:.2f}"])

    # Base table styling
    table_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),  # Header row
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
    ]

    # Add zebra striping for even rows (row index starts at 0)
    for row in range(1, len(table_data)):
        if row % 2 == 0:  # even index → second, fourth, etc.
            table_style.append(
                ('BACKGROUND', (0, row), (-1, row), colors.whitesmoke)
            )

    table = Table(table_data)
    table.setStyle(TableStyle(table_style))

    elements.append(table)

    # Optional LLM Analysis Section
    if llm_response:
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("<b>LLM Analysis:</b>", styles["Heading2"]))
        elements.append(Spacer(1, 6))

        for line in llm_response.split("\n"):
            if line.strip():
                elements.append(Paragraph(line.strip(), styles["Normal"]))
                elements.append(Spacer(1, 4))



    # Build PDF
    doc.build(elements)
    logger.info("PDF created successfully: %s", filename)


def collect_predictions(parsed_folder):
    """
    Collects predictions from parsed file summaries.
    Returns a flat list of ["filename: skill", probability] sorted
    by file modification time (newest first).
    """

    if not isinstance(parsed_folder, list):
        logger.warning("Unexpected parsed_folder structure; PDF will be empty")
        return []

    files_with_mtime = []

    # Attach modification times
    for file_summary in parsed_folder:
        file_name = file_summary.get("file", "Unknown file")

        # Only set mtime if the file exists on disk
        if os.path.exists(file_name):
            mtime = os.path.getmtime(file_name)
        else:
            mtime = 0  # fallback if file path is missing
        files_with_mtime.append((file_summary, mtime))

    # Sort files from newest to oldest
    files_with_mtime.sort(key=lambda x: x[1], reverse=True)

    all_predictions = []

    # Collect predictions in sorted order
    for file_summary, _ in files_with_mtime:
        file_name = file_summary.get("file", "Unknown file")

        # Accept both "skills" and "predictions" fields
        skills = (
            file_summary.get("skills")
            or file_summary.get("predictions")
            or []
        )

        if not isinstance(skills, list):
            continue

        for item in skills:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                skill, prob = item
                all_predictions.append([f"{file_name}: {skill}", prob])
            else:
                logger.warning("Skipping invalid skill entry in %s: %r", file_name, item)

    return all_predictions



def export_portfolio_top_projects_pdf(portfolio_summary: dict, filename: str = "portfolio_top_projects.pdf") -> str:
    """
    Writes a simple PDF containing the top project summaries and bullets.

    Expects portfolio_summary shape returned by POST /portfolio/generate:
      {
        "portfolio_id": ...,
        "generated_at": ...,
        "top_projects": [
          {"project_name": ..., "summary_text": ..., "resume_bullets": [...]}, ...
        ]
      }
    Returns filename for convenience.
    """
    if not isinstance(portfolio_summary, dict):
        portfolio_summary = {}

    top = portfolio_summary.get("top_projects", [])
    if not isinstance(top, list):
        top = []

    doc = SimpleDocTemplate(filename, pagesize=LETTER)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Portfolio: Top Ranked Project Summaries", styles["Title"]))
    elements.append(Spacer(1, 12))

    meta = f"Generated at: {portfolio_summary.get('generated_at', '(unknown)')}<br/>Portfolio ID: {portfolio_summary.get('portfolio_id', '(unknown)')}"
    elements.append(Paragraph(meta, styles["Normal"]))
    elements.append(Spacer(1, 12))

    if not top:
        elements.append(Paragraph("No ranked projects available.", styles["Normal"]))
        doc.build(elements)
        return filename

    for idx, item in enumerate(top, start=1):
        name = str(item.get("project_name") or item.get("project_id") or f"Project {idx}")
        summary = str(item.get("summary_text") or "").strip()
        bullets = item.get("resume_bullets") or []
    
        # Add project title
        elements.append(Paragraph(f"{idx}. {name}", styles["Heading2"]))
        elements.append(Spacer(1, 6))
    
        # Add portfolio image if exists
        blob = item.get("thumbnail_blob")
        blob_sha = item.get("thumbnail_blob_sha256")  # optional, for logs only

        if blob:
            try:
                tmp_path = materialize_blob_to_tempfile(blob)

                img = Image(tmp_path)
                img.drawHeight = 1.5 * 72   # 1.5 inches
                img.drawWidth = 2.5 * 72    # 2.5 inches

                elements.append(img)
                elements.append(Spacer(1, 6))

                logger.debug("Embedded image from blob %s", blob_sha)

            except Exception:
                logger.warning("Could not add image from blob %s", blob_sha, exc_info=True)

        # Add summary
        if summary:
            elements.append(Paragraph(summary, styles["Normal"]))
            elements.append(Spacer(1, 6))
    
        # Add bullets
        if isinstance(bullets, list) and bullets:
            elements.append(Paragraph("Résumé bullets:", styles["Heading3"]))
            for b in bullets[:5]:
                b = str(b).strip()
                if b:
                    elements.append(Paragraph(f"• {b}", styles["Normal"]))
            elements.append(Spacer(1, 10))

    doc.build(elements)
    return filename


def export_resume_item_pdf(resume_item: dict, filename: str = "resume_item.pdf") -> str:
    """
    Writes a PDF for a single resume item (summary + bullets).
    Expects the shape returned by GET /resume/{id}:
      {"resume_id": ..., "content": {"project": {...}, "summary_text": ..., "resume_bullets": [...]}}
    """
    if not isinstance(resume_item, dict):
        resume_item = {}

    content = resume_item.get("content") or {}
    if not isinstance(content, dict):
        content = {}

    project = content.get("project") or {}
    if not isinstance(project, dict):
        project = {}

    doc = SimpleDocTemplate(filename, pagesize=LETTER)
    styles = getSampleStyleSheet()
    elements = []

    title = project.get("name") or project.get("id") or "Resume Item"
    elements.append(Paragraph(str(title), styles["Title"]))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(f"Resume Item ID: {resume_item.get('resume_id', '(unknown)')}", styles["Normal"]))
    elements.append(Paragraph(f"Generated at: {content.get('generated_at', '(unknown)')}", styles["Normal"]))
    elements.append(Spacer(1, 12))

    summary = str(content.get("summary_text") or "").strip()
    if summary:
        elements.append(Paragraph("Summary", styles["Heading2"]))
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(summary, styles["Normal"]))
        elements.append(Spacer(1, 12))

    bullets = content.get("resume_bullets") or []
    if isinstance(bullets, list) and bullets:
        elements.append(Paragraph("Résumé Bullets", styles["Heading2"]))
        elements.append(Spacer(1, 6))
        for b in bullets[:10]:
            b = str(b).strip()
            if b:
                elements.append(Paragraph(f"• {b}", styles["Normal"]))
                elements.append(Spacer(1, 4))

    doc.build(elements)
    return filename


def _as_bool(val, default: bool) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        s = val.strip().lower()
        if s in {"1", "true", "yes", "y", "on"}:
            return True
        if s in {"0", "false", "no", "n", "off"}:
            return False
    if isinstance(val, (int, float)):
        return bool(val)
    return default


def _as_int(val, default: int, lo: int, hi: int) -> int:
    try:
        n = int(val)
    except Exception:
        n = default
    return max(lo, min(hi, n))


def _normalize_resume_filters(filters: dict) -> dict:
    raw = filters if isinstance(filters, dict) else {}
    out = {
        "show_summary": _as_bool(raw.get("show_summary"), True),
        "show_bullets": _as_bool(raw.get("show_bullets"), True),
        "max_bullets": _as_int(raw.get("max_bullets"), 6, 0, 20),
        "show_metadata": _as_bool(raw.get("show_metadata"), True),
        "show_project_profile": _as_bool(raw.get("show_project_profile"), True),
        "show_metrics": _as_bool(raw.get("show_metrics"), True),
        "show_tech_stack": _as_bool(raw.get("show_tech_stack"), True),
        "show_evidence": _as_bool(raw.get("show_evidence"), True),
    }

    # Backward compatibility: existing "hide all" behavior with legacy keys.
    new_keys = {"show_project_profile", "show_metrics", "show_tech_stack", "show_evidence"}
    if (
        not any(k in raw for k in new_keys)
        and not out["show_summary"]
        and not out["show_bullets"]
        and not out["show_metadata"]
    ):
        out["show_project_profile"] = False
        out["show_metrics"] = False
        out["show_tech_stack"] = False
        out["show_evidence"] = False

    return out


def export_resume_item_pdf_bytes(resume_item: dict, filters: dict = None) -> bytes:
    """
    Build a PDF in-memory for a single resume item, respecting user toggles.
    Embeds thumbnail image if available.
    """
    if not isinstance(resume_item, dict):
        resume_item = {}

    opts = _normalize_resume_filters(filters)

    show_summary = opts["show_summary"]
    show_bullets = opts["show_bullets"]
    max_bullets = opts["max_bullets"]
    show_metadata = opts["show_metadata"]
    show_project_profile = opts["show_project_profile"]
    show_metrics = opts["show_metrics"]
    show_tech_stack = opts["show_tech_stack"]
    show_evidence = opts["show_evidence"]

    content = resume_item.get("content") or {}
    if not isinstance(content, dict):
        content = {}

    project = content.get("project") or {}
    if not isinstance(project, dict):
        project = {}

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER)
    styles = getSampleStyleSheet()
    elements = []

    # Title (always shown)
    title = project.get("name") or project.get("id") or "Resume Item"
    elements.append(Paragraph(str(title), styles["Title"]))
    elements.append(Spacer(1, 12))

    if show_metadata:
        elements.append(Paragraph(f"Resume Item ID: {resume_item.get('resume_id', '(unknown)')}", styles["Normal"]))
        elements.append(Paragraph(f"Generated at: {content.get('generated_at', '(unknown)')}", styles["Normal"]))
        elements.append(Spacer(1, 12))

    if show_project_profile:
        role = str(project.get("user_role") or "").strip()
        collab = str(project.get("collaboration_type") or "").strip()
        latest_snapshot_id = str(content.get("latest_snapshot_id") or "").strip()

        profile_lines = []
        if role:
            profile_lines.append(f"Role: {role}")
        if collab:
            profile_lines.append(f"Collaboration: {collab}")
        if latest_snapshot_id:
            profile_lines.append(f"Latest snapshot: {latest_snapshot_id}")

        if profile_lines:
            elements.append(Paragraph("Project Profile", styles["Heading2"]))
            elements.append(Spacer(1, 6))
            for line in profile_lines:
                elements.append(Paragraph(line, styles["Normal"]))
            elements.append(Spacer(1, 12))

    # --- Embed thumbnail if available ---
    thumbnail_blob = content.get("thumbnail_blob")
    if thumbnail_blob:
        try:
            # If blob has base64 data (as in your artifact)
            file_bytes = base64.b64decode(thumbnail_blob.get("data_base64", ""))
            suffix = ".png"  # default
            if "mime_type" in thumbnail_blob and "/" in thumbnail_blob["mime_type"]:
                suffix = "." + thumbnail_blob["mime_type"].split("/")[-1]

            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp.write(file_bytes)
            tmp.close()

            img = Image(tmp.name)
            img.drawHeight = 1.5 * 72
            img.drawWidth = 2.5 * 72
            elements.append(img)
            elements.append(Spacer(1, 12))
            logger.debug("Embedded thumbnail image in PDF")

        except Exception:
            logger.warning("Could not embed thumbnail in resume PDF", exc_info=True)

    # Summary section
    if show_summary:
        summary = str(content.get("summary_text") or "").strip()
        if summary:
            elements.append(Paragraph("Summary", styles["Heading2"]))
            elements.append(Spacer(1, 6))
            elements.append(Paragraph(summary.replace(". ", ".<br/>"), styles["Normal"]))
            elements.append(Spacer(1, 12))

    # Bullets section
    if show_bullets:
        bullets = content.get("resume_bullets") or []
        if isinstance(bullets, list) and bullets:
            elements.append(Paragraph("Resume Bullets", styles["Heading2"]))
            elements.append(Spacer(1, 6))
            for b in bullets[:max_bullets]:
                b = str(b).strip()
                if b:
                    elements.append(Paragraph(f"- {b}", styles["Normal"]))
                    elements.append(Spacer(1, 4))
            elements.append(Spacer(1, 8))

    if show_metrics:
        metrics = content.get("metrics") if isinstance(content.get("metrics"), dict) else {}
        metric_lines = []
        if metrics:
            if metrics.get("total_commits") is not None:
                metric_lines.append(f"Total commits: {metrics.get('total_commits')}")
            if metrics.get("user_commits") is not None:
                metric_lines.append(f"Your commits: {metrics.get('user_commits')}")
            if metrics.get("contributor_count") is not None:
                metric_lines.append(f"Contributors: {metrics.get('contributor_count')}")
        if metric_lines and not (
            str(metrics.get("total_commits") or "0") == "0" and str(metrics.get("contributor_count") or "0") == "0"
        ):
            elements.append(Paragraph("Git Metrics", styles["Heading2"]))
            elements.append(Spacer(1, 6))
            for line in metric_lines:
                elements.append(Paragraph(line, styles["Normal"]))
            elements.append(Spacer(1, 12))

    if show_tech_stack:
        signals = content.get("signals") if isinstance(content.get("signals"), dict) else {}
        parser_sig = signals.get("parser") if isinstance(signals.get("parser"), dict) else {}
        ml_sig = signals.get("local_ml") if isinstance(signals.get("local_ml"), dict) else {}

        lang_names = []
        for row in (parser_sig.get("top_languages") or [])[:4]:
            if isinstance(row, dict) and row.get("language"):
                lang_names.append(str(row["language"]))

        frameworks = []
        for fw in (parser_sig.get("frameworks") or [])[:4]:
            text_fw = str(fw).strip()
            if text_fw:
                frameworks.append(text_fw)

        skill_names = []
        for row in (ml_sig.get("top_skills") or [])[:6]:
            if isinstance(row, dict) and row.get("skill"):
                skill_names.append(str(row["skill"]))

        tech_lines = []
        if lang_names:
            tech_lines.append(f"Languages: {', '.join(lang_names)}")
        if frameworks:
            tech_lines.append(f"Frameworks: {', '.join(frameworks)}")
        if skill_names:
            tech_lines.append(f"Top skills: {', '.join(skill_names)}")

        if tech_lines:
            elements.append(Paragraph("Tech Stack", styles["Heading2"]))
            elements.append(Spacer(1, 6))
            for line in tech_lines:
                elements.append(Paragraph(line, styles["Normal"]))
            elements.append(Spacer(1, 12))

    if show_evidence:
        evidence = project.get("evidence_json") if isinstance(project.get("evidence_json"), dict) else {}
        evidence_lines = []

        metrics = evidence.get("metrics")
        if isinstance(metrics, dict) and metrics:
            metric_bits = []
            for k, v in list(metrics.items())[:3]:
                key = str(k).strip()
                val = str(v).strip()
                if key and val:
                    metric_bits.append(f"{key}: {val}")
            if metric_bits:
                evidence_lines.append(f"Outcomes:<br/>{'<br/>'.join(metric_bits)}")

        if evidence.get("feedback"):
            evidence_lines.append("Feedback available")
        if evidence.get("evaluation"):
            evidence_lines.append("Evaluation available")

        if evidence_lines:
            elements.append(Paragraph("Evidence Highlights", styles["Heading2"]))
            elements.append(Spacer(1, 6))
            for line in evidence_lines:
                elements.append(Paragraph(line, styles["Normal"]))
            elements.append(Spacer(1, 12))

    doc.build(elements)
    return buf.getvalue()
