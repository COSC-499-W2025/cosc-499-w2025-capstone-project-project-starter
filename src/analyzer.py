import os

def analyze_project(directory):
    """
    Analyzes the project directory to count the total files, and categorize them as text or binary.
    
    Args:
        directory (Path): The path to the directory to analyze.
    
    Returns:
        dict: A summary containing the total file count, binary files, and text files.
    """
    text_files = []
    binary_files = []
    total_files = 0
    
    # Iterate through the files in the directory
    for file in os.listdir(directory):
        file_path = directory / file  # Create the full file path
        
        # Check if it is a file (not a directory)
        if file_path.is_file():
            total_files += 1
            
            # Classify the file as binary or text
            if is_binary(file_path):
                binary_files.append(file)
            else:
                text_files.append(file)
    
    # Return the summary
    return {
        "total_files": total_files,
        "binary_files": binary_files,
        "text_files": text_files
    }

def is_binary(file_path):
    """
    Determines whether a file is binary or not by checking for non-printable characters.
    
    Args:
        file_path (Path): The path to the file.
    
    Returns:
        bool: True if the file is binary, False if it's a text file.
    """
    try:
        with open(file_path, 'rb') as file:  # Open the file in binary mode
            # Read the first 1024 bytes (or less if the file is smaller)
            chunk = file.read(1024)
            # Check if there are non-printable characters in the chunk
            # Printable characters are usually in the range of 32-126
            for byte in chunk:
                if byte < 32 or byte > 126:
                    return True  # It's a binary file
        return False  # If no non-printable characters are found, it's a text file
    except Exception as e:
        # Catch any other exceptions, though this is unlikely
        print(f"Unexpected error when reading file {file_path}: {e}")
        return True  # Assume it's binary if there's any error
