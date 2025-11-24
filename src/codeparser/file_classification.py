import os
import magic


def is_binary_file(path):
    """Return True if the given file is binary, False otherwise."""
    try:
        mime = magic.from_file(path, mime=True)
        return not mime.startswith("text/")
    except Exception:
        # On failure to determine MIME type, treat as binary to be safe.
        return True

def list_text_files(directory):
    """
    Recursively collect all non-binary (text) files under `directory`.
    Returns a list of absolute paths.
    """
    text_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            path = os.path.join(root, file)
            if not is_binary_file(path):
                text_files.append(path)
    return text_files
