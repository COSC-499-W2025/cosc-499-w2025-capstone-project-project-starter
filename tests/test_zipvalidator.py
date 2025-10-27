import pytest
import zipfile
import tempfile
import os
from src.main import check_zip_file, main
from unittest.mock import patch

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

# --- New tests for consent in main() ---

def test_main_user_consents(tmp_path):
    # create a dummy zip file
    zip_file = tmp_path / "dummy.zip"
    with zipfile.ZipFile(zip_file, "w") as zf:
        zf.writestr("file.txt", "content")

    # mock input to simulate user consent, mock sys.argv for file argument
    with patch("builtins.input", return_value="y"), \
         patch("sys.argv", ["main.py", str(zip_file)]), \
         patch("builtins.print") as mock_print:
        main()
        # check that the zip result is printed
        printed = [call.args[0] for call in mock_print.call_args_list]
        assert any("is a zip file" in line for line in printed)

def test_main_user_declines(tmp_path):
    # create a dummy zip file
    zip_file = tmp_path / "dummy.zip"
    with zipfile.ZipFile(zip_file, "w") as zf:
        zf.writestr("file.txt", "content")

    # mock input to simulate user declining consent
    with patch("builtins.input", return_value="n"), \
         patch("sys.argv", ["main.py", str(zip_file)]), \
         patch("builtins.print") as mock_print:
        main()
        printed = [call.args[0] for call in mock_print.call_args_list]
        assert "Consent not given. Exiting." in printed

def test_unzip_file():
    # create a temporary zip file same as before
    # this test assumes that test_zip_file() and non_zip_file() have 
    # already run and passed
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        zip_file = tmp.name
        try:
        # write a dummy file into the zip
            with zipfile.ZipFile(zip_file, "w") as zf:
                zf.writestr("file.txt", "content")
            
            result = unzip_file(zip_file)
            assert zip_file in result
            assert "extraction successful!" in result
        finally:
            os.remove(zip_file)
