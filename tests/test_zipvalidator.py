import pytest
import zipfile
import tempfile
import os
from src.main import check_zip_file

def test_nonexistent_file():
    # just provide a path that doesn't exist
    file = "missing.zip"
    result = check_zip_file(file)
    assert "does not exist" in result

def test_zip_file():
    # create a temporary zip file
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        zip_file = tmp.name
    try:
        # write a dummy file into the zip
        with zipfile.ZipFile(zip_file, "w") as zf:
            zf.writestr("file.txt", "content")

        result = check_zip_file(zip_file)
        assert zip_file in result
        assert "is a zip file" in result
    finally:
        os.remove(zip_file)

def test_non_zip_file():
    # create a temporary non-zip file
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        non_zip_file = tmp.name
        tmp.write(b"hello")
    try:
        result = check_zip_file(non_zip_file)
        assert non_zip_file in result
        assert "is not a zip file" in result
    finally:
        os.remove(non_zip_file)
