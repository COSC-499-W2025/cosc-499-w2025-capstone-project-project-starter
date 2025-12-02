import argparse
from ml.universal.predict import classify_text
from exporter.pdf_exporter import export_predictions_to_pdf

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to file to classify")
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--out", default="predictions.pdf", help="Output PDF file")
    args = parser.parse_args()

    # Load input text
    with open(args.file, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    # Run prediction (no changes to predict.py)
    preds = classify_text(text, threshold=args.threshold)

    # Export predictions
    export_predictions_to_pdf(preds, args.out)

    print(f"PDF saved to {args.out}")

if __name__ == "__main__":
    main()