import sys
from validator import zipvalidation
from codeparser import parse_core
from exporter.pdf_exporter import export, collect_predictions


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
    all_predictions = collect_predictions(parsed_folder)

    # Then export as a PDF for user visualization
    export({"predictions": all_predictions}, filename="report.pdf")


    

if __name__ == "__main__":
    main()
