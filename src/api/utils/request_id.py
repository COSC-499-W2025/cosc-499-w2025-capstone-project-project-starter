"""Helpers for request id handling."""

import uuid
from typing import Mapping, Optional

REQUEST_ID_HEADER = "X-Request-ID"

def get_or_create_request_id(headers: Mapping[str, str], header_name: str = REQUEST_ID_HEADER) -> str:
    """
    Return client-supplied request id if present; otherwise generate one.

    Header lookup is case-insensitive.
    """
    if not headers:
        return str(uuid.uuid4())

    # case-insensitive lookup
    target = header_name.lower()
    existing: Optional[str] = None
    for k, v in headers.items():
        if k.lower() == target and v:
            existing = v
            break

    return existing or str(uuid.uuid4())