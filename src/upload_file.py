import os
import shutil
import zipfile
import json
from config.db_config import with_db_cursor
from parsing.file_validator import validate_uploaded_file, WrongFormatError
from parsing.file_contents_manager import init_file_contents_table, extract_and_store_file_contents, get_file_contents_by_upload_id
from pathlib import Path

UPLOAD_FOLDER = UPLOAD_FOLDER = Path(os.getenv("UPLOAD_FOLDER", "uploads"))

class UploadResult:
    """Encapsulates the result of an upload operation"""
    def __init__(self, success: bool, message: str, error_type: str = None, data: dict = None):
        self.success = success
        self.message = message
        self.error_type = error_type
        self.data = data or {}
    
    def to_dict(self):
        """Convert to dictionary format for UI consumption"""
        return {
            "success": self.success,
            "message": self.message,
            "error_type": self.error_type,
            "data": self.data
        }
def ensure_upload_dir() -> str | None:
    try:
        UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
        return None
    except Exception as e:
        return f"Failed to create upload directory: {e}"

def init_uploaded_files_table():
    """Create the uploaded_files table if it doesn't exist."""
    try:
        with with_db_cursor() as cursor:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS uploaded_files (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255) NOT NULL,
                filepath VARCHAR(500) NOT NULL,
                status VARCHAR(50) DEFAULT 'uploaded',
                metadata JSONB,
                file_data BYTEA,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print(" Uploaded files table initialized")

        # Add last_modified_at column if it doesn't exist
        try:
            with with_db_cursor() as cursor:
                # Add the column if it doesn't exist
                cursor.execute("""
                    ALTER TABLE uploaded_files
                    ADD COLUMN IF NOT EXISTS last_modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
                """)

                # Initialize existing records' last_modified_at to created_at if NULL
                cursor.execute("""
                    UPDATE uploaded_files
                    SET last_modified_at = COALESCE(last_modified_at, created_at)
                    WHERE last_modified_at IS NULL;
                """)
            # commented out to reduce noise
            # print(" uploaded_files table migrated (last_modified_at ensured & initialized)")
        except Exception as e:
            # If migration fails, log but continue
            print(f" [WARN] Skipping last_modified_at migration: {e}")
        
        # Also initialize the file contents table
        init_file_contents_table()
        
    except ConnectionError:
        raise Exception("Failed to connect to database")
    except Exception as e:
        print(f" Error initializing uploaded_files table: {e}")
        raise

def add_file_to_db(filepath) -> UploadResult:
    # 1. Check if file exists
    if not os.path.exists(filepath):
        return UploadResult(False, f"File does not exist: {filepath}", "FILE_NOT_FOUND")

    # 2. Validate file format
    try:
        validate_uploaded_file(filepath)
    except WrongFormatError as e:
        return UploadResult(False, f"Invalid file format: {str(e)}", "INVALID_FORMAT", {"filepath": filepath})

    filename = os.path.basename(filepath)
    dest_path = str(UPLOAD_FOLDER / filename)   # keep as str if the rest of your code expects str

    # 3. Create upload directory (via helper)
    err = ensure_upload_dir()
    if err:
        return UploadResult(
            success=False,
            message=err,
            error_type="DIRECTORY_ERROR",
            data={"destination": str(UPLOAD_FOLDER)}
        )

    # 4. Copy file to upload folder
    try:
        shutil.copy(filepath, dest_path)
        print(f"File copied to {dest_path}")
    except Exception as e:
        return UploadResult(
            success=False,
            message=f"File copy failed: {str(e)}",
            error_type="COPY_ERROR",
            data={"source": filepath, "destination": dest_path}
        )

    # 5. Extract metadata from zip
    file_contents = []
    try:
        if zipfile.is_zipfile(dest_path):
            with zipfile.ZipFile(dest_path, 'r') as zip_ref:
                file_contents = zip_ref.namelist()
            print(f"Files inside zip: {file_contents}")
    except Exception as e:
        return UploadResult(
            success=False,
            message=f"ZIP file extraction failed: {str(e)}",
            error_type="ZIP_EXTRACTION_ERROR",
            data={"filepath": dest_path}
        )

    # 6. Save to database
    try:
        with open(dest_path, "rb") as f:
            zip_bytes = f.read()
        with with_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO uploaded_files (
                    filename,
                    filepath,
                    status,
                    metadata,
                    file_data,
                    last_modified_at
                )
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                RETURNING id
            """, (
                filename,
                dest_path,
                "uploaded",
                json.dumps({"files": file_contents}),
                zip_bytes,
            ))
            uploaded_file_id = cursor.fetchone()[0]

        print("Extracting file contents...")
        extraction_result = extract_and_store_file_contents(uploaded_file_id, dest_path)

        return UploadResult(
            success=True,
            message=f"File '{filename}' uploaded successfully!",
            error_type=None,
            data={
                "file_id": uploaded_file_id,
                "filename": filename,
                "filepath": dest_path,
                "file_count": len(file_contents),
                "files": file_contents
            }
        )

    except ConnectionError:
        return UploadResult(False, "Could not connect to database", "DATABASE_CONNECTION_ERROR")
    except Exception as e:
        return UploadResult(False, f"Database save failed: {str(e)}", "DATABASE_SAVE_ERROR", {"filename": filename})


def get_uploaded_file_contents(uploaded_file_id):
    """
    Retrieve all file contents for a specific uploaded file.
    
    Args:
        uploaded_file_id (int): The ID of the uploaded file record
    
    Returns:
        list: List of file content records
    """
    return get_file_contents_by_upload_id(uploaded_file_id)


def list_uploaded_files():
    """
    Get a list of all uploaded files with their metadata.
    
    Returns:
        list: List of uploaded file records
    """
    try:
        with with_db_cursor() as cursor:
            cursor.execute("""
                SELECT
                    id,
                    filename,
                    filepath,
                    status,
                    metadata,
                    created_at,
                    last_modified_at
                FROM uploaded_files
                ORDER BY created_at DESC
            """)
            
            results = cursor.fetchall()
        
        files = []
        for row in results:
            files.append({
                "id": row[0],
                "filename": row[1],
                "filepath": row[2],
                "status": row[3],
                "metadata": row[4],
                "created_at": row[5],
                "last_modified_at": row[6],
            })
        
        return files
        
    except ConnectionError:
        print("Could not connect to database.")
        return []
    except Exception as e:
        print(f"Error retrieving uploaded files: {e}")
        return []
