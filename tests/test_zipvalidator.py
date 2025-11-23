import os
import zipfile
import pytest

from src.validator import zipvalidation


def test_check_zip_file_nonexistent(tmp_path):
    # path that does not exist
    missing = tmp_path / "missing.zip"
    result = zipvalidation.check_zip_file(str(missing))
    assert "does not exist" in result
    assert str(missing) in result


def test_check_zip_file_with_zip(tmp_path):
    zip_path = tmp_path / "test_archive.zip"

    # create a valid zip file
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("file.txt", "content")

    result = zipvalidation.check_zip_file(str(zip_path))
    assert str(zip_path) in result
    assert "is a zip file" in result


def test_check_zip_file_with_non_zip(tmp_path):
    non_zip_path = tmp_path / "not_a_zip.txt"
    non_zip_path.write_text("some text")

    result = zipvalidation.check_zip_file(str(non_zip_path))
    assert str(non_zip_path) in result
    assert "is not a zip file" in result

def _create_simple_zip(zip_path):
    """Create a simple zip at zip_path containing one file 'file.txt'."""
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("file.txt", "content")


def test_unzip_creates_new_folder_default_extract_dir(tmp_path):
    zip_path = tmp_path / "dummy.zip"
    _create_simple_zip(zip_path)

    # default extract_dir should be zip path without ".zip"
    expected_extract_dir = tmp_path / "dummy"

    result = zipvalidation.unzip_file(str(zip_path))

    assert "extraction successful" in result
    assert str(zip_path) in result
    assert os.path.isdir(expected_extract_dir)
    assert os.path.isfile(expected_extract_dir / "file.txt")


def test_unzip_creates_specified_new_folder(tmp_path):
    zip_path = tmp_path / "dummy.zip"
    _create_simple_zip(zip_path)

    extract_dir = tmp_path / "extracted_here"

    result = zipvalidation.unzip_file(str(zip_path), extract_dir=str(extract_dir))

    assert "extraction successful" in result
    assert str(zip_path) in result
    assert os.path.isdir(extract_dir)
    assert os.path.isfile(extract_dir / "file.txt")


def test_unzip_existing_empty_folder(tmp_path):
    zip_path = tmp_path / "dummy.zip"
    _create_simple_zip(zip_path)

    extract_dir = tmp_path / "extracted"
    os.makedirs(extract_dir)  # existing but empty

    result = zipvalidation.unzip_file(str(zip_path), extract_dir=str(extract_dir))

    assert "extraction successful" in result
    assert os.path.isdir(extract_dir)
    assert os.path.isfile(extract_dir / "file.txt")


def test_unzip_existing_nonempty_folder_raises(tmp_path):
    zip_path = tmp_path / "dummy.zip"
    _create_simple_zip(zip_path)

    extract_dir = tmp_path / "extracted"
    os.makedirs(extract_dir)
    # make directory non-empty
    (extract_dir / "old.txt").write_text("old data")

    with pytest.raises(FileExistsError) as excinfo:
        zipvalidation.unzip_file(str(zip_path), extract_dir=str(extract_dir))

    assert "already exists and is not empty" in str(excinfo.value)


def test_unzip_raises_for_missing_zip(tmp_path):
    missing_zip = tmp_path / "missing.zip"

    with pytest.raises(FileNotFoundError):
        zipvalidation.unzip_file(str(missing_zip))
