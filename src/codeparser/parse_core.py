import os
from .file_classification import is_binary_file


def parse_directory(directory):
    """
    Recursively parse the given directory to classify files as binary or text.

    Args:
        directory (str): The path to the directory to parse.

    Returns:
        dict: A summary dictionary with:
            - total_files (int)
            - binary_files (list[str])
            - text_files (list[str])

    Raises:
        FileNotFoundError: If the specified directory does not exist.
    """
    if not os.path.isdir(directory):
        raise FileNotFoundError(f"Directory not found: {directory}")

    binary_files = []
    text_files = []

    for file_path in _yield_all_files(directory):
        try:
            if is_binary_file(file_path):
                binary_files.append(file_path)
            else:
                text_files.append(file_path)
        except Exception as e:
            # Log or handle unreadable files if needed
            print(f"Warning: could not classify file '{file_path}': {e}")
            binary_files.append(file_path)  # Treat as binary by default

    return {
        "total_files": len(binary_files) + len(text_files),
        "binary_files": binary_files,
        "text_files": text_files
    }


def _yield_all_files(directory):
    """
    Recursively yield all files and symlinks to files under the given directory.

    Args:
        directory (str): Root directory to walk.

    Yields:
        str: Full path to each file or symlinked file found.
    """
    with os.scandir(directory) as it:
        for entry in it:
            path = entry.path
            if entry.is_symlink():
                # If it's a symlink, check if it points to a file
                try:
                    if os.path.isfile(os.readlink(path)) or os.path.isfile(path):
                        yield path
                except OSError:
                    # Broken symlink or permission error — skip or treat as needed
                    continue
            elif entry.is_file():
                yield path
            elif entry.is_dir(follow_symlinks=False):
                yield from _yield_all_files(path)


def summarize_results(summary):
    """
    Print a readable summary of the parsed results.

    Args:
        summary (dict): Dictionary returned by `parse_directory()`.
    """
    print("\n📊 Scan Summary")
    print("------------------")
    print(f"Total files scanned: {summary['total_files']}")
    print(f"Binary files       : {len(summary['binary_files'])}")
    print(f"Text files         : {len(summary['text_files'])}")