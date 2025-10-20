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