#to run: python .\db_tests\check_full_skills.py

import sys
import os

# Get the project root directory
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir) if "db_tests" in current_dir else current_dir

# Add src to path
src_dir = os.path.join(project_root, 'src')
sys.path.insert(0, src_dir)

print(f"Project root: {project_root}")
print(f"Looking for db in: {src_dir}")

try:
    from db.connect import get_db_connection
    print("✅ Import successful")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Rest of the function stays the same...
def check_all_skills():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("📊 COMPLETE SKILLS DATABASE CHECK")
    print("="*50)
    
    # Get all analyses
    cursor.execute("""
        SELECT id, project_id, source, analysis_type, 
               created_at, LENGTH(skills_data::text) as data_size
        FROM skills_analysis 
        ORDER BY created_at DESC
    """)
    
    analyses = cursor.fetchall()
    print(f"\nTotal analyses: {len(analyses)}")
    
    for i, (id, project_id, source, analysis_type, created_at, data_size) in enumerate(analyses, 1):
        print(f"\n{i}. Analysis ID: {id}")
        print(f"   Project: {project_id[:12]}...")
        print(f"   Source: {source}")
        print(f"   Type: {analysis_type}")
        print(f"   Created: {created_at}")
        print(f"   Data size: {data_size} chars")
        
        # Get skills data for this analysis
        cursor.execute("SELECT skills_data FROM skills_analysis WHERE id = %s", (id,))
        skills_json = cursor.fetchone()[0]
        
        # Try to parse and show key info
        import json
        try:
            data = json.loads(skills_json)
            if 'detected_skills' in data:
                detected = [skill for skill, found in data['detected_skills'].items() if found]
                print(f"   Detected skills: {len(detected)}")
                if detected:
                    print(f"   Skills: {', '.join(detected[:5])}{'...' if len(detected) > 5 else ''}")
        except:
            pass
    
    # Get all detailed skills
    print(f"\n{'='*50}")
    print("DETAILED SKILLS BREAKDOWN:")
    cursor.execute("""
        SELECT skill_name, COUNT(*) as count, 
               STRING_AGG(DISTINCT project_id, ', ') as projects,
               STRING_AGG(DISTINCT source, ', ') as sources
        FROM detailed_skills 
        GROUP BY skill_name 
        ORDER BY count DESC, skill_name
    """)
    
    skills = cursor.fetchall()
    print(f"\nTotal unique skills: {len(skills)}")
    
    for skill, count, projects, sources in skills:
        print(f"\n  {skill}:")
        print(f"    Count: {count}")
        print(f"    Sources: {sources}")
        print(f"    Projects: {projects[:50]}...")
    
    conn.close()

if __name__ == "__main__":
    check_all_skills()