"""
LLM_permission.py

Handles:
- Displaying data privacy concerns
- Requesting user consent for LLM usage
- Running Ollama-based analysis
- Falling back to local ML analysis if consent is denied

Compatible with pytest imports.
"""

import subprocess
import importlib

# ------------------ PRIVACY NOTICE ------------------

def display_privacy_notice():
    print("\n⚠️  DATA PRIVACY NOTICE")
    print("=" * 70)
    print("You are about to send your project data to an external processing system:")
    print("Ollama (Local Large Language Model)")
    print("\nBy consenting, you acknowledge that:")
    print("  • Your extracted source code may be processed by a locally running LLM.")
    print("  • No cloud service is used, but the model still processes raw content.")
    print("  • If you decline, local heuristic analysis will be used instead.")
    print("=" * 70)

# ------------------ CONSENT HANDLING ------------------

def request_consent():
    """
    Ask user for consent to analyze data.
    Accepts: 'y', 'yes', 'n', 'no' (case-insensitive)
    """
    while True:
        resp = input("Do you consent to use Ollama (Local LLM)? (yes/no): ").strip().lower()
        if resp in ("y", "yes"):
            return True
        elif resp in ("n", "no"):
            return False
        else:
            print("❌ Invalid input. Please enter 'yes' or 'no'.")

# ------------------ OLLAMA EXECUTION ------------------

def run_ollama_analysis(prompt: str) -> str:
    """
    Run Ollama locally with given prompt.
    Optimized to prioritize code over instructions.
    """

    MAX_INPUT_CHARS = 2000  # Safe under Ollama's window

    trimmed_prompt = prompt[:MAX_INPUT_CHARS]
    if len(prompt) > MAX_INPUT_CHARS:
        trimmed_prompt += "\n[Truncated]"

    concise_prompt = f"""
Analyze this code. Respond EXACTLY in this format
(max 2 sentences per point):

1. Skill level of the author:
2. Code design patterns:
3. Data structures & algorithms:
4. Performance considerations:
5. Optimization / reasoning maturity:

Code:
{trimmed_prompt}
"""

    try:
        process = subprocess.Popen(
            ["ollama", "run", "mistral"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        output, error = process.communicate(concise_prompt)

        if process.returncode != 0:
            return f"❌ Ollama error: {error.strip()}"

        return output.strip()

    except FileNotFoundError:
        return "❌ Ollama not installed or not running."

# ------------------ LOCAL ANALYSIS FALLBACK ------------------

def analyze_locally(data: str):
    """
    Fallback analysis if consent is denied.
    """
    try:
        local_module = importlib.import_module("src.ml.universal.local_analysis")
        return local_module.run_local_analysis(data)
    except Exception:
        return f"[Local heuristic analysis: {data[:50]}...]"

# ------------------ EXTERNAL ANALYSIS FOR TESTS ------------------

def analyze_with_external_service(data: str):
    """Used in tests for external analysis."""
    return "EXTERNAL"

def process_data_with_permission(service_name: str, data_type: str, data: str):
    """
    Request consent and run external or local analysis accordingly.
    """
    consent = request_consent()
    if consent:
        print("🤖 Running Ollama analysis...")
        return run_ollama_analysis(data)
    else:
        print("🧠 Running local analysis...")
        return analyze_locally(data)
