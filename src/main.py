import sys
from validator import zipvalidation
from codeparser import parse_core
from exporter.pdf_exporter import export


def main():
    # Get the file as a command-line argument
    if len(sys.argv) != 2:
        print("Error: expected a single file argument")
        return
    
    # Ask for user consent
    consent = input("Do you consent to your data being analyzed? (y/n): ").strip().lower()
    if consent != 'y':
        print("Consent not given. Exiting.")
        return

    # Validate zip
    file = sys.argv[1]
    result = zipvalidation.check_zip_file(file)
    print("\n" + result + "\n")

    # Unzip the zip file
    unzipped = zipvalidation.unzip_file(file)
    unzipped = unzipped.split("Extracted to: ")[1]
    print(unzipped + " unzipped successfully!\n")

    # Parse the unzipped folder and summarize results
    parsed_folder = parse_core.parse_directory(unzipped)
    parse_core.summarize_results(parsed_folder)

    # Collect predictions for PDF
    all_predictions = []

    # If parsed_folder is a list of dicts
    if isinstance(parsed_folder, list):
        for file_summary in parsed_folder:
            file_name = file_summary.get("file", "Unknown file")
            skills = file_summary.get("skills", [])
            if not isinstance(skills, list):
                continue
            for item in skills:
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    skill, prob = item
                    all_predictions.append([f"{file_name}: {skill}", prob])
                else:
                    print(f"⚠️ Skipping invalid skill entry in {file_name}: {item}")
    else:
        print("⚠️ Unexpected parsed_folder structure. PDF will be empty.")

    # Export to PDF
    if all_predictions:
        export({"predictions": all_predictions}, filename="predictions.pdf")
        print("\n✅ PDF generated successfully: predictions.pdf")
    else:
        print("\n⚠️ No valid skills to export.")

if __name__ == "__main__":
    main()
