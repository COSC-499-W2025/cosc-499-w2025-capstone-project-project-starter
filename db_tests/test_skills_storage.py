# test_skills_storage.py (updated with better error handling)
import sys
import os

# Add src to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

print(f"Python path includes: {src_dir}")

try:
    from db.skills_repository import SkillsRepository
    from skills_processor import SkillsProcessor
    print("✅ Successfully imported modules")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\nDebug info:")
    print(f"Current directory: {current_dir}")
    print(f"Looking in src directory: {src_dir}")
    
    # List files in src directory
    if os.path.exists(src_dir):
        print("\nFiles in src directory:")
        for f in os.listdir(src_dir):
            print(f"  {f}")
        
        print("\nFiles in src/db directory:")
        db_dir = os.path.join(src_dir, 'db')
        if os.path.exists(db_dir):
            for f in os.listdir(db_dir):
                print(f"  {f}")
    
    sys.exit(1)

def test_skills_storage():
    """Test the skills storage system"""
    print("\n" + "="*60)
    print("Testing skills storage system")
    print("="*60 + "\n")
    
    # Test project ID generation
    test_zip = "Archive.zip"
    project_id = SkillsProcessor.generate_project_id(test_zip)
    print(f"✅ Generated Project ID: {project_id}")
    
    # Test ML skills processing
    ml_summary = {
        "languages": ["Python", "JavaScript"],
        "frameworks": ["Flask", "React"],
        "tools": ["Docker", "Git"],
        "file_count": 10,
        "analysis": "Test analysis data"
    }
    
    print("Processing ML summary...")
    ml_skills = SkillsProcessor.process_ml_summary(ml_summary)
    print(f"✅ ML Skills processed. Has detected_skills: {'detected_skills' in ml_skills}")
    
    # Test LLM skills processing
    llm_response = "Python, Flask, React, Docker, Testing, SQL"
    
    print("\nProcessing LLM response...")
    llm_skills = SkillsProcessor.extract_skills_from_llm_response(llm_response)
    print(f"✅ LLM Skills extracted. Has detected_skills: {'detected_skills' in llm_skills}")
    
    if 'detected_skills' in llm_skills:
        detected_count = sum(1 for skill, detected in llm_skills.get("detected_skills", {}).items() if detected)
        print(f"✅ LLM detected {detected_count} skills")
    
    # Store test data
    try:
        print("\n" + "-"*60)
        print("Storing data in database...")
        
        # Store ML analysis
        SkillsRepository.store_skills_analysis(
            project_id=project_id,
            analysis_type="test_ml_analysis",
            skills_data=ml_skills,
            source="ml"
        )
        print("✅ Stored ML analysis")
        
        # Store LLM analysis
        SkillsRepository.store_skills_analysis(
            project_id=project_id,
            analysis_type="test_llm_analysis",
            skills_data=llm_skills,
            source="llm"
        )
        print("✅ Stored LLM analysis")
        
        # Try to store individual skills
        try:
            if 'detected_skills' in ml_skills:
                detected_skills = SkillsProcessor.get_detected_skills_list(ml_skills)
                if detected_skills:
                    SkillsRepository.store_detailed_skills(
                        project_id=project_id,
                        skills_list=detected_skills,
                        source="ml",
                        confidence=0.8
                    )
                    print(f"✅ Stored {len(detected_skills)} ML skills")
        except Exception as e:
            print(f"⚠️  Could not store detailed ML skills: {e}")
        
        try:
            if 'detected_skills' in llm_skills:
                llm_detected_skills = SkillsProcessor.get_detected_skills_list(llm_skills)
                if llm_detected_skills:
                    SkillsRepository.store_detailed_skills(
                        project_id=project_id,
                        skills_list=llm_detected_skills,
                        source="llm",
                        confidence=0.9,
                        context="Test LLM analysis"
                    )
                    print(f"✅ Stored {len(llm_detected_skills)} LLM skills")
        except Exception as e:
            print(f"⚠️  Could not store detailed LLM skills: {e}")
        
        print(f"\n✅ All test data stored for project: {project_id}")
        
        # Retrieve and display summary
        print("\n" + "-"*60)
        print("Retrieving project summary from database...")
        try:
            summary = SkillsRepository.get_project_skills_summary(project_id)
            
            print(f"\n📊 PROJECT SUMMARY")
            print(f"Project ID: {summary['project_id']}")
            print(f"Total Analyses: {summary['total_analyses']}")
            
            if summary['all_detected_skills']:
                print(f"\nDetected Skills ({len(summary['all_detected_skills'])}):")
                for skill in summary['all_detected_skills']:
                    print(f"  - {skill}")
            else:
                print("\nNo skills detected in test data.")
            
            if summary['detailed_stats']:
                print(f"\n📈 Detailed Statistics:")
                for stat in summary['detailed_stats']:
                    print(f"  {stat['skill']}: {stat['count']} detection(s) from {stat['sources']}")
        
        except Exception as e:
            print(f"⚠️  Could not retrieve summary: {e}")
        
        print("\n🎉 Skills storage test completed!")
        
    except Exception as e:
        print(f"\n❌ Error in test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_skills_storage()