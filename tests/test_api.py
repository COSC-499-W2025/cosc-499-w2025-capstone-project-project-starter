import io
import os

import api


def test_health_endpoint():
    app = api.create_app()
    client = app.test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_create_scan_requires_zip_or_path():
    app = api.create_app()
    client = app.test_client()

    response = client.post("/scans", json={})

    assert response.status_code == 400
    assert response.get_json()["error"] == "zip file or zip_path is required"


def test_create_scan_from_json_path(monkeypatch):
    app = api.create_app()
    client = app.test_client()

    captured = {}

    def mock_check_file_validity(path):
        assert path == "/tmp/sample.zip"
        return [{"filename": "/tmp/extracted/project/file.py", "isFile": True}]

    def mock_run_scan(file_list, analysis_mode, advanced_options, consent, persist):
        captured["file_list"] = file_list
        captured["analysis_mode"] = analysis_mode
        captured["advanced_options"] = advanced_options
        captured["consent"] = consent
        captured["persist"] = persist
        return {"project_summaries": [{"project": "Demo"}]}

    monkeypatch.setattr(api, "check_file_validity", mock_check_file_validity)
    monkeypatch.setattr(api, "run_scan", mock_run_scan)

    response = client.post(
        "/scans",
        json={
            "zip_path": "/tmp/sample.zip",
            "analysis_mode": "advanced",
            "advanced_options": {"framework_scan": False},
            "consent": "true",
            "persist": False,
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["analysis_mode"] == "advanced"
    assert payload["persisted"] is False
    assert payload["results"]["project_summaries"][0]["project"] == "Demo"
    assert captured["analysis_mode"] == "advanced"
    assert captured["advanced_options"] == {"framework_scan": False}
    assert captured["consent"] is True
    assert captured["persist"] is False


def test_create_scan_rejects_invalid_analysis_mode():
    app = api.create_app()
    client = app.test_client()

    response = client.post(
        "/scans",
        json={"zip_path": "/tmp/sample.zip", "analysis_mode": "expert"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "analysis_mode must be one of: basic, advanced"


def test_create_scan_rejects_invalid_advanced_options_json():
    app = api.create_app()
    client = app.test_client()

    response = client.post(
        "/scans",
        json={
            "zip_path": "/tmp/sample.zip",
            "analysis_mode": "advanced",
            "advanced_options": "{not-json}",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "advanced_options must be valid JSON"


def test_create_scan_rejects_advanced_options_in_basic_mode():
    app = api.create_app()
    client = app.test_client()

    response = client.post(
        "/scans",
        json={
            "zip_path": "/tmp/sample.zip",
            "analysis_mode": "basic",
            "advanced_options": {"framework_scan": False},
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "advanced_options is only supported in advanced mode"


def test_create_scan_with_multipart_upload(monkeypatch):
    app = api.create_app()
    client = app.test_client()
    temp_paths = []

    def mock_check_file_validity(path):
        temp_paths.append(path)
        assert os.path.exists(path)
        return [{"filename": "/tmp/extracted/project/file.py", "isFile": True}]

    monkeypatch.setattr(api, "check_file_validity", mock_check_file_validity)
    monkeypatch.setattr(
        api,
        "run_scan",
        lambda *_args, **_kwargs: {"project_summaries": [{"project": "Multipart"}]},
    )

    response = client.post(
        "/scans",
        data={
            "analysis_mode": "advanced",
            "advanced_options": '{"framework_scan": false}',
            "persist": "false",
            "zip": (io.BytesIO(b"fake zip bytes"), "demo.zip"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    assert response.get_json()["results"]["project_summaries"][0]["project"] == "Multipart"
    assert len(temp_paths) == 1
    assert not os.path.exists(temp_paths[0])


def test_create_scan_returns_400_on_invalid_zip(monkeypatch):
    app = api.create_app()
    client = app.test_client()

    monkeypatch.setattr(api, "check_file_validity", lambda _path: None)

    response = client.post("/scans", json={"zip_path": "/tmp/sample.zip"})

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid or empty zip file"


def test_create_scan_returns_500_when_scan_fails(monkeypatch):
    app = api.create_app()
    client = app.test_client()

    monkeypatch.setattr(
        api,
        "check_file_validity",
        lambda _path: [{"filename": "/tmp/extracted/project/file.py", "isFile": True}],
    )

    def explode(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(api, "run_scan", explode)

    response = client.post("/scans", json={"zip_path": "/tmp/sample.zip"})

    assert response.status_code == 500
    assert response.get_json()["error"] == "scan execution failed"


def test_get_scans_returns_list(monkeypatch):
    app = api.create_app()
    client = app.test_client()

    monkeypatch.setattr(
        api,
        "list_full_scans",
        lambda: [{"summary_id": 1, "analysis_mode": "basic", "timestamp": "t"}],
    )

    response = client.get("/scans")

    assert response.status_code == 200
    assert response.get_json()["scans"][0]["summary_id"] == 1


def test_get_scan_by_id_success(monkeypatch):
    app = api.create_app()
    client = app.test_client()

    monkeypatch.setattr(
        api,
        "get_full_scan_by_id",
        lambda _summary_id: {"summary_id": 77, "analysis_mode": "advanced"},
    )

    response = client.get("/scans/77")

    assert response.status_code == 200
    assert response.get_json()["scan"]["summary_id"] == 77


def test_get_scan_by_id_not_found(monkeypatch):
    app = api.create_app()
    client = app.test_client()

    monkeypatch.setattr(api, "get_full_scan_by_id", lambda _summary_id: None)

    response = client.get("/scans/77")

    assert response.status_code == 404
    assert response.get_json()["error"] == "scan not found"


def test_delete_scan_success(monkeypatch):
    app = api.create_app()
    client = app.test_client()

    monkeypatch.setattr(api, "delete_full_scan_by_id", lambda _summary_id: True)

    response = client.delete("/scans/5")

    assert response.status_code == 200
    body = response.get_json()
    assert body["deleted"] is True
    assert body["summary_id"] == 5


def test_delete_scan_not_found(monkeypatch):
    app = api.create_app()
    client = app.test_client()

    monkeypatch.setattr(api, "delete_full_scan_by_id", lambda _summary_id: False)

    response = client.delete("/scans/999")

    assert response.status_code == 404
    assert response.get_json()["error"] == "scan not found"
