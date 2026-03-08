import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from api.utils.request_id import get_or_create_request_id

REQUEST_ID_HEADER = "X-Request-ID"

PROCESS_TIME_HEADER = "X-Process-Time-ms" 

class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = get_or_create_request_id(request.headers, REQUEST_ID_HEADER)
        request.state.request_id = request_id
        start_time = time.time()
        response = await call_next(request)
        process_time_ms = int((time.time() - start_time) * 1000)
        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers[PROCESS_TIME_HEADER] = str(process_time_ms)
        
        return response