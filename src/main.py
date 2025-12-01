import sys
from validator.LLM_permission import display_privacy_notice, request_consent, run_ollama_analysis
from validator.zipvalidation import check_zip_file, unzip_file
from codeparser import parse_core


def main():
    # 1. Show privacy notice FIRST
    display_privacy_notice()

    # 2. Ask for consent
    consent = request_consent()
    if not consent:
        print("Consent not given. Exiting.")
        return

    # 3. Get ZIP file path (command line argument preferred)
    if len(sys.argv) > 1:
        zip_path = sys.argv[1]
    else:
        zip_path = input("\nEnter the path to your ZIP file: ").strip()

    # 4. Validate ZIP
    result = check_zip_file(zip_path)
    print(result)

    if "not a zip file" in result or "does not exist" in result:
        print("❌ Invalid zip file. Exiting.")
        return

    # 5. Unzip (unzip_file RETURN VALUE is ONLY the folder path)
    try:
        unzipped_dir = unzip_file(zip_path)
        print(f"✅ Extracted to: {unzipped_dir}")
        print(unzipped_dir + " unzipped successfully!\n")
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        return

    # 6. Local code parsing (your existing parser)
    parsed_folder = parse_core.parse_directory(unzipped_dir)
    parse_core.summarize_results(parsed_folder)

    # 7. Shortened Prompt (more room for code in context window)
    prompt = (
        "Provide a concise analysis of the code base below (max 2 sentences per point):\n"
        f"Path: {unzipped_dir}\n\n"
        "Focus on:\n"
        "1. Skill level of the author.\n"
        "2. Code design patterns.\n"
        "3. Data structures & algorithms used.\n"
        "4. Performance considerations.\n"
        "5. Evidence of optimization or reasoning maturity.\n"
        "Keep the response short and high-signal.\n"
    )

    print("\n🤖 Running analysis with Ollama...\n")
    response = run_ollama_analysis(prompt)

    print("\n================ FINAL ANALYSIS ================\n")
    print(response)
    print("\n================================================\n")


if __name__ == "__main__":
    main()
