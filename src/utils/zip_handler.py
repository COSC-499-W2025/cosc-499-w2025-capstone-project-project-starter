"""
Zip File Handler
Extracts and processes zip files for analysis.
"""
from pathlib import Path
from typing import Dict, Any, List, Optional
import zipfile
import tempfile
import shutil
import os


class ZipHandler:
    """Handler for extracting and processing zip files."""
    
    def __init__(self):
        """Initialize zip handler."""
        self.temp_dirs = []
    
    def extract_zip(self, zip_path: str, extract_to: Optional[str] = None) -> str:
        """
        Extract a zip file to a temporary or specified directory.
        
        Args:
            zip_path: Path to the zip file
            extract_to: Optional target directory (creates temp dir if None)
            
        Returns:
            Path to the extracted directory
        """
        zip_path = Path(zip_path)
        
        if not zip_path.exists():
            raise FileNotFoundError(f"Zip file not found: {zip_path}")
        
        if not zipfile.is_zipfile(zip_path):
            raise ValueError(f"Not a valid zip file: {zip_path}")
        
        # Create extraction directory
        if extract_to is None:
            extract_dir = tempfile.mkdtemp(prefix="zip_extract_")
            self.temp_dirs.append(extract_dir)
        else:
            extract_dir = extract_to
            os.makedirs(extract_dir, exist_ok=True)
        
        print(f"📦 Extracting {zip_path.name}...")
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            print(f"   ✅ Extracted to: {extract_dir}")
            return extract_dir
            
        except Exception as e:
            raise RuntimeError(f"Failed to extract zip file: {str(e)}")
    
    def get_zip_contents(self, zip_path: str) -> List[Dict[str, Any]]:
        """
        Get list of files in a zip archive without extracting.
        
        Args:
            zip_path: Path to the zip file
            
        Returns:
            List of file information dictionaries
        """
        zip_path = Path(zip_path)
        
        if not zip_path.exists():
            raise FileNotFoundError(f"Zip file not found: {zip_path}")
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                file_list = []
                for info in zip_ref.filelist:
                    if not info.is_dir():
                        file_list.append({
                            "filename": info.filename,
                            "size": info.file_size,
                            "compressed_size": info.compress_size,
                            "date_time": info.date_time
                        })
                
                return file_list
                
        except Exception as e:
            raise RuntimeError(f"Failed to read zip contents: {str(e)}")
    
    def find_files_in_extracted(
        self,
        extracted_dir: str,
        extensions: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        skip_hidden: bool = True
    ) -> List[str]:
        """
        Find files in extracted directory with optional filtering.
        
        Args:
            extracted_dir: Path to extracted directory
            extensions: Optional list of extensions to include (e.g., ['.py', '.js'])
            exclude_patterns: Optional list of patterns to exclude (e.g., ['node_modules', '__pycache__'])
            skip_hidden: Whether to skip hidden files (starting with .)
            
        Returns:
            List of file paths
        """
        extracted_dir = Path(extracted_dir)
        
        if not extracted_dir.exists():
            raise FileNotFoundError(f"Directory not found: {extracted_dir}")
        
        exclude_patterns = exclude_patterns or [
            '__pycache__',
            'node_modules',
            '.git',
            'venv',
            'env',
            '.venv',
            'dist',
            'build',
            '.pytest_cache',
            '.mypy_cache'
        ]
        
        files = []
        
        for root, dirs, filenames in os.walk(extracted_dir):
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if not any(pattern in d for pattern in exclude_patterns)]
            
            for filename in filenames:
                # Skip hidden files (starting with .) if requested
                if skip_hidden and filename.startswith('.'):
                    continue
                
                file_path = Path(root) / filename
                
                # Check exclusions
                if any(pattern in str(file_path) for pattern in exclude_patterns):
                    continue
                
                # Check extensions if specified
                if extensions:
                    if file_path.suffix.lower() in extensions:
                        files.append(str(file_path))
                else:
                    files.append(str(file_path))
        
        return files
    
    def is_git_repository(self, directory: str) -> bool:
        """
        Check if the directory contains a Git repository.
        
        Args:
            directory: Path to directory
            
        Returns:
            True if directory contains .git folder
        """
        git_dir = Path(directory) / ".git"
        return git_dir.exists() and git_dir.is_dir()
    
    def find_git_repositories(self, directory: str) -> List[str]:
        """
        Find all Git repositories in a directory (including subdirectories).
        
        Args:
            directory: Path to search
            
        Returns:
            List of paths to Git repositories
        """
        directory = Path(directory)
        repos = []
        
        for root, dirs, files in os.walk(directory):
            if '.git' in dirs:
                repos.append(root)
                # Don't traverse into this repo's subdirectories
                dirs[:] = [d for d in dirs if d != '.git']
        
        return repos
    
    def get_directory_structure(self, directory: str, max_depth: int = 3) -> Dict[str, Any]:
        """
        Get a hierarchical view of directory structure.
        
        Args:
            directory: Path to directory
            max_depth: Maximum depth to traverse
            
        Returns:
            Dictionary representing directory structure
        """
        directory = Path(directory)
        
        def build_tree(path: Path, depth: int = 0) -> Dict[str, Any]:
            if depth >= max_depth:
                return {"name": path.name, "type": "directory", "truncated": True}
            
            result = {
                "name": path.name,
                "type": "directory" if path.is_dir() else "file",
                "children": []
            }
            
            if path.is_dir():
                try:
                    for item in sorted(path.iterdir()):
                        # Skip hidden files and common excludes
                        if item.name.startswith('.') or item.name in ['node_modules', '__pycache__']:
                            continue
                        result["children"].append(build_tree(item, depth + 1))
                except PermissionError:
                    result["error"] = "Permission denied"
            
            return result
        
        return build_tree(directory)
    
    def cleanup(self):
        """Clean up temporary directories created during extraction."""
        for temp_dir in self.temp_dirs:
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    print(f"   🧹 Cleaned up: {temp_dir}")
            except Exception as e:
                print(f"   ⚠️  Failed to cleanup {temp_dir}: {e}")
        
        self.temp_dirs = []
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()



