# tests/test_upload_file.py
import sys
import os
import pytest
import zipfile
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Adjust the path to import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
# Added WrongFormatError to make it easier to simulate the error types thrown by the validator in tests.
from src.upload_file import add_file_to_db, UPLOAD_FOLDER, UploadResult, WrongFormatError


class TestUploadFile:
    """Test suite for upload_file.py functionality"""
    
    def setup_method(self):
        """Set up test environment before each test"""
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        # Create a temporary upload directory to avoid creating uploads/ in project root
        self.temp_upload_dir = Path(tempfile.mkdtemp())
        # Patch UPLOAD_FOLDER to use temp directory
        self.upload_folder_patcher = patch('src.upload_file.UPLOAD_FOLDER', 
                                          self.temp_upload_dir)
        self.mock_upload_folder = self.upload_folder_patcher.start()
        
    def teardown_method(self):
        """Clean up after each test"""
        # Stop the patcher
        if hasattr(self, 'upload_folder_patcher'):
            self.upload_folder_patcher.stop()
        # Remove temporary directories
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        if hasattr(self, 'temp_upload_dir') and self.temp_upload_dir.exists():
            shutil.rmtree(str(self.temp_upload_dir))
        # Clean up actual uploads/ folder if it was accidentally created
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        actual_uploads = os.path.join(project_root, 'uploads')
        if os.path.exists(actual_uploads) and os.path.isdir(actual_uploads):
            try:
                # Only remove if it's empty or contains only test files
                files = os.listdir(actual_uploads)
                if not files or all(f.startswith('test') for f in files):
                    shutil.rmtree(actual_uploads)
            except Exception:
                pass  # Ignore cleanup errors
    
    def create_test_zip(self, filename="test.zip", content="test content"):
        """Helper method to create a test ZIP file"""
        zip_path = os.path.join(self.test_dir, filename)
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("test_file.txt", content)
        return zip_path
    
    def create_invalid_file(self, filename="test.txt", content="not a zip"):
        """Helper method to create an invalid file"""
        file_path = os.path.join(self.test_dir, filename)
        with open(file_path, 'w') as f:
            f.write(content)
        return file_path
    
    @patch('src.upload_file.extract_and_store_file_contents')
    @patch('src.upload_file.zipfile.is_zipfile')
    @patch('src.upload_file.zipfile.ZipFile')
    @patch('builtins.open', create=True)
    @patch('src.upload_file.shutil.copy')
    @patch('src.upload_file.with_db_cursor')
    @patch('src.parsing.file_validator.validate_uploaded_file')
    @patch('src.upload_file.os.path.exists')
    def test_add_file_to_db_success(self, mock_exists, mock_validate, mock_with_db_cursor, mock_copy, mock_open, mock_zipfile, mock_is_zipfile, mock_extract_and_store_file_contents):

        """Test successful file upload to database"""
        # Create a valid ZIP file for testing
        zip_path = self.create_test_zip()
        
        # Mock file existence check - return True for source file, False for destination
        def exists_side_effect(path):
            return path == zip_path
        mock_exists.side_effect = exists_side_effect
        
        # Mock validation to pass
        mock_validate.return_value = None
        
        # Mock file operations
        mock_is_zipfile.return_value = True
        mock_zip_instance = MagicMock()
        mock_zip_context = MagicMock()
        mock_zip_context.namelist.return_value = ['test_file.txt']
        mock_zip_instance.__enter__.return_value = mock_zip_context
        mock_zipfile.return_value = mock_zip_instance
        
        # Mock file reading
        mock_file_obj = MagicMock()
        mock_file_obj.read.return_value = b'fake zip content'
        mock_open.return_value.__enter__.return_value = mock_file_obj
        
        # Mock the database cursor
        mock_cursor = Mock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_cursor
        mock_with_db_cursor.return_value = mock_context
        mock_cursor.fetchone.return_value = [123]  # Mock file_id

        # Call the function to add the file to the Database
        result = add_file_to_db(zip_path)
        
        # Verify result is UploadResult with success=True
        assert isinstance(result, UploadResult)
        assert result.success is True
        assert result.error_type is None
        assert "uploaded successfully" in result.message
        assert "file_id" in result.data
        assert result.data["filename"] == "test.zip"
        assert result.data["file_count"] >= 1
        
        # Verify database operations
        mock_with_db_cursor.assert_called_once()
        mock_cursor.execute.assert_called_once()
        
        # Verify the execute call contains correct parameters
        call_args = mock_cursor.execute.call_args
        assert "INSERT INTO uploaded_files" in call_args[0][0]
        assert call_args[0][1][0] == "test.zip"  # filename
        assert call_args[0][1][2] == "uploaded"  # status
        assert call_args[0][1][5] is None  # user_name (default None)
    
    # this is a test for a non-existent file
    def test_add_file_to_db_nonexistent_file(self):

        """Test handling of non-existent file"""
        nonexistent_path = os.path.join(self.test_dir, "nonexistent.zip")
        
        # Should return UploadResult with error
        result = add_file_to_db(nonexistent_path)
        assert isinstance(result, UploadResult)
        assert result.success is False
        assert result.error_type == "FILE_NOT_FOUND"
        assert "does not exist" in result.message
    
    @patch('src.upload_file.shutil.copy')
    def test_add_file_to_db_invalid_extension(self, mock_copy):
        """Test handling of file with invalid extension"""
        invalid_file = self.create_invalid_file("test.txt")
        
        # Should return UploadResult with format error
        result = add_file_to_db(invalid_file)
        assert isinstance(result, UploadResult)
        assert result.success is False
        assert result.error_type == "INVALID_FORMAT"
        assert "Invalid file format" in result.message
    
    # This test should now correspond to "pseudo-zip (content is not zip, but the extension is .zip)",
    # Expect error_type to be INVALID_ZIP, and include newly added friendly hint.
    @patch('src.upload_file.shutil.copy')
    def test_add_file_to_db_invalid_zip_file(self, mock_copy):
        """Test handling of corrupted/invalid ZIP file with .zip extension"""
        # Create a file with .zip extension but invalid content
        fake_zip_path = os.path.join(self.test_dir, "fake.zip")
        with open(fake_zip_path, 'w') as f:
            f.write("This is not a valid ZIP file")
        
        result = add_file_to_db(fake_zip_path)
        assert isinstance(result, UploadResult)
        assert result.success is False
        assert result.error_type == "INVALID_ZIP"
        assert "has a .zip extension but is not a valid ZIP archive" in result.message
    
    @patch('src.upload_file.extract_and_store_file_contents')
    @patch('src.upload_file.zipfile.is_zipfile')
    @patch('src.upload_file.zipfile.ZipFile')
    @patch('builtins.open', create=True)
    @patch('src.upload_file.shutil.copy')
    @patch('src.upload_file.with_db_cursor')
    @patch('src.parsing.file_validator.validate_uploaded_file')
    @patch('src.upload_file.os.path.exists')
    # This is a mock database connection and it mocks it to return None to see if the function handles it correctly when the database fails to connect
    def test_add_file_to_db_database_connection_failure(self, mock_exists, mock_validate, mock_with_db_cursor, mock_copy, mock_open, mock_zipfile, mock_is_zipfile, mock_extract_and_store_file_contents):
        """Test handling of database connection failure"""
        zip_path = self.create_test_zip()
        
        # Mock file existence check
        def exists_side_effect(path):
            return path == zip_path
        mock_exists.side_effect = exists_side_effect
        mock_validate.return_value = None
        
        # Mock file operations
        mock_is_zipfile.return_value = True
        mock_zip_instance = MagicMock()
        mock_zip_context = MagicMock()
        mock_zip_context.namelist.return_value = ['test_file.txt']
        mock_zip_instance.__enter__.return_value = mock_zip_context
        mock_zipfile.return_value = mock_zip_instance
        
        # Mock file reading
        mock_file_obj = MagicMock()
        mock_file_obj.read.return_value = b'fake zip content'
        mock_open.return_value.__enter__.return_value = mock_file_obj
        
        # Mock database connection failure
        mock_with_db_cursor.side_effect = ConnectionError("Could not connect to database")
        
        # Should return UploadResult with database error
        result = add_file_to_db(zip_path)
        assert isinstance(result, UploadResult)
        assert result.success is False
        assert result.error_type == "DATABASE_CONNECTION_ERROR"
        # Relaxed matching to avoid being overly sensitive to the entire sentence.
        assert "connect to the database" in result.message
    
    @patch('src.upload_file.shutil.copy')
    def test_add_file_to_db_copy_failure(self, mock_copy):
        """Test handling of file copy failure"""
        zip_path = self.create_test_zip()
        
        # Mock file copy failure
        mock_copy.side_effect = Exception("Permission denied")
        
        result = add_file_to_db(zip_path)
        assert isinstance(result, UploadResult)
        assert result.success is False
        assert result.error_type == "COPY_ERROR"
        assert "File copy failed" in result.message
        assert "source" in result.data
        assert "destination" in result.data
    
    @patch('src.upload_file.ensure_upload_dir', return_value="Failed to create upload directory: Permission denied")
    def test_add_file_to_db_directory_creation_failure(self, mock_ensure):
        zip_path = self.create_test_zip()
        result = add_file_to_db(zip_path)
        assert isinstance(result, UploadResult)
        assert result.success is False
        assert result.error_type == "DIRECTORY_ERROR"
        assert "Failed to create upload directory" in result.message

    
    @patch('src.upload_file.extract_and_store_file_contents')
    @patch('src.upload_file.zipfile.is_zipfile')
    @patch('src.upload_file.zipfile.ZipFile')
    @patch('builtins.open', create=True)
    @patch('src.upload_file.shutil.copy')
    @patch('src.upload_file.with_db_cursor')
    @patch('src.parsing.file_validator.validate_uploaded_file')
    @patch('src.upload_file.os.path.exists')
    def test_upload_result_to_dict(self, mock_exists, mock_validate, mock_with_db_cursor, mock_copy, mock_open, mock_zipfile, mock_is_zipfile, mock_extract_and_store_file_contents):
        """Test UploadResult.to_dict() method from actual upload operation"""
        zip_path = self.create_test_zip()
        
        # Mock file existence check
        def exists_side_effect(path):
            return path == zip_path
        mock_exists.side_effect = exists_side_effect
        mock_validate.return_value = None
        
        # Mock file operations
        mock_is_zipfile.return_value = True
        mock_zip_instance = MagicMock()
        mock_zip_context = MagicMock()
        mock_zip_context.namelist.return_value = ['test_file.txt']
        mock_zip_instance.__enter__.return_value = mock_zip_context
        mock_zipfile.return_value = mock_zip_instance
        
        # Mock file reading
        mock_file_obj = MagicMock()
        mock_file_obj.read.return_value = b'fake zip content'
        mock_open.return_value.__enter__.return_value = mock_file_obj
        
        # Mock successful database operation
        mock_cursor = Mock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_cursor
        mock_with_db_cursor.return_value = mock_context
        mock_cursor.fetchone.return_value = [456]
        
        # Execute actual upload
        result = add_file_to_db(zip_path)
        
        # Convert to dict and verify structure
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert result_dict["success"] is True
        assert "message" in result_dict
        assert "error_type" in result_dict
        assert "data" in result_dict
        assert result_dict["error_type"] is None
        assert result_dict["data"]["file_id"] == 456
        assert result_dict["data"]["filename"] == "test.zip"
    
    def test_upload_result_with_error(self):
        """Test UploadResult error handling from actual failed operation"""
        # Test with multiple error scenarios
        nonexistent_path = os.path.join(self.test_dir, "nonexistent.zip")
        result = add_file_to_db(nonexistent_path)
        
        # Verify error result structure
        assert isinstance(result, UploadResult)
        assert result.success is False
        assert result.error_type == "FILE_NOT_FOUND"
        assert len(result.message) > 0
        
        # Test to_dict() on error result
        result_dict = result.to_dict()
        assert result_dict["success"] is False
        assert result_dict["error_type"] == "FILE_NOT_FOUND"
        assert "does not exist" in result_dict["message"]

    # [Added]
    # Simulate the validator to directly throw WrongFormatError("The uploaded file is not a valid ZIP archive.")
    # Confirms that the INVALID_ZIP branch added in add_file_to_db (i.e., the text currently seen in the CLI) will be executed.
    @patch('src.upload_file.os.path.exists', return_value=True)
    @patch('src.parsing.file_validator.validate_uploaded_file')
    def test_invalid_zip_message_from_validator_triggers_invalid_zip(self, mock_validate, mock_exists):
        """Validator reports 'not a valid ZIP' -> should produce friendly INVALID_ZIP message."""
        fake_zip_path = os.path.join(self.test_dir, "fake_from_validator.zip")

        mock_validate.side_effect = WrongFormatError("The uploaded file is not a valid ZIP archive.")

        result = add_file_to_db(fake_zip_path)

        assert isinstance(result, UploadResult)
        assert result.success is False
        assert result.error_type == "INVALID_ZIP"
        assert "has a .zip extension but is not a valid ZIP archive" in result.message

    # [Added] New Test 2:
    # The validator allows it, but zipfile.is_zipfile(dest_path) in 4.5 returns False.
    # The subsequent defensive checks will also give INVALID_ZIP and a friendly hint.
    @patch('src.upload_file.extract_and_store_file_contents')
    @patch('src.upload_file.zipfile.is_zipfile')
    @patch('src.upload_file.shutil.copy')
    @patch('src.parsing.file_validator.validate_uploaded_file')
    @patch('src.upload_file.os.path.exists', return_value=True)
    def test_invalid_zip_after_copy_triggers_guard_check(self, mock_exists, mock_validate, mock_copy, mock_is_zipfile, mock_extract):
        """Guard check: non-zip content detected by zipfile.is_zipfile(dest_path) -> INVALID_ZIP."""
        zip_path = self.create_test_zip("guard_test.zip")

        mock_validate.return_value = None
        mock_is_zipfile.return_value = False  # simulate that dest_path is not a real zip

        result = add_file_to_db(zip_path)

        assert isinstance(result, UploadResult)
        assert result.success is False
        assert result.error_type == "INVALID_ZIP"
        assert "has a .zip extension but is not a valid ZIP archive" in result.message

    @patch('src.upload_file.extract_and_store_file_contents')
    @patch('src.upload_file.zipfile.is_zipfile')
    @patch('src.upload_file.zipfile.ZipFile')
    @patch('builtins.open', create=True)
    @patch('src.upload_file.shutil.copy')
    @patch('src.upload_file.with_db_cursor')
    @patch('src.parsing.file_validator.validate_uploaded_file')
    @patch('src.upload_file.os.path.exists')
    def test_add_file_to_db_with_user_name(self, mock_exists, mock_validate, mock_with_db_cursor, mock_copy, mock_open, mock_zipfile, mock_is_zipfile, mock_extract_and_store_file_contents):
        """Test file upload with user_name parameter"""
        zip_path = self.create_test_zip()
        
        # Mock file existence check
        def exists_side_effect(path):
            return path == zip_path
        mock_exists.side_effect = exists_side_effect
        mock_validate.return_value = None
        
        # Mock file operations
        mock_is_zipfile.return_value = True
        mock_zip_instance = MagicMock()
        mock_zip_context = MagicMock()
        mock_zip_context.namelist.return_value = ['test_file.txt']
        mock_zip_instance.__enter__.return_value = mock_zip_context
        mock_zipfile.return_value = mock_zip_instance
        
        # Mock file reading
        mock_file_obj = MagicMock()
        mock_file_obj.read.return_value = b'fake zip content'
        mock_open.return_value.__enter__.return_value = mock_file_obj
        
        # Mock database cursor
        mock_cursor = Mock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_cursor
        mock_with_db_cursor.return_value = mock_context
        mock_cursor.fetchone.return_value = [123]

        # Call with user_name
        result = add_file_to_db(zip_path, user_name="testuser")
        
        # Verify result
        assert isinstance(result, UploadResult)
        assert result.success is True
        assert result.error_type is None
        
        # Verify database call includes user_name
        call_args = mock_cursor.execute.call_args
        assert "INSERT INTO uploaded_files" in call_args[0][0]
        assert "user_name" in call_args[0][0]
        assert call_args[0][1][5] == "testuser"  # user_name parameter

    @patch('src.upload_file.with_db_cursor')
    def test_list_uploaded_files_by_user(self, mock_with_db_cursor):
        """Test listing files for a specific user"""
        from src.upload_file import list_uploaded_files_by_user
        
        # Mock database cursor
        mock_cursor = Mock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_cursor
        mock_with_db_cursor.return_value = mock_context
        
        # Mock database results
        mock_cursor.fetchall.return_value = [
            (1, 'file1.zip', 'uploads/file1.zip', 'uploaded', {}, 'testuser', '2026-01-04 10:00:00', '2026-01-04 10:00:00'),
            (2, 'file2.zip', 'uploads/file2.zip', 'uploaded', {}, 'testuser', '2026-01-04 11:00:00', '2026-01-04 11:00:00'),
        ]
        
        # Call function
        files = list_uploaded_files_by_user('testuser')
        
        # Verify results
        assert len(files) == 2
        assert files[0]['filename'] == 'file1.zip'
        assert files[0]['user_name'] == 'testuser'
        assert files[1]['filename'] == 'file2.zip'
        assert files[1]['user_name'] == 'testuser'
        
        # Verify SQL query includes WHERE clause
        call_args = mock_cursor.execute.call_args
        assert 'WHERE user_name = %s' in call_args[0][0]
        assert call_args[0][1] == ('testuser',)

    @patch('src.upload_file.with_db_cursor')
    def test_list_uploaded_files_includes_user_name(self, mock_with_db_cursor):
        """Test that list_uploaded_files returns user_name field"""
        from src.upload_file import list_uploaded_files
        
        # Mock database cursor
        mock_cursor = Mock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_cursor
        mock_with_db_cursor.return_value = mock_context
        
        # Mock database results with user_name
        mock_cursor.fetchall.return_value = [
            (1, 'file1.zip', 'uploads/file1.zip', 'uploaded', {}, 'user1', '2026-01-04 10:00:00', '2026-01-04 10:00:00'),
            (2, 'file2.zip', 'uploads/file2.zip', 'uploaded', {}, None, '2026-01-04 11:00:00', '2026-01-04 11:00:00'),
        ]
        
        # Call function
        files = list_uploaded_files()
        
        # Verify user_name is included in results
        assert len(files) == 2
        assert 'user_name' in files[0]
        assert files[0]['user_name'] == 'user1'
        assert 'user_name' in files[1]
        assert files[1]['user_name'] is None
        
        # Verify SQL query includes user_name column
        call_args = mock_cursor.execute.call_args
        assert 'user_name' in call_args[0][0]


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
