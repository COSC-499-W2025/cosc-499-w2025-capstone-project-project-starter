import sys
from validator import zipvalidation

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
    result = zipvalidation.check_zip_file(file)
    unzipped = zipvalidation.unzip_file(file)
    print("\n"+ result + "\n")
    print("\n" + unzipped + "\n")
    print("\nMain working correctly.\n")




if __name__ == "__main__":
    main()
