from __future__ import annotations
import argparse
from pathlib import Path
from typing import Optional

# Optional imports are raised with helpful messages so the user knows which
# dependency is missing when the script is invoked directly.
try:
    from PIL import Image, ImageOps
except ImportError as exc:  # pragma: no cover - import guard
    raise ImportError(
        "Pillow is required for image loading. Install with `pip install Pillow`."
    ) from exc

try:
    import pytesseract
except ImportError as exc:  # pragma: no cover - import guard
    raise ImportError(
        "pytesseract is required for OCR. Install with `pip install pytesseract` "
        "and ensure the Tesseract binary is available on your system PATH."
    ) from exc

SUPPORTED_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
    ".bmp",
    ".gif",
    ".webp",
}

def _load_image(image_path: Path) -> Image.Image:
    """Load and normalize the image for OCR."""
    with Image.open(image_path) as img:
        # Respect EXIF rotation so text is upright for OCR
        normalized = ImageOps.exif_transpose(img)
        return normalized.convert("RGB")

def extract_text(image_path: Path) -> str:
    """
    Extract text from an image using Tesseract OCR.

    Args:
        image_path: Path to the image file.

    Returns:
        Extracted text as a string (leading/trailing whitespace removed).
    """
    if image_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {image_path.suffix}. "
            f"Supported types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    image_path = image_path.resolve()
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image = _load_image(image_path)
    text = pytesseract.image_to_string(image)
    return text.strip()

def write_text_to_file(text: str, output_path: Path) -> Path:
    """Write the OCR text to a file, creating parent directories if needed."""
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text + "\n", encoding="utf-8")
    return output_path

def process_image_to_text(image_path: Path, output_path: Optional[Path] = None) -> Path:
    """
    Convert an image to text and write the result to a file.

    Args:
        image_path: Image to process.
        output_path: Optional destination for the text file. If not provided,
            the output will be created next to the image with a .txt extension.

    Returns:
        Path to the text file that was written.
    """
    image_path = Path(image_path)
    if output_path is None:
        output_path = image_path.with_suffix(".txt")
    else:
        output_path = Path(output_path)

    text = extract_text(image_path)
    return write_text_to_file(text, output_path)

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Extract text from an image using Tesseract OCR and write it to a text file. "
            "Requires the Tesseract binary to be installed and accessible on PATH."
        )
    )
    parser.add_argument(
        "image",
        type=Path,
        help="Path to the image file (png, jpg, jpeg, tif, tiff, bmp, gif, webp).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Optional path for the output text file. Defaults to <image>.txt next to the image.",
    )
    return parser

#command to run: python -m src.tools.image_text_extractor images/basic_text.png
def main():
    parser = _build_parser()
    args = parser.parse_args()

    output_path = process_image_to_text(args.image, args.output)
    print(f"OCR complete. Text written to: {output_path}")


if __name__ == "__main__":
    main()
