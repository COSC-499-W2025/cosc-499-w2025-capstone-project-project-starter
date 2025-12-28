# query_skills.py (run this in project root)
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from db.connect import get_db_connection
import json

def check_stored_skills():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("📊 Checking skills in database...")
    
    # Count total records
    cursor.execute("SELECT COUNT(*) FROM skills_analysis")
    total = cursor.fetchone()[0]
    print(f"Total skills analyses: {total}")
    
    cursor.execute("SELECT COUNT(*) FROM detailed_skills")
    total_detailed = cursor.fetchone()[0]
    print(f"Total detailed skill entries: {total_detailed}")
    
    # Show recent entries
    print("\n📋 Recent skills analyses:")
    cursor.execute("""
        SELECT project_id, source, analysis_type, created_at 
        FROM skills_analysis 
        ORDER BY created_at DESC 
        LIMIT 5
    """)
    
    for project_id, source, analysis_type, created_at in cursor.fetchall():
        print(f"  {project_id[:12]}... | {source} | {analysis_type} | {created_at}")
    
    # Show detected skills
    print("\n🎯 Skills detected in database:")
    cursor.execute("""
        SELECT skill_name, COUNT(*) as count, 
               STRING_AGG(DISTINCT source, ', ') as sources
        FROM detailed_skills 
        GROUP BY skill_name 
        ORDER BY count DESC
    """)
    
    for skill, count, sources in cursor.fetchall():
        print(f"  {skill}: {count} times (sources: {sources})")
    
    conn.close()

if __name__ == "__main__":
    check_stored_skills()