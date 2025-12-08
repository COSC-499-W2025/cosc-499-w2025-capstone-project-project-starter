import sys
from validator.LLM_permission import display_privacy_notice, request_consent, run_ollama_analysis
from validator.zipvalidation import check_zip_file, unzip_file
from validator.data_permission import display_data_privacy_notice, request_data_consent
from codeparser import parse_core, parse_metadata
from contributions.contribution_check import find_git_repos, get_commit_contributions
from exporter.pdf_exporter import collect_predictions, export
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
        unzipped_dir = unzip_file(zip_path)
        print(f".zip extracted to: {unzipped_dir}")
        print(unzipped_dir + " unzipped successfully!\n")
    except Exception as e:
        print(f"Extraction failed: {e}")
        return

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
    parsed_folder = parse_core.parse_directory(unzipped_dir)
    
    #ML model results
    ml_summary = parse_core.summarize_results(parsed_folder)
    
    predictions = collect_predictions(parsed_folder)


    # If LLM consent is not given, stop and export just the ML results to PDF
    if not llm_consent:
        export({"predictions": predictions}, filename="report.pdf")
        print("\nLLM analysis was skipped because consent was not given.")
        print("Above is the aggregated summary from the local pretrained model only.")
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

    print("\nRunning analysis with Ollama...\n")
    response = run_ollama_analysis(prompt)

    # Export both ML and LLM data in PDF
    export({"predictions": predictions}, response, filename="report.pdf")


    

if __name__ == "__main__":
    main()
