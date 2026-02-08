import sys
import zipfile
import types
import importlib.util
from pathlib import Path

import pytest

# Ensure the project root is on the Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def _ensure_module(name: str, module: types.ModuleType) -> None:
    if name not in sys.modules:
        sys.modules[name] = module


# Stub optional heavy dependencies when they aren't available locally so the orchestrator can import
if importlib.util.find_spec("moviepy.editor") is None:
    moviepy_stub = types.ModuleType("moviepy")
    editor_stub = types.ModuleType("moviepy.editor")

    class _DummyVideoFileClip:
        def __init__(self, *args, **kwargs):
            self.duration = 0
            self.fps = 0
            self.size = (0, 0)
            self.audio = None

        def close(self):
            return None

    editor_stub.VideoFileClip = _DummyVideoFileClip
    moviepy_stub.editor = editor_stub
    _ensure_module("moviepy", moviepy_stub)
    sys.modules["moviepy.editor"] = editor_stub

if importlib.util.find_spec("whisper") is None:
    whisper_stub = types.ModuleType("whisper")
    whisper_stub.load_model = lambda *args, **kwargs: None
    _ensure_module("whisper", whisper_stub)

if importlib.util.find_spec("cv2") is None:
    _ensure_module("cv2", types.ModuleType("cv2"))

if importlib.util.find_spec("pytesseract") is None:
    pytesseract_stub = types.ModuleType("pytesseract")
    pytesseract_stub.image_to_string = lambda *args, **kwargs: ""
    _ensure_module("pytesseract", pytesseract_stub)

if importlib.util.find_spec("pyzbar") is None:
    pyzbar_pkg = types.ModuleType("pyzbar")
    pyzbar_mod = types.ModuleType("pyzbar.pyzbar")
    pyzbar_mod.decode = lambda *args, **kwargs: []
    pyzbar_pkg.pyzbar = pyzbar_mod
    _ensure_module("pyzbar", pyzbar_pkg)
    sys.modules["pyzbar.pyzbar"] = pyzbar_mod

if importlib.util.find_spec("skimage") is None:
    skimage_pkg = types.ModuleType("skimage")
    skimage_feature_stub = types.ModuleType("skimage.feature")
    skimage_filters_stub = types.ModuleType("skimage.filters")
    skimage_measure_stub = types.ModuleType("skimage.measure")
    skimage_color_stub = types.ModuleType("skimage.color")
    skimage_color_stub.rgb2gray = lambda *args, **kwargs: None
    skimage_feature_stub.graycomatrix = lambda *args, **kwargs: None
    skimage_feature_stub.graycoprops = lambda *args, **kwargs: None
    _ensure_module("skimage", skimage_pkg)
    sys.modules["skimage.feature"] = skimage_feature_stub
    sys.modules["skimage.filters"] = skimage_filters_stub
    sys.modules["skimage.measure"] = skimage_measure_stub
    sys.modules["skimage.color"] = skimage_color_stub

from src.config import config_manager
from src.pipeline import orchestrator


@pytest.fixture
def temp_db(monkeypatch, tmp_path):
    """Point the config manager at a temporary SQLite DB."""
    db_path = tmp_path / "user_config.db"
    monkeypatch.setattr(config_manager, "DB_PATH", str(db_path))
    return str(db_path)


def _create_test_zip(tmp_path: Path) -> Path:
    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    (project_dir / "README.md").write_text("hello world")

    zip_path = tmp_path / "proj.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in project_dir.rglob("*"):
            zf.write(file_path, file_path.relative_to(project_dir.parent))
    return zip_path


# def test_resolve_llm_consent_reuses_existing(monkeypatch, temp_db, tmp_path):
#     manager = config_manager.UserConfigManager(db_path=temp_db)
#     manager.create_config("tester", "/tmp/original.zip", True)

#     prompts = []
#     monkeypatch.setattr("builtins.input", lambda _: prompts.append("asked") or "y")

#     new_zip = tmp_path / "latest.zip"
#     new_zip.write_text("placeholder zip path marker")

#     consent = orchestrator.resolve_llm_consent(str(new_zip), "tester")

#     assert consent is True
#     assert prompts == []

#     cfg = manager.load_config("tester")
#     assert cfg.zip_file == str(new_zip)


def test_resolve_llm_consent_prompts_and_saves(monkeypatch, temp_db, tmp_path):
    responses = iter(["n"])
    monkeypatch.setattr("builtins.input", lambda _: next(responses))

    zip_path = tmp_path / "file.zip"
    zip_path.write_text("placeholder zip path marker")

    consent = orchestrator.resolve_llm_consent(str(zip_path), "fresh-user")
    assert consent is False

    cfg = config_manager.UserConfigManager(db_path=temp_db).load_config("fresh-user")
    assert cfg is not None
    assert cfg.llm_consent is False
    assert cfg.zip_file == str(zip_path)


def test_resolve_data_access_consent_prompts_and_saves(monkeypatch, temp_db, tmp_path):
    responses = iter(["y"])
    monkeypatch.setattr("builtins.input", lambda _: next(responses))

    zip_path = tmp_path / "data.zip"
    zip_path.write_text("placeholder zip path marker")

    consent = orchestrator.resolve_data_access_consent(str(zip_path), "fresh-user")
    assert consent is True

    cfg = config_manager.UserConfigManager(db_path=temp_db).load_config("fresh-user")
    assert cfg is not None
    assert cfg.data_access_consent is True
    assert cfg.llm_consent is False
    assert cfg.llm_consent_asked is False
    assert cfg.zip_file == str(zip_path)


def test_resolve_data_access_consent_reprompts_after_denial(monkeypatch, temp_db, tmp_path):
    manager = config_manager.UserConfigManager(db_path=temp_db)
    manager.create_config(
        "tester",
        "/tmp/original.zip",
        llm_consent=False,
        llm_consent_asked=False,
        data_access_consent=False,
    )

    prompts = []
    monkeypatch.setattr("builtins.input", lambda _: prompts.append(True) or "y")

    zip_path = tmp_path / "latest.zip"
    zip_path.write_text("placeholder zip path marker")

    consent = orchestrator.resolve_data_access_consent(str(zip_path), "tester")
    assert consent is True
    assert len(prompts) == 1

    cfg = manager.load_config("tester")
    assert cfg.data_access_consent is True
    assert cfg.zip_file == str(zip_path)


def test_pipeline_runs_llm_when_enabled(monkeypatch, tmp_path):
    zip_path = _create_test_zip(tmp_path)

    pipeline = orchestrator.ArtifactPipeline(enable_insights=False)
    called = {"ran": False}

    def fake_llm(projects):
        called["ran"] = True
        return {"projects": list(projects.keys())}

    monkeypatch.setattr(pipeline, "_analyze_categorized_files", lambda categorized: {})
    monkeypatch.setattr(pipeline, "_run_llm_summarization", fake_llm)

    result = pipeline.start(str(zip_path), use_llm=True)

    assert called["ran"] is True
    assert result.get("llm_summaries") == {"projects": ["proj"]}


def test_pipeline_skips_llm_when_disabled(monkeypatch, tmp_path):
    zip_path = _create_test_zip(tmp_path)

    pipeline = orchestrator.ArtifactPipeline(enable_insights=False)

    def fail(_projects):
        raise AssertionError("LLM summarization should be skipped")

    monkeypatch.setattr(pipeline, "_analyze_categorized_files", lambda categorized: {})
    monkeypatch.setattr(pipeline, "_run_llm_summarization", fail)

    result = pipeline.start(str(zip_path), use_llm=False)

    assert "llm_summaries" not in result
