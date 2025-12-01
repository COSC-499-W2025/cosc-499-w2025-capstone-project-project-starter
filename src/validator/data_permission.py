import subprocess
import importlib

# ------------------ PRIVACY NOTICE ------------------

def display_data_privacy_notice():
    print("\n⚠️  DATA PRIVACY NOTICE")
    print("=" * 70)
    print("You are about to upload your data for analysis.")
    print("\nBy consenting, you acknowledge that:")
    print("  • Your extracted source code will be analyzed by the system.")
    print("  • No cloud service is used, but the model still processes raw content.")
    print("=" * 70)

# ------------------ CONSENT HANDLING ------------------

def request_data_consent():
    """
    Ask user for consent to analyze data.
    Accepts: 'y', 'yes', 'n', 'no' (case-insensitive)
    """
    while True:
        resp = input("Do you consent to your data being analyzed? (yes/no): ").strip().lower()
        if resp in ("y", "yes"):
            return True
        elif resp in ("n", "no"):
            return False
        else:
            print("❌ Invalid input. Please enter 'yes' or 'no'.")