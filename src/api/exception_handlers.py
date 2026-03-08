from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from common.logger import setup_logger

logger = setup_logger(__name__)

async def global_exception_handler(request: Request, exc: Exception):
    """
    Catches ALL unhandled Python exceptions (500 Internal Server Error).
    """
    request_id = getattr(request.state, "request_id", "unknown-request-id")
    logger.error(f"Unhandled Exception [ReqID: {request_id}] at {request.url.path}: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred while processing your request.",
            "request_id": request_id
        }
    )

async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Catches standard FastAPI HTTPExceptions (400, 401, 404, 422 etc.)
    """
    request_id = getattr(request.state, "request_id", "unknown-request-id")
    if isinstance(exc.detail, str):
        message = exc.detail
        details = None
    else:
        message = "A validation or request structure error occurred."
        details = exc.detail

    if exc.status_code >= 500:
        logger.error(f"HTTP {exc.status_code} [ReqID: {request_id}]: {exc.detail}")
    else:
        logger.warning(f"HTTP {exc.status_code} [ReqID: {request_id}]: {exc.detail}")

    payload = {
        "error": "HTTP Error",
        "message": message,
        "request_id": request_id
    }
    
    if details is not None:
        payload["details"] = details

    return JSONResponse(
        status_code=exc.status_code,
        content=payload
    )