import sys
from validator.LLM_permission import display_privacy_notice, request_consent, run_ollama_analysis
from validator.zipvalidation import check_zip_file, unzip_file
from codeparser import parse_core
from exporter.pdf_exporter import collect_predictions, export
import json

def main():
    # LLM privacy notice
    display_privacy_notice()

    # Request consent for use of LLM
    consent = request_consent()

    # Accepts zip file at command line
    if len(sys.argv) > 1:
        zip_path = sys.argv[1]
    else:
        zip_path = input("\nEnter the path to ZIP file: ").strip()

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
    parsed_folder = parse_core.parse_directory(unzipped_dir)
    all_predictions = collect_predictions(parsed_folder)

    # If LLM consent is not given, stop and export just the ML results to PDF
    if not consent:
        # Export using just the ML data
        export({"predictions": all_predictions}, filename="report.pdf")

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
    export({"predictions": all_predictions}, response, filename="report.pdf")


    

if __name__ == "__main__":
    main()
