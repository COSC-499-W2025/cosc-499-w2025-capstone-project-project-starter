import subprocess
import sys


def display_privacy_notice():
    print("\n================ DATA PRIVACY NOTICE ================\n")
    print("This program uses Ollama (Local LLM) to analyze your uploaded data.")
    print("Your files stay on your machine and are NOT uploaded to the internet.")
    print("However, AI processing will occur locally using Ollama.")
    print("\nBy continuing, you agree to allow your data to be processed by Ollama.\n")
    print("====================================================\n")


def request_consent():
    while True:
        response = input("Do you consent to use Ollama (Local LLM)? (yes/no): ").strip().lower()
        if response in ["yes", "y"]:
            print("✅ Consent granted. Using external LLM.")
            return True
        elif response in ["no", "n"]:
            print("🚫 Consent denied.")
            return False
        else:
            print("Please type 'yes' or 'no'.")


def run_ollama_analysis(prompt: str) -> str:
    """
    Runs analysis using Ollama CLI locally.
    Requires: ollama installed and running.
    Default model: mistral
    """

    try:
        result = subprocess.run(
            ["ollama", "run", "mistral"],
            input=prompt,
            text=True,
            capture_output=True,
            check=True
        )
        return result.stdout.strip()

    except subprocess.CalledProcessError as e:
        return f"❌ Ollama error: {e.stderr.strip()}"

    except FileNotFoundError:
        return "❌ Ollama not found. Please install it: https://ollama.com"


def process_data_with_permission(zip_file_path: str):
    """
    Wrapper function expected by main.py.
    Handles:
    - Privacy notice
    - Consent
    - Running Ollama analysis
    """

    display_privacy_notice()

    if not request_consent():
        print("Program stopped due to lack of consent.")
        sys.exit(0)

    prompt = f"""
    A user uploaded a zipped file named: {zip_file_path}.

    Please analyze the probable purpose, structure, and potential risks
    associated with contents of this archive.

    Provide a concise technical summary.
    """

    print("\n🤖 Running analysis with Ollama...\n")
    result = run_ollama_analysis(prompt)
    return result
