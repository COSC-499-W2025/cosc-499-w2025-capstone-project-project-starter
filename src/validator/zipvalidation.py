import os
import zipfile
import time


def check_zip_file(file_path):
    # Check if the zip folder actually exists on the users system
    if not os.path.exists(file_path):
        return f"{file_path} does not exist"

    # Check if the file is a valid zip file
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

    # Extract contents and preserve original modification times
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        for info in zip_ref.infolist():
            extracted_path = zip_ref.extract(info, path=extract_dir)

            # Convert info.date_time tuple to timestamp
            mod_time = time.mktime(info.date_time + (0, 0, -1))
            # Update file's access and modification times
            os.utime(extracted_path, (mod_time, mod_time))

    # Return ONLY the real directory path
    return extract_dir