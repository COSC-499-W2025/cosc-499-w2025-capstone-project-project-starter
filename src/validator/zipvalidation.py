import os
import zipfile

def check_zip_file(file):

    # first ensure file exists
    if not os.path.exists(file):
        return f"Error: file '{file}' does not exist"

    # then check if its a zip
    if zipfile.is_zipfile(file):
        return f"{file} is a zip file"
    else:
        return f"{file} is not a zip file"
    
def unzip_file(file, extract_dir=None):

    # extracts the directory from the zipfile with the same name (without .zip)
    if extract_dir is None:
        extract_dir = os.path.splitext(file)[0]

    # if folder exists and is non-empty, raise an error
    if os.path.exists(extract_dir):
        if os.listdir(extract_dir):  # folder not empty
            raise FileExistsError(f"Folder '{extract_dir}' already exists and is not empty.")
    else:
        # create folder if it doesn't exist
        os.makedirs(extract_dir)

    # perform extraction
    with zipfile.ZipFile(file, "r") as zf:
        zf.extractall(extract_dir)

    return f"{file} extraction successful! Extracted to: {extract_dir}"

