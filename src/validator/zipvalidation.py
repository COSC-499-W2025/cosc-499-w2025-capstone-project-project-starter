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
    
def unzip_file(file):

    # get the parent folder name to extract to
    extract_dir = os.path.dirname(file)

    with zipfile.ZipFile(file,'r') as unzipf:
        unzipf.extractall(extract_dir)

    # modify function behaviour to return the extracted folder path

    return os.path.splitext(file)[0]
