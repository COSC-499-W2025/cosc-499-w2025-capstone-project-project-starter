# test_skills_storage_simple.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from db.connect import get_db_connection

def test_connection():
    print("Testing database connection...")
    try:
        conn = get_db_connection()
        print("✅ Connected successfully!")
        
        cursor = conn.cursor()
        
        # Check if skills tables exist
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_name IN ('skills_analysis', 'detailed_skills')
        """)
        
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Found tables: {tables}")
        
        if 'skills_analysis' in tables:
            cursor.execute("SELECT COUNT(*) FROM skills_analysis")
            count = cursor.fetchone()[0]
            print(f"skills_analysis has {count} records")
            
            if count > 0:
                cursor.execute("SELECT project_id, source FROM skills_analysis LIMIT 3")
                print("Sample records:")
                for project_id, source in cursor.fetchall():
                    print(f"  Project: {project_id[:10]}..., Source: {source}")
        
        if 'detailed_skills' in tables:
            cursor.execute("SELECT COUNT(*) FROM detailed_skills")
            count = cursor.fetchone()[0]
            print(f"detailed_skills has {count} records")
            
            if count > 0:
                cursor.execute("SELECT skill_name, COUNT(*) FROM detailed_skills GROUP BY skill_name")
                print("Skills found:")
                for skill, skill_count in cursor.fetchall():
                    print(f"  {skill}: {skill_count}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_connection()