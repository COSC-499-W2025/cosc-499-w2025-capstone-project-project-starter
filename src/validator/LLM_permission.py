"""
LLM_permission.py

Handles:
  • Requesting user consent before sending data to external services (LLMs, APIs, etc.)
  • Displaying data privacy implications clearly
  • Falling back to local analysis (/src/ml/) if user declines

Refinements:
  • Added retry limit + delay to prevent infinite loops
  • Moved consent notice text into a helper for clarity and reuse
"""

import importlib
import time


def _display_data_privacy_notice(service_name: str, data_type: str) -> None:
    """
    Display a clear data privacy notice to the user before requesting consent.

    Args:
        service_name (str): Name of the external service (e.g., "OpenAI API").
        data_type (str): Type of data being processed (e.g., "source code").
    """
    print("\n⚠️  DATA PRIVACY NOTICE")
    print("=" * 70)
    print(f"You are about to send your {data_type} to an external service: {service_name}")
    print("\nBy consenting, you acknowledge that:")
    print("  • The data may be processed or stored by external servers outside your local machine.")
    print("  • The external service may log or retain portions of your data for debugging or improvement.")
    print("  • You should avoid including personal, confidential, or proprietary information.")
    print("  • This process is optional — if you decline, a local analysis will be performed instead.")
    print("=" * 70)


def request_external_service_permission(service_name: str, data_type: str, max_retries: int = 3, delay: float = 1.0) -> bool:
    """
    Ask the user for consent before using an external service and display privacy implications.

    Args:
        service_name (str): Name of the external service (e.g., "OpenAI API").
        data_type (str): Type of data that will be sent (e.g., "source code").
        max_retries (int): Maximum number of invalid attempts allowed before auto-deny.
        delay (float): Delay (in seconds) after invalid input before retry prompt.

    Returns:
        bool: True if user consents, False otherwise.
    """
    _display_data_privacy_notice(service_name, data_type)

    attempts = 0
    while attempts < max_retries:
        consent = input(f"\nDo you consent to use {service_name} for processing your {data_type}? (yes/no): ").strip().lower()
        if consent in ["yes", "no"]:
            return consent == "yes"
        print("❌ Invalid input. Please type 'yes' or 'no'.")
        attempts += 1
        time.sleep(delay)

    print("⚠️  Maximum invalid attempts reached. Defaulting to 'no'.")
    return False


def analyze_with_external_service(data: str):
    """
    Stub for sending data to an external service such as an LLM.
    Replace this with actual API logic when external service integration is ready.
    """
    print("📤 Sending data to external service...")
    return f"[External Analysis Result for data: {data[:30]}...]"


def analyze_locally(data: str):
    """
    Local fallback analysis (Requirement 5).
    Tries to use /src/ml/universal/local_analysis.py if available.
    """
    try:
        local_module = importlib.import_module("src.ml.universal.local_analysis")
        print("🧠 Running local analysis using /src/ml/universal/local_analysis.py...")
        return local_module.run_local_analysis(data)
    except ModuleNotFoundError:
        print("⚙️ Local ML module not found. Using fallback local heuristic analysis.")
        return f"[Local Analysis Result for data: {data[:30]}...]"


def process_data_with_permission(service_name: str, data_type: str, data: str):
    """
    Orchestrates the workflow:
    - Requests user permission
    - Runs external or local analysis accordingly
    """
    has_consent = request_external_service_permission(service_name, data_type)

    if has_consent:
        print("✅ User consented to external processing.")
        return analyze_with_external_service(data)
    else:
        print("🔒 User declined external service — switching to local analysis.")
        return analyze_locally(data)


if __name__ == "__main__":
    # Example standalone run
    example_data = "Sample source code snippet for testing"
    result = process_data_with_permission("OpenAI API", "source code", example_data)
    print("\nResult:\n", result)
