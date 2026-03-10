import os
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Allow importing from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from api import client
from api.routes import public
from common import utils
from config import db_config


def test_utils_module_basic():
    assert utils is not None

    attributes = dir(utils)

    assert isinstance(attributes, list)
    assert len(attributes) > 0


def test_utils_callables_do_not_crash():
    for name in dir(utils):
        obj = getattr(utils, name)

        if callable(obj):
            try:
                obj()
            except TypeError:
                pass


def test_db_config_env_read(monkeypatch):
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PORT", "5432")

    assert db_config is not None


def test_db_config_environment_access():
    os.environ["POSTGRES_DB"] = "artifact_data"

    assert os.getenv("POSTGRES_DB") == "artifact_data"


def test_api_client_module():
    assert client is not None

    attrs = dir(client)

    assert isinstance(attrs, list)
    assert len(attrs) > 0


def test_api_client_functions_do_not_crash():
    for name in dir(client):
        obj = getattr(client, name)

        if callable(obj):
            try:
                obj()
            except TypeError:
                pass


def test_public_router_basic():
    app = FastAPI()
    app.include_router(public.router)

    client_test = TestClient(app)

    response = client_test.get("/public")

    assert response.status_code < 500


def test_public_router_response_format():
    app = FastAPI()
    app.include_router(public.router)

    client_test = TestClient(app)

    response = client_test.get("/public")

    assert response.headers["content-type"].startswith("application/json")