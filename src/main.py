import sys
from validator import zipvalidation
from codeparser import parse_core

def main():
    # get the file as a command-line argument
    if len(sys.argv) != 2:
        print("Error: expected a single file argument")
        return
    
    # ask for user consent
    consent = input("Do you consent to your data being analyzed? (y/n): ").strip().lower()
    if consent != 'y':
        print("Consent not given. Exiting.")
        return

    # validate zip
    file = sys.argv[1]
    result = zipvalidation.check_zip_file(file)
    print("\n"+ result + "\n")

    # now unzip the zip file
    unzipped = zipvalidation.unzip_file(file)
    unzipped = unzipped.split("Extracted to: ")[1]
    print(unzipped + " unzipped successfully!\n")

    # parse the unzipped folder and summarize results
    parsed_folder = parse_core.parse_directory(unzipped)
    parse_core.summarize_results(parsed_folder)

    print("\nMain working correctly.\n")




if __name__ == "__main__":
    main()
