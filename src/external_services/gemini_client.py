import os
from typing import Iterable, Optional

from dotenv import load_dotenv

try:
    # New SDK (recommended)
    import google.genai as genai  # type: ignore
except ImportError:  # pragma: no cover
    # Fallback to legacy package if the user keeps it around
    import google.generativeai as genai  # type: ignore


load_dotenv()


_API_KEY = os.getenv("GEMINI_API_KEY")


if not _API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not set. "
        "Add it to your .env (see .env.example)."
    )


def _get_client():
    """
    Return a configured Gemini client.

    - With the new `google-genai` SDK this creates a Client instance.
    - With legacy `google-generativeai`, this simply configures the global client.
    """
    # New SDK – preferred
    if hasattr(genai, "Client"):
        return genai.Client(api_key=_API_KEY)

    # Legacy SDK – fallback
    if hasattr(genai, "configure"):
        genai.configure(api_key=_API_KEY)
        return genai

    raise RuntimeError("Unknown Gemini client library installed.")


def generate_text(
    prompt: str,
    *,
    model_name: str = "gemini-2.0-flash",
    system_instruction: Optional[str] = None,
    temperature: float = 0.2,
) -> str:
    """
    Simple helper to get a single-shot text response from Gemini.

    This keeps the rest of your codebase decoupled from the concrete SDK.
    """
    client = _get_client()

    # New SDK (google-genai)
    if hasattr(client, "models"):
        model = client.models.generate_content
        parts: Iterable[str] = [prompt]
        if system_instruction:
            # System instruction first, then user prompt
            parts = [system_instruction, prompt]

        response = model(
            model=model_name,
            contents=parts,
            config={"temperature": temperature},
        )

        # The new SDK exposes output_text on responses
        text = getattr(response, "text", None) or getattr(
            response, "output_text", None
        )
        return text or ""

    # Legacy SDK (google-generativeai)
    if hasattr(client, "GenerativeModel"):
        model = client.GenerativeModel(model_name)
        parts = []
        if system_instruction:
            parts.append(system_instruction)
        parts.append(prompt)

        response = model.generate_content(parts)
        # `text` property is available on the response
        return getattr(response, "text", "")

    raise RuntimeError("Unsupported Gemini client configuration.")

