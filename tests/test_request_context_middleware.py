from fastapi.testclient import TestClient

import sys
import os
# Adjust the path to import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from api.main import app


def test_request_id_added_when_missing():
    client = TestClient(app)

    r = client.get("/api/health")
    assert r.status_code == 200

    assert "X-Request-ID" in r.headers
    assert r.headers["X-Request-ID"] != ""

    assert "X-Process-Time-ms" in r.headers
    float(r.headers["X-Process-Time-ms"])


def test_request_id_preserved_when_provided():
    client = TestClient(app)

    r = client.get("/api/health", headers={"X-Request-ID": "eric-123"})
    assert r.status_code == 200
    assert r.headers["X-Request-ID"] == "eric-123"
    float(r.headers["X-Process-Time-ms"])


def test_error_response_includes_request_id():
    client = TestClient(app)

    r = client.get("/dashboard.html", headers={"X-Request-ID": "eric-err-1"})
    assert r.status_code in (404, 200)

    if r.status_code == 404:
        body = r.json()
        assert body["success"] is False
        assert body["request_id"] == "eric-err-1"

def test_get_or_create_request_id_pure_function():
    from api.utils.request_id import get_or_create_request_id

    rid1 = get_or_create_request_id({})
    assert isinstance(rid1, str) and len(rid1) > 0

    rid2 = get_or_create_request_id({"X-Request-ID": "fixed-id"})
    assert rid2 == "fixed-id"

    rid3 = get_or_create_request_id({"x-request-id": "lowercase-id"})
    assert rid3 == "lowercase-id"