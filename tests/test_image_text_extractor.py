from pathlib import Path

import pytest

from src.tools import image_text_extractor as extractor


def test_process_image_to_text_writes_default_txt(monkeypatch, tmp_path):
    image_path = tmp_path / "sample.png"
    image_path.touch()

    monkeypatch.setattr(extractor, "_load_image", lambda path: "image-object")
    monkeypatch.setattr(extractor.pytesseract, "image_to_string", lambda img: "Hello OCR")

    output_path = extractor.process_image_to_text(image_path)

    assert output_path.name == "sample.txt"
    assert output_path.read_text(encoding="utf-8").strip() == "Hello OCR"


def test_process_image_to_text_respects_custom_output(monkeypatch, tmp_path):
    image_path = tmp_path / "custom.png"
    image_path.touch()
    custom_output = tmp_path / "out" / "result.txt"

    monkeypatch.setattr(extractor, "_load_image", lambda path: "image-object")
    monkeypatch.setattr(extractor.pytesseract, "image_to_string", lambda img: "Custom text")

    output_path = extractor.process_image_to_text(image_path, custom_output)

    assert output_path == custom_output
    assert output_path.read_text(encoding="utf-8").strip() == "Custom text"


def test_extract_text_rejects_unsupported_extension():
    with pytest.raises(ValueError):
        extractor.extract_text(Path("file.pdf"))


def test_extract_text_raises_when_missing_file():
    missing_image = Path("does_not_exist.png")
    with pytest.raises(FileNotFoundError):
        extractor.extract_text(missing_image)
