import os
import zipfile


def check_zip_file(file_path):
    if not os.path.exists(file_path):
        return f"{file_path} does not exist"

    if zipfile.is_zipfile(file_path):
        return f"{file_path} is a zip file"
    else:
        return f"{file_path} is not a zip file"


def unzip_file(zip_path, extract_dir=None):
    if extract_dir is None:
        # Safer than replace(".zip", "") in case filename contains ".zip" elsewhere
        extract_dir = os.path.splitext(zip_path)[0]

    # Prevent accidental overwrite
    if os.path.exists(extract_dir) and os.listdir(extract_dir):
        raise FileExistsError("Extraction directory already exists and is not empty.")

    # Ensure extraction directory exists
    os.makedirs(extract_dir, exist_ok=True)

    # Extract contents
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_dir)

    # Return ONLY the real directory path
    return extract_dir