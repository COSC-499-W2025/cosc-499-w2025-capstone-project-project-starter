"""
Quick script to clean error summaries from the database.
Run this to remove any "Error: No user is currently logged in." messages
that were stored in the project_rankings table.
"""

from src.analysis.ranking_storage import clean_error_summaries

if __name__ == "__main__":
    print("="*80)
    print("Cleaning Error Summaries from Database")
    print("="*80)
    print()
    
    if clean_error_summaries():
        print()
        print("✓ Cleanup completed successfully!")
        print()
        print("Next steps:")
        print("1. Run the application: python src/main.py")
        print("2. Use option 6 to rank and summarize projects")
        print("3. The error should no longer appear")
    else:
        print()
        print("✗ Cleanup failed. Please check database connection.")
    
    print("="*80)
