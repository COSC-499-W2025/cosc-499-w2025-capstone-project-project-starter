# src/api/exception_handlers.py
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from common.logger import setup_logger

logger = setup_logger(__name__)

async def global_exception_handler(request: Request, exc: Exception):
    # Grab the request ID from the middleware state
    request_id = getattr(request.state, "request_id", "unknown-request-id")
    
    # Log the full error to the server console with the request ID so you can debug it
    logger.error(f"Unhandled Exception [ReqID: {request_id}] at {request.url.path}: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred while processing your request.",
            "details": str(exc), # Helps frontend debug, can remove for true production security
            "request_id": request_id
        }
    )

async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", "unknown-request-id")
    
    # Log warnings for bad requests
    if exc.status_code >= 500:
        logger.error(f"HTTP {exc.status_code} [ReqID: {request_id}]: {exc.detail}")
    else:
        logger.warning(f"HTTP {exc.status_code} [ReqID: {request_id}]: {exc.detail}")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Error",
            "message": exc.detail,
            "request_id": request_id
        }
    )