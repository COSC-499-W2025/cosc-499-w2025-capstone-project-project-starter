"""
pdf_exporter.py
-----------------
Export a dictionary of predictions to a nicely formatted PDF table.
Does not require the ML model.
"""

from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from main import consent


def export(data, filename="report.pdf"):
    """
    Exports a predictions dictionary to a formatted PDF file with a styled table.

    Args:
        data (dict): Dictionary of predictions, e.g.:
                     {"predictions": [["Flask", 0.93], ["SQL", 0.71]]}
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
        print(f"✅ PDF created (empty): {filename}")
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

    # Build PDF
    doc.build(elements)
    print(f"✅ PDF successfully created: {filename}")


def collect_predictions(parsed_folder):
    """
    Collects predictions from parsed file summaries.
    Returns a flat list of ["filename: skill", probability].
    """

    all_predictions = []

    if isinstance(parsed_folder, list):
        for file_summary in parsed_folder:
            file_name = file_summary.get("file", "Unknown file")

            # Accept both "skills" and "predictions"
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
                    print(f"⚠️ Skipping invalid skill entry in {file_name}: {item}")
    else:
        print("⚠️ Unexpected parsed_folder structure. PDF will be empty.")

    return all_predictions
