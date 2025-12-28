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


def unzip_file(zip_path, extract_dir=None, cleanup=True):
    """
    Extract zip file to a directory.
    
    Args:
        zip_path: Path to the zip file
        extract_dir: Optional directory to extract to (if None, uses temp directory)
        cleanup: If True and using temp directory, will clean up after extraction
                 (set to False if you need to keep the files after processing)
    
    Returns:
        Path to the extraction directory
    """
    using_temp_dir = False
    
    if extract_dir is None:
        # Use a temporary directory
        extract_dir = tempfile.mkdtemp(prefix="extracted_")
        using_temp_dir = True
        print(f"📁 Using temporary directory: {extract_dir}")
    else:
        # User provided directory - clean it if it exists
        if os.path.exists(extract_dir):
            print(f"🧹 Cleaning existing directory: {extract_dir}")
            shutil.rmtree(extract_dir, ignore_errors=True)
        
        # Create the directory
        os.makedirs(extract_dir, exist_ok=True)
    
    try:
        # Extract contents
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            file_count = len(zip_ref.namelist())
            zip_ref.extractall(extract_dir)
        
        print(f"✅ Extracted {file_count} files to: {extract_dir}")
        return extract_dir
        
    except Exception as e:
        # Clean up on error
        if using_temp_dir or cleanup:
            shutil.rmtree(extract_dir, ignore_errors=True)
        raise Exception(f"Failed to extract zip: {e}")