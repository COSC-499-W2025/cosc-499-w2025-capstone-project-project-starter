# src/main.py (COMPLETE FIXED VERSION)
import sys
import os

# Add current directory to path for relative imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Now use relative imports since we're in src/
from validator.LLM_permission import display_privacy_notice, request_consent, run_ollama_analysis
from validator.zipvalidation import check_zip_file, unzip_file
from validator.data_permission import display_data_privacy_notice, request_data_consent
from codeparser import parse_core, parse_metadata
from contributions.contribution_check import find_git_repos, get_commit_contributions
from exporter.pdf_exporter import collect_predictions, export
from db.skills_integration import store_ml_results_to_db, store_llm_results_to_db, get_project_summary
import json

def main():
    
    # Data privacy notice
    display_data_privacy_notice()
    # Request consent for data analysis
    data_consent = request_data_consent()
    if not data_consent:
        print("Data consent not given. Exiting.")
        return

    # LLM privacy notice
    display_privacy_notice()
    # Request consent for use of LLM
    llm_consent = request_consent()
    if len(sys.argv) > 1:
        zip_path = sys.argv[1]
    else:
        zip_path = input("\nEnter the path to ZIP file: ").strip()

    # Check if the passed filepath is a valid zip file and exists
    result = check_zip_file(zip_path)
    print(result)

    if "not a zip file" in result or "does not exist" in result:
        print("Invalid zip file. Exiting.")
        return

    try:
        unzipped_dir = unzip_file(zip_path, overwrite=True)
        print(f".zip extracted to: {unzipped_dir}")
        print(unzipped_dir + " unzipped successfully!\n")
    except Exception as e:
        print(f"Extraction failed: {e}")
        return

    zip_meta = parse_core.read_zip_metadata(zip_path)
    
    # DEBUG: Check what zip_meta is
    print(f"DEBUG: zip_meta type: {type(zip_meta)}")
    if hasattr(zip_meta, '__dict__'):
        print(f"DEBUG: zip_meta attributes: {[attr for attr in dir(zip_meta) if not attr.startswith('_')]}")
        if hasattr(zip_meta, 'filename'):
            print(f"DEBUG: zip_meta.filename: {zip_meta.filename}")
    
    # Extract simple metadata for database storage
    simple_meta = {}
    if hasattr(zip_meta, 'filename'):
        simple_meta = {"filename": zip_meta.filename}
    elif isinstance(zip_meta, dict):
        simple_meta = {"filename": zip_meta.get('filename', 'unknown')}
    else:
        simple_meta = {"filename": str(zip_meta)}
    
    print(f"DEBUG: Using metadata: {simple_meta}")

    # Check for Git repos and contribution data
    git_repos = [] 
    git_repos = find_git_repos(unzipped_dir)
    print(f"Found {len(git_repos)} Git repositories.\n")

    for repo_path in git_repos:
        print(f"\n📁 Repo found at: {repo_path}")
        contributions = get_commit_contributions(repo_path)
        print("👥 Commit Contributions:")
        for author, count in contributions.items():
            print(f"  - {author}: {count} commits")

    # Parse data
    parsed_folder = parse_core.parse_directory(unzipped_dir, zip_metadata=zip_meta)
    
    # ML model results
    ml_summary = parse_core.summarize_results(parsed_folder)
    predictions = collect_predictions(parsed_folder)
    
    # DEBUG: Check what ml_summary and predictions are
    print(f"\nDEBUG: ml_summary type: {type(ml_summary)}")
    print(f"DEBUG: predictions type: {type(predictions)}")
    
    # ✅ STORE ML RESULTS TO DATABASE
    print("\n" + "="*50)
    print("STORING ML RESULTS TO DATABASE...")
    print("="*50)
    
    project_id = store_ml_results_to_db(
        project_path=unzipped_dir,
        ml_summary=ml_summary,
        predictions=predictions,
        zip_metadata=simple_meta  # Use the simple metadata, not the raw zip_meta
    )
    
    if project_id:
        print(f"📊 ML analysis completed. Project ID: {project_id}")
    else:
        print("⚠️  ML analysis completed but not stored in database.")
        project_id = None

    # If LLM consent is not given, stop and export just the ML results to PDF
    if not llm_consent:
        export({"predictions": predictions}, filename="report.pdf")
        print("\n" + "="*50)
        print("LLM analysis was skipped because consent was not given.")
        print("Above is the aggregated summary from the local pretrained model only.")
        print("="*50)
        
        # Display database summary if we have a project_id
        if project_id:
            print(f"\n📈 Database Summary for Project {project_id}:")
            summary = get_project_summary(project_id)
            if summary:
                print(f"  - Total skills detected: {len(summary.get('all_detected_skills', []))}")
                print(f"  - Sources: {', '.join(summary.get('skills_by_source', {}).keys())}")
            else:
                print("  - No summary available (no data stored)")
        return
    
    # If LLM consent was provided, proceed with LLM analysis
    prompt = f"""
    Analyze the following extracted code directory:

    Path: {unzipped_dir}

    Focus on deep insights:
    - Skill level of the author
    - Code design patterns
    - Use of data structures & algorithms
    - Performance considerations
    - Evidence of optimization or reasoning maturity
    """

    print("\n" + "="*50)
    print("RUNNING LLM ANALYSIS WITH OLLAMA...")
    print("="*50)
    
    response = run_ollama_analysis(prompt)
    
    # ✅ STORE LLM RESULTS TO DATABASE
    print("\n" + "="*50)
    print("STORING LLM RESULTS TO DATABASE...")
    print("="*50)
    
    if project_id:
        # Use existing project_id if we have one
        llm_project_id = store_llm_results_to_db(
            project_path=unzipped_dir,
            llm_response=response,
            predictions=predictions,
            project_id=project_id,  # Use same project ID
            zip_metadata=simple_meta
        )
    else:
        # Create new project_id for LLM only
        llm_project_id = store_llm_results_to_db(
            project_path=unzipped_dir,
            llm_response=response,
            predictions=predictions,
            project_id=None,
            zip_metadata=simple_meta
        )
        project_id = llm_project_id  # Update project_id
    
    if llm_project_id:
        print(f"🧠 LLM analysis completed and stored. Project ID: {llm_project_id}")
    else:
        print("⚠️  LLM analysis completed but not stored in database.")

    # Export both ML and LLM data in PDF
    export({"predictions": predictions}, response, filename="report.pdf")
    
    # Display database summary
    if project_id:
        print("\n" + "="*50)
        print(f"📈 DATABASE SUMMARY FOR PROJECT {project_id}:")
        print("="*50)
        
        summary = get_project_summary(project_id)
        if summary:
            print(f"  - Total skills detected: {len(summary.get('all_detected_skills', []))}")
            print(f"  - Sources: {', '.join(summary.get('skills_by_source', {}).keys())}")
            
            if 'detailed_stats' in summary and summary['detailed_stats']:
                print(f"  - Detailed skills:")
                for stat in summary['detailed_stats'][:10]:  # Show top 10
                    print(f"    • {stat['skill']}: {stat['count']} mentions")
            
            if 'all_detected_skills' in summary and summary['all_detected_skills']:
                print(f"  - All detected skills: {', '.join(summary['all_detected_skills'][:10])}")
                if len(summary['all_detected_skills']) > 10:
                    print(f"    ... and {len(summary['all_detected_skills']) - 10} more")
        else:
            print("  - No data found in database for this project")
    
    print("\n" + "="*50)
    print("✅ PROCESSING COMPLETE")
    print("="*50)

if __name__ == "__main__":
    main()