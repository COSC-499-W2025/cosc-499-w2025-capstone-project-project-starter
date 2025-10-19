import sys
import os
import zipfile

def check_zip_file(file):

    # first ensure file exists
    if not os.path.exists(file):
        return f"Error: file '{file}' does not exist"

    # then check if its a zip
    if zipfile.is_zipfile(file):
        return f"{file} is a zip file"
    else:
        return f"{file} is not a zip file"


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

    file = sys.argv[1]
    result = check_zip_file(file)
    print(result)
    print("\nMain working correctly.\n")




if __name__ == "__main__":
    main()
