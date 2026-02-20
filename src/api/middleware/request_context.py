"""Request context middleware: adds request-id and processing time headers."""

import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from api.utils.request_id import get_or_create_request_id

REQUEST_ID_HEADER = "X-Request-ID"
PROCESS_TIME_HEADER = "X-Process-Time-ms"

class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Adds:
      - X-Request-ID: incoming value preserved, otherwise generated UUID4
      - X-Process-Time-ms: request processing time in milliseconds
    Also stores request_id in request.state.request_id for use in handlers/logging.
    """
    async def dispatch(self, request: Request, call_next):
        request_id = get_or_create_request_id(dict(request.headers), REQUEST_ID_HEADER)
        request.state.request_id = request_id

        start = time.perf_counter()
        response: Response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers[PROCESS_TIME_HEADER] = f"{elapsed_ms:.2f}"
        return response