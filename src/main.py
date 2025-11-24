from validator.LLM_permission import display_privacy_notice, request_consent, run_ollama_analysis
from validator.zipvalidation import check_zip_file, unzip_file
from codeparser import parse_core


def main():
    # 1. Show privacy notice FIRST
    display_privacy_notice()

    # 2. Ask for consent
    consent = request_consent()
    if not consent:
        print("Program terminated. No data was processed.")
        return

    # 3. Now ask for ZIP file path
    zip_path = input("\nEnter the path to your ZIP file: ").strip()

    # 4. Validate ZIP
    result = check_zip_file(zip_path)
    print(result)

    if "not a zip file" in result or "does not exist" in result:
        print("❌ Invalid zip file. Exiting.")
        return

    # 5. Unzip
    try:
        extraction_message = unzip_file(zip_path)
        print(extraction_message)

        unzipped_dir = extraction_message.split("Extracted to: ")[1]
        print(unzipped_dir + " unzipped successfully!\n")

    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        return

    # 6. Local code parsing
    parsed_folder = parse_core.parse_directory(unzipped_dir)
    parse_core.summarize_results(parsed_folder)

    # 7. Prepare prompt for Ollama
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

    print("\n🤖 Running analysis with Ollama...\n")
    response = run_ollama_analysis(prompt)

    print("\n================ FINAL ANALYSIS ================\n")
    print(response)
    print("\n================================================\n")


if __name__ == "__main__":
    main()
