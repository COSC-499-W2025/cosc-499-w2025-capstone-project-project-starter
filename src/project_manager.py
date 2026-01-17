"""
Project Manager Module

Manages project listing and retrieval operations.
Supports both alphabetical and chronological ordering of projects.
"""
import json
from config.db_config import with_db_cursor


def list_projects(user_name):
    """
    List all stored projects (ZIP files) for a specific user in alphabetical order.
    Data Isolation: Only returns projects belonging to the specified user.
    
    Args:
        user_name (str): Username to filter projects by
    
    Returns:
        list: List of project dictionaries with id, filename, created_at, and file_count.
    """
    try:
        with with_db_cursor() as cursor:
            # Data Isolation: Filter projects by user_name to ensure users only see their own data
            cursor.execute("""
                SELECT id, filename, status, metadata, created_at
                FROM uploaded_files
                WHERE user_name = %s
                ORDER BY filename ASC
            """, (user_name,))
            projects = cursor.fetchall()
        
        # if there are no projects, return an empty list
        if not projects:
            print("No projects found in database.")
            return []
        
        print("-"*80)
        print("Stored Projects (Alphabetical Order)")  
        print("-"*80)
        
        project_list = []
        
        for project in projects:
            project_id, filename, status, metadata, created_at = project
            
            # Count files in metadata if available
            file_count = 0
            if metadata:
                try:
                    metadata_dict = json.loads(metadata) if isinstance(metadata, str) else metadata
                    if 'files' in metadata_dict and metadata_dict['files']:
                        # Count only actual files (not directories)
                        actual_files = [f for f in metadata_dict['files'] if not f.endswith('/')]
                        file_count = len(actual_files)
                except (json.JSONDecodeError, TypeError):
                    pass
            
            project_list.append({
                'id': project_id,
                'filename': filename,
                'created_at': created_at,
                'file_count': file_count
            })
            
            # Display project info
            created_date = created_at.strftime("%Y-%m-%d") if created_at else "Unknown"
            print(f"\n{len(project_list)}. {filename}")
            print(f"   ID: {project_id}, Created: {created_date}, Files: {file_count}")
        
        print("\n" + "-"*80)
        print(f"Total projects: {len(project_list)}")
        print("-"*80)
        
        return project_list
        
    except ConnectionError:
        print("Could not connect to database.")
        return []
    except Exception as e:
        print(f"Error retrieving projects: {e}")
        return []


def list_project_files(project_id, user_name):
    """
    List individual files within a specific project.
    Data Isolation: Verifies project belongs to the user before returning files.
    
    Args:
        project_id (int): The ID of the project to list files for
        user_name (str): Username to verify project ownership
        
    Returns:
        list: List of file paths/names in the project
    """
    try:
        with with_db_cursor() as cursor:
            # Data Isolation: Verify project belongs to the specified user
            cursor.execute("""
                SELECT metadata
                FROM uploaded_files
                WHERE id = %s AND user_name = %s
            """, (project_id, user_name))
            
            result = cursor.fetchone()
            
            if not result:
                print(f"Project with ID {project_id} not found.")
                return []
            
            metadata = result[0]
            
            if not metadata:
                print("No file metadata available for this project.")
                return []
            
            try:
                metadata_dict = json.loads(metadata) if isinstance(metadata, str) else metadata
                if 'files' in metadata_dict and metadata_dict['files']:
                    # Filter out directories and return actual files
                    actual_files = [f for f in metadata_dict['files'] if not f.endswith('/')]
                    return actual_files
                else:
                    print("No files found in project metadata.")
                    return []
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Error parsing project metadata: {e}")
                return []
                
    except ConnectionError:
        print("Could not connect to database.")
        return []
    except Exception as e:
        print(f"Error retrieving project files: {e}")
        return []

# this function will get a project by its id
def get_project_by_id(project_id, user_name):
    """
    Get a project by its ID for a specific user.
    Data Isolation: Only returns project if it belongs to the specified user.
    
    Args:
        project_id (int): The ID of the project to retrieve
        user_name (str): Username to verify project ownership
        
    Returns:
        dict: Project information or None if not found or access denied
    """
    try:
        with with_db_cursor() as cursor:
            # Data Isolation: Verify project belongs to the specified user
            cursor.execute("""
                SELECT id, filename, filepath, status, metadata, created_at
                FROM uploaded_files
                WHERE id = %s AND user_name = %s
            """, (project_id, user_name))
            
            project = cursor.fetchone()
        
        if not project:
            print(f"Project with ID {project_id} not found.")
            return None
        
        project_id, filename, filepath, status, metadata, created_at = project
        
        # return the project information
        return {
            'id': project_id,
            'filename': filename,
            'filepath': filepath,
            'status': status,
            'metadata': metadata,
            'created_at': created_at
        }
        
    except ConnectionError:
        print("Could not connect to database.")
        return None
    except Exception as e:
        print(f"Error retrieving project: {e}")
        return None

# this function will get the total number of projects in the database
def get_project_count(user_name):
    """
    Get the total number of projects for a specific user.
    Data Isolation: Only counts projects belonging to the specified user.
    
    Args:
        user_name (str): Username to filter projects by
        
    Returns:
        int: Number of projects owned by the user
    """
    try:
        with with_db_cursor() as cursor:
            # Data Isolation: Count only projects belonging to the specified user
            cursor.execute("""
                SELECT COUNT(*) 
                FROM uploaded_files 
                WHERE user_name = %s
            """, (user_name,))
            count = cursor.fetchone()[0]
        return count
        
    except ConnectionError:
        print("Could not connect to database.")
        return 0
    except Exception as e:
        print(f"Error getting project count: {e}")
        return 0


def list_projects_chronologically(user_name):
    """
    List all stored projects (ZIP files) for a specific user in chronological order by creation date.
    Data Isolation: Only returns projects belonging to the specified user.
    Requirement: Produce a chronological list of projects.
    
    Args:
        user_name (str): Username to filter projects by
    
    Returns:
        list: List of project dictionaries with id, filename, created_at, and file_count,
              ordered by created_at ascending (oldest first).
    """
    try:
        with with_db_cursor() as cursor:
            # Data Isolation: Filter projects by user_name to ensure users only see their own data
            cursor.execute("""
                SELECT id, filename, status, metadata, created_at
                FROM uploaded_files
                WHERE user_name = %s
                ORDER BY created_at ASC
            """, (user_name,))
            projects = cursor.fetchall()
        
        # if there are no projects, return an empty list
        if not projects:
            print("No projects found in database.")
            return []
        
        print("-"*80)
        print("Stored Projects (Chronological Order - Oldest First)")  
        print("-"*80)
        
        project_list = []
        
        for project in projects:
            project_id, filename, status, metadata, created_at = project
            
            # Count files in metadata if available
            file_count = 0
            if metadata:
                try:
                    metadata_dict = json.loads(metadata) if isinstance(metadata, str) else metadata
                    if 'files' in metadata_dict and metadata_dict['files']:
                        # Count only actual files (not directories)
                        actual_files = [f for f in metadata_dict['files'] if not f.endswith('/')]
                        file_count = len(actual_files)
                except (json.JSONDecodeError, TypeError):
                    pass
            
            project_list.append({
                'id': project_id,
                'filename': filename,
                'created_at': created_at,
                'file_count': file_count
            })
            
            # Display project info
            created_date = created_at.strftime("%Y-%m-%d") if created_at else "Unknown"
            print(f"\n{len(project_list)}. {filename}")
            print(f"   ID: {project_id}, Created: {created_date}, Files: {file_count}")
        
        print("\n" + "-"*80)
        print(f"Total projects: {len(project_list)}")
        print("-"*80)
        
        return project_list
        
    except ConnectionError:
        print("Could not connect to database.")
        return []
    except Exception as e:
        print(f"Error retrieving projects chronologically: {e}")
        return []
