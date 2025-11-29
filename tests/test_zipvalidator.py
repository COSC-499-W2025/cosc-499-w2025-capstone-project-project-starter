import pytest
import zipfile
import tempfile
import os
from unittest.mock import patch
from src.main import main
from src.validator import zipvalidation


def test_nonexistent_file():
    file = "missing.zip"
    result = zipvalidation.check_zip_file(file)
    assert "does not exist" in result
    assert file in result  # fixed typo (was 'missing')


def test_zip_file():
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        zip_file = tmp.name
    try:
        with zipfile.ZipFile(zip_file, "w") as zf:
            zf.writestr("file.txt", "content")
        result = zipvalidation.check_zip_file(zip_file)
        assert zip_file in result
        assert "is a zip file" in result
    finally:
        os.remove(zip_file)


def test_non_zip_file():
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        non_zip_file = tmp.name
        tmp.write(b"hello")
    try:
        result = zipvalidation.check_zip_file(non_zip_file)
        assert non_zip_file in result
        assert "is not a zip file" in result
    finally:
        os.remove(non_zip_file)


def test_unzip_creates_new_folder():
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_file = os.path.join(tmpdir, "dummy.zip")
        extract_dir = os.path.join(tmpdir, "extracted")

        with zipfile.ZipFile(zip_file, "w") as zf:
            zf.writestr("file.txt", "content")

        result = zipvalidation.unzip_file(zip_file, extract_dir=extract_dir)
        assert "extraction successful" in result
        assert os.path.exists(os.path.join(extract_dir, "file.txt"))


def test_unzip_existing_nonempty_folder():
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_file = os.path.join(tmpdir, "dummy.zip")
        extract_dir = os.path.join(tmpdir, "extracted")

        with zipfile.ZipFile(zip_file, "w") as zf:
            zf.writestr("file.txt", "content")

        os.makedirs(extract_dir)
        with open(os.path.join(extract_dir, "old.txt"), "w") as f:
            f.write("old data")

        import pytest
        with pytest.raises(FileExistsError):
            zipvalidation.unzip_file(zip_file, extract_dir=extract_dir)
