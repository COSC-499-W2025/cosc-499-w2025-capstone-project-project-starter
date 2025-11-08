"""Display functions for CLI output."""


def display_success(result):
    """Display success information to user."""
    print("\n" + "="*70)
    print("SUCCESS")
    print("="*70)
    
    if hasattr(result, 'message') and result.message:
        print(f"Message: {result.message}")
    
    if hasattr(result, 'data') and result.data:
        data = result.data
        
        # Display file information
        if 'filename' in data:
            print(f"File: {data['filename']}")
        
        if 'file_id' in data:
            print(f"File ID: {data['file_id']}")
        
        # Display file list
        if 'files' in data and data['files']:
            files = data['files']
            file_count = len(files)
            
            print(f"\n{file_count} files:")
            
            # Show first 5 files
            for i, file in enumerate(files[:5], 1):
                print(f"  {i}. {file}")
            
            # If more than 5 files, indicate there are more
            if file_count > 5:
                print(f"  ... and {file_count - 5} more files")
        
        # Display file count if provided
        if 'file_count' in data and 'files' not in data:
            print(f"Total files: {data['file_count']}")
    
    print("="*70 + "\n")


def display_error(result):
    """Format and display error information"""
    print("\n" + "="*60)
    print("ERROR")
    print("="*60)
    print(f"Error Type: {result.error_type}")
    print(f"Message: {result.message}")
    if result.data:
        print("\nDetails:")
        for key, value in result.data.items():
            print(f"  • {key}: {value}")
    print("="*60 + "\n")

