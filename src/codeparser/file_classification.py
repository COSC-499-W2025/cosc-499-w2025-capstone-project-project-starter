import os
import magic


TEXT_MIME_PREFIXES = (
    "text/",
)

TEXT_MIME_EXACT = {
    "application/json",
    "application/xml",
    "application/javascript",
    "application/x-javascript",
    "application/x-sh",
    "application/sql",
    "application/x-httpd-php",
}

TEXT_EXTENSIONS = {
    ".txt", ".md", ".rst", ".csv", ".tsv", ".json", ".jsonl", ".yaml", ".yml", ".xml", ".html",
    ".htm", ".css", ".js", ".jsx", ".ts", ".tsx", ".py", ".java", ".kt", ".kts", ".go", ".rs",
    ".c", ".h", ".cpp", ".hpp", ".cs", ".swift", ".php", ".rb", ".sh", ".bash", ".zsh", ".ps1",
    ".sql", ".toml", ".ini", ".cfg", ".conf", ".properties", ".gradle", ".gitignore", ".dockerfile",
}


def _is_probably_text_by_bytes(path):
    try:
        with open(path, "rb") as f:
            chunk = f.read(8192)
        if not chunk:
            return True
        if b"\x00" in chunk:
            return False
        chunk.decode("utf-8")
        return True
    except Exception:
        return False


def is_binary_file(path):
    """Return True if the given file is binary, False otherwise."""
    ext = os.path.splitext(path)[1].lower()

    try:
        mime = magic.from_file(path, mime=True)
        if isinstance(mime, str):
            mime = mime.strip().lower()
            if mime.startswith(TEXT_MIME_PREFIXES) or mime in TEXT_MIME_EXACT:
                return False
            if ext in TEXT_EXTENSIONS:
                return False
            return True
    except Exception:
        pass

    if ext in TEXT_EXTENSIONS:
        return False
    return not _is_probably_text_by_bytes(path)


def list_text_files(directory):
    """
    Recursively collect all non-binary (text) files under `directory`.
    Returns a list of absolute paths.
    """
    directory = os.path.abspath(os.path.expanduser(directory))

    text_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            path = os.path.join(root, file)
            abs_path = os.path.abspath(path)
            if not is_binary_file(abs_path):
                text_files.append(abs_path)

    return text_files