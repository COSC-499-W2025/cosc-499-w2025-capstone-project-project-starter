"""
LLM_permission.py

This module:
  • Requests user consent before sending data to an external service (e.g., LLM).
  • Clearly provides data privacy implications (requirement 4).
  • Offers a local alternative analysis (/src/ml/) if consent is denied (requirement 5).
"""

import importlib


def request_external_service_permission(service_name: str, data_type: str) -> bool:
    """
    Ask the user for consent before using an external service and
    display clear data privacy implications.

    Args:
        service_name (str): Name of the external service (e.g., "OpenAI API").
        data_type (str): Type of data that will be sent (e.g., "source code", "user input").

    Returns:
        bool: True if the user consents, False otherwise.
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

    while True:
        consent = input(f"\nDo you consent to use {service_name} for processing your {data_type}? (yes/no): ").strip().lower()
        if consent in ["yes", "no"]:
            return consent == "yes"
        print("❌ Invalid input. Please type 'yes' or 'no'.")


def analyze_with_external_service(data: str):
    """
    Stub for sending data to an external service such as an LLM.
    In actual implementation, this would handle the API request and return the response.
    """
    print("📤 Sending data to external service...")
    # Placeholder for API logic
    return f"[External Analysis Result for data: {data[:30]}...]"


def analyze_locally(data: str):
    """
    Alternative local analysis (Requirement 5).
    Uses models or logic in /src/ml/ if the user declines external service.
    """
    try:
        # Dynamically load your local ML analysis module (placeholder)
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
