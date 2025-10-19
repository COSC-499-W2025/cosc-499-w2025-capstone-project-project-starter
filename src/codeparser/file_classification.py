import os
import magic

def is_binary_file(path):
    """Return True if the given file is binary, False otherwise."""
    try:
        mime = magic.from_file(path, mime=True)
        return not mime.startswith('text/')
    except Exception:
        return True

def scan_directory_for_binaries(directory):
    """Recursively scan the given directory and for now just print whether each file is binary or not."""
    for root, _, files in os.walk(directory):
        for file in files:
            path = os.path.join(root, file)
            binary = is_binary_file(path)
            print(f"{binary}: {path}")