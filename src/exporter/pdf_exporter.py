"""
pdf_exporter.py
-----------------
Export a dictionary of predictions to a nicely formatted PDF.
Does not require the ML model.
"""

from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

def export(data, filename="report.pdf"):
    """
    Exports a predictions dictionary to a formatted PDF file.

    Args:
        data (dict): Dictionary of predictions, e.g.:
                     {"predictions": [["Flask", 0.93], ["SQL", 0.71]]}
        filename (str): Output PDF filename.
    """
    from reportlab.lib.pagesizes import LETTER
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    # Make sure data is a dictionary
    if not isinstance(data, dict):
        data = {}

    # Make sure predictions is a list of lists
    predictions = data.get("predictions", [])
    if not isinstance(predictions, list):
        predictions = []

    # Filter out invalid items that cannot be unpacked
    clean_predictions = []
    for item in predictions:
        if (
            isinstance(item, (list, tuple))
            and len(item) == 2
            and isinstance(item[0], str)
            and isinstance(item[1], (float, int))
        ):
            clean_predictions.append(item)

    doc = SimpleDocTemplate(filename, pagesize=LETTER)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph("Code-to-Skills Prediction Report", styles["Title"]))
    elements.append(Spacer(1, 12))

    # Predictions section
    if not clean_predictions:
        elements.append(Paragraph("No skills predicted.", styles["Normal"]))
    else:
        elements.append(Paragraph("<b>Predicted Skills:</b>", styles["Heading2"]))
        elements.append(Spacer(1, 6))
        for skill, confidence in clean_predictions:
            elements.append(Paragraph(f"• {skill} — {confidence:.2f}", styles["Normal"]))
            elements.append(Spacer(1, 4))

    doc.build(elements)
    print(f"✅ PDF successfully created: {filename}")


def collect_predictions(parsed_folder):
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



