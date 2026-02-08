"""
Zip file parsing functionality.
"""

import json
import tempfile
import shutil
import zipfile
import hashlib
from pathlib import Path
from typing import Union

from .models import ZipIndex, ZipEntry
from src.categorize.file_categorizer import categorize_folder_structure


class ZipParseError(Exception):
    """Raised when zip file parsing fails."""
    pass


def parse_zip(zip_path: Union[str, Path]) -> ZipIndex:
    """Parse a zip file and return structured metadata."""
    zip_path = Path(zip_path)
    
    # Validate file exists
    if not zip_path.exists():
        raise ZipParseError(f"File not found: {zip_path}")
    
    # Validate file is readable
    if not zip_path.is_file():
        raise ZipParseError(f"Path is not a file: {zip_path}")
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Validate zip file integrity
            if zf.testzip() is not None:
                raise ZipParseError(f"Corrupt zip file: {zip_path}")
            
            files = []
            total_uncompressed = 0
            total_compressed = 0
            
            for info in zf.infolist():
                # Skip directories
                if info.is_dir():
                    continue
                
                # Basic path normalization
                rel_path = info.filename.replace('\\', '/')
                if rel_path.startswith('/'):
                    rel_path = rel_path[1:]
                
                # Absolute path
                abs_path = str((zip_path.parent / rel_path).resolve())
                
                # Calculate depth
                depth = len(Path(rel_path).parts) - 1
                
                # Extract file extension
                ext = Path(rel_path).suffix.lower()
                if ext.startswith('.'):
                    ext = ext[1:]
                
                # Read file content for hash
                with zf.open(info) as file_obj:
                    content = file_obj.read()
                
                # Compute SHA256 hash
                sha256_hash = hashlib.sha256(content).hexdigest()
                
                # Simple text detection
                is_text = _is_text_content(content)
                
                # Determine if compressed
                is_compressed = info.compress_type != zipfile.ZIP_STORED
                
                # Create file entry
                entry = ZipEntry(
                    abs_path=abs_path,
                    rel_path=rel_path,
                    size=info.file_size,
                    compressed_size=info.compress_size,
                    is_compressed=is_compressed,
                    sha256=sha256_hash,
                    depth=depth,
                    ext=ext,
                    is_text_guess=is_text
                )
                
                files.append(entry)
                total_uncompressed += info.file_size
                total_compressed += info.compress_size
            
            return ZipIndex(
                root_name=zip_path.name,
                file_count=len(files),
                total_uncompressed_bytes=total_uncompressed,
                total_compressed_bytes=total_compressed,
                files=files
            )
            
    except zipfile.BadZipFile:
        raise ZipParseError(f"Not a valid zip file: {zip_path}")
    except Exception as e:
        raise ZipParseError(f"Unexpected error parsing zip file {zip_path}: {e}")


def _is_text_content(content: bytes) -> bool:
    """Simple text detection heuristic."""
    if not content:
        return True
    
    try:
        content.decode('utf-8', errors='ignore')
        return True
    except Exception:
        return False
    

def categorize_parse_zip(zip_path: Union[str, Path]) -> dict:
    """
    Parse a ZIP file, extract its contents to a temporary folder,
    categorize the extracted files by type, and include detailed file info
    from the ZIP metadata.

    Args:
        zip_path (str | Path): Path to the ZIP file to parse and categorize.

    Returns:
        dict: A structured representation of the ZIP contents including:
              - ZIP metadata
              - File info for each entry
              - Categorized folder structure
    """
    zip_path = Path(zip_path)

    try:
        # Parse ZIP metadata
        zip_index = parse_zip(zip_path)
        print(f"[INFO] Parsed ZIP '{zip_index.root_name}' with {zip_index.file_count} files")

        # Extract contents to a temporary directory
        temp_dir = Path(tempfile.mkdtemp(prefix="unzipped_"))
        print(f"[INFO] Extracting ZIP to temporary folder: {temp_dir}")

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(temp_dir)

        # Categorize extracted files
        categorized_structure = categorize_folder_structure(temp_dir)

        # Build file info list from ZipIndex, but only for actually extracted files
        file_info = []

        for entry in zip_index.files:
            # Skip macOS system files and duplicates
            if "__MACOSX" in entry.rel_path or Path(entry.rel_path).name.startswith("._"):
                continue

            # Compute where this file was extracted to
            extracted_path = temp_dir / entry.rel_path
            if not extracted_path.exists():
                # Skip entries that don't exist in the extracted folder
                continue

            abs_extracted_path = str(extracted_path.resolve())

            file_info.append({
                "abs_path": abs_extracted_path,
                "rel_path": entry.rel_path,
                "size": entry.size,
                "compressed_size": entry.compressed_size,
                "is_compressed": entry.is_compressed,
                "sha256": entry.sha256,
                "depth": entry.depth,
                "ext": entry.ext,
                "is_text_guess": entry.is_text_guess,
            })

        # Combine all components
        combined = {
            "zip_metadata": {
                "root_name": zip_index.root_name,
                "file_count": zip_index.file_count,
                "total_uncompressed_bytes": zip_index.total_uncompressed_bytes,
                "total_compressed_bytes": zip_index.total_compressed_bytes,
            },
            "file_info": file_info,
            "categorized_contents": categorized_structure
        }
        return combined

    except ZipParseError as e:
        print(f"[ERROR] ZIP parsing failed: {e}")
        return {}
    except Exception as e:
        print(f"[ERROR] categorize_parse_zip() failed: {e}")
        return {}
    finally:
        # Clean up temporary directory
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass

# if __name__ == "__main__":
#     result = categorize_parse_zip("./tests/categorize/demo_projects.zip")
#     print(json.dumps(result, indent=2))