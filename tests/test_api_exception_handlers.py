import os
import sys

from fastapi import HTTPException
from fastapi.testclient import TestClient

# Allow importing from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from api.main import app

client = TestClient(app, raise_server_exceptions=False)


@app.get("/test-http-exception-string")
async def route_http_exception_string():
    raise HTTPException(status_code=404, detail="Not found")


@app.get("/test-http-exception-dict")
async def route_http_exception_dict():
    raise HTTPException(
        status_code=400,
        detail={
            "error_type": "VALIDATION_ERROR",
            "message": "Bad request data",
        },
    )


@app.get("/test-runtime-error")
async def route_runtime_error():
    raise RuntimeError("Unexpected failure")


def test_http_exception_string_response():
    response = client.get("/test-http-exception-string")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")

    data = response.json()
    assert isinstance(data, dict)


def test_http_exception_dict_response():
    response = client.get("/test-http-exception-dict")

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/json")

    data = response.json()
    assert isinstance(data, dict)


def test_runtime_error_response():
    response = client.get("/test-runtime-error")

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/json")

    data = response.json()
    assert isinstance(data, dict)