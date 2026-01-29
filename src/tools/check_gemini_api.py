#!/usr/bin/env python3
"""
Standalone Gemini API test — no package dependencies.
Run from project root:  python src/tools/check_gemini_api.py
"""

import os
import sys

# Ensure we can load .env from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    sys.exit("ERROR: GEMINI_API_KEY not set in .env")

try:
    import google.genai as genai  # new SDK
except ImportError:
    import google.generativeai as genai  # legacy fallback

# Configure client
if hasattr(genai, "Client"):
    client = genai.Client(api_key=API_KEY)
else:
    genai.configure(api_key=API_KEY)
    client = genai


def main() -> None:
    prompt = "Reply with exactly: Hello from Gemini."
    print("Sending prompt to Gemini...")

    # New SDK path
    if hasattr(client, "models"):
        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt],
        )
        text = getattr(resp, "text", None) or getattr(resp, "output_text", "")
    else:
        # Legacy SDK path
        model = client.GenerativeModel("gemini-2.0-flash")
        resp = model.generate_content(prompt)
        text = resp.text

    print("\nResponse:")
    print(text)


if __name__ == "__main__":
    main()
