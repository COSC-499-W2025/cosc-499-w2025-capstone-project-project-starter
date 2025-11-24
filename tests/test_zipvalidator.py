import pytest
import zipfile
import tempfile
import os
from src.main import main
from src.validator import zipvalidation
from unittest.mock import patch

def test_nonexistent_file():
    file = "missing.zip"
    result = zipvalidation.check_zip_file(file)
    assert "does not exist" in result

def test_zip_file():
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        zip_file = tmp.name
    try:
        with zipfile.ZipFile(zip_file, "w") as zf:
            zf.writestr("file.txt", "content")
        result = zipvalidation.check_zip_file(zip_file)
        assert "is a zip file" in result
    finally:
        os.remove(zip_file)

def test_non_zip_file():
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        non_zip_file = tmp.name
        tmp.write(b"hello")
    try:
        result = zipvalidation.check_zip_file(non_zip_file)
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


# --- Fixed main() consent tests ---
import zipfile
from unittest.mock import patch
from src.main import main


def capture_printed(mock_print):
    output = []
    for call in mock_print.call_args_list:
        for arg in call.args:
            output.append(str(arg))
    return output


def test_main_user_consents(tmp_path):
    import zipfile
    from unittest.mock import patch
    import src.main as main_module   # <-- IMPORTANT: import the actual module
    from src.main import main

    # -----------------------------
    # Create dummy ZIP
    # -----------------------------
    zip_file = tmp_path / "dummy.zip"
    unzip_dir = tmp_path / "unzipped"
    unzip_message = f"Extracted to: {unzip_dir}"

    with zipfile.ZipFile(zip_file, "w") as zf:
        zf.writestr("file.txt", "content")

    # -----------------------------
    # Debug mock
    # -----------------------------
    def debug_mock(prompt):
        print(">>> MOCK run_ollama_analysis CALLED")
        return "[EXTERNAL ANALYSIS]"

    # -----------------------------
    # Helper to capture printed text
    # -----------------------------
    def capture_printed(mock_print):
        out = []
        for call in mock_print.call_args_list:
            for arg in call.args:
                out.append(str(arg))
        return out

    # -----------------------------
    # Run main() with patches
    # -----------------------------
    with patch("validator.LLM_permission.input", side_effect=["yes"]), \
         patch("builtins.print") as mock_print, \
         patch.object(main_module, "run_ollama_analysis", side_effect=debug_mock), \
         patch("validator.zipvalidation.unzip_file", return_value=unzip_message), \
         patch("codeparser.parse_core.parse_directory", return_value="parsed"), \
         patch("codeparser.parse_core.summarize_results", return_value=None), \
         patch("sys.argv", ["main.py", str(zip_file)]):

        main()  # <-- run the actual main()

        printed = capture_printed(mock_print)

        # Debug print
        for i, line in enumerate(printed):
            print(f"{i}: {repr(line)}")

        # Assertions
        assert any("zip" in line.lower() for line in printed)


def test_main_user_declines(tmp_path):
    zip_file = tmp_path / "dummy.zip"
    with zipfile.ZipFile(zip_file, "w") as zf:
        zf.writestr("file.txt", "content")

    # Provide denial input
    inputs = ["no"]
    with patch("builtins.input", side_effect=inputs), \
         patch("sys.argv", ["main.py", str(zip_file)]), \
         patch("builtins.print") as mock_print:
        main()
        printed = [str(call.args[0]) for call in mock_print.call_args_list]
        assert any("Consent not given. Exiting." in line for line in printed)
