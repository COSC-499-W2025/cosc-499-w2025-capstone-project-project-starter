import os
import zipfile
import tempfile
import shutil


def check_zip_file(file_path):
    if not os.path.exists(file_path):
        return f"{file_path} does not exist"

    if zipfile.is_zipfile(file_path):
        return f"{file_path} is a zip file"
    else:
        return f"{file_path} is not a zip file"


def unzip_file(zip_path, extract_dir=None, cleanup=True, overwrite=False):
    """
    Extract zip file to a directory.
    
    Args:
        zip_path: Path to the zip file
        extract_dir: Optional directory to extract to (if None, uses temp directory)
        cleanup: If True and using temp directory, will clean up after extraction
                 (set to False if you need to keep the files after processing)
        overwrite: If True, clean existing directory; if False, raise FileExistsError
                   when directory exists and is not empty. Default is False to match
                   original behavior and pass existing tests.
    
    Returns:
        Path to the extraction directory
    """
    using_temp_dir = False
    
    if extract_dir is None:
        # Use a temporary directory
        extract_dir = tempfile.mkdtemp(prefix="extracted_")
        using_temp_dir = True
        # Temp directories are always "overwrite" since they're unique
        overwrite = True
    else:
        # User provided directory - check if it exists and has content
        if os.path.exists(extract_dir):
            if os.listdir(extract_dir):  # Directory is not empty
                if overwrite:
                    # Clean it if overwrite is True
                    shutil.rmtree(extract_dir, ignore_errors=True)
                    os.makedirs(extract_dir, exist_ok=True)
                else:
                    # Raise error if overwrite is False (original behavior)
                    raise FileExistsError("Extraction directory already exists and is not empty.")
            else:
                # Directory exists but is empty, use it
                os.makedirs(extract_dir, exist_ok=True)
        else:
            # Directory doesn't exist, create it
            os.makedirs(extract_dir, exist_ok=True)
    
    try:
        # Extract contents
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            file_count = len(zip_ref.namelist())
            zip_ref.extractall(extract_dir)
        
        return extract_dir
        
    except Exception as e:
        # Clean up on error
        if using_temp_dir or cleanup:
            shutil.rmtree(extract_dir, ignore_errors=True)
        raise Exception(f"Failed to extract zip: {e}")