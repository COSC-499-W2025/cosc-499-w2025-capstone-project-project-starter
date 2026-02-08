"""
Additional orchestrator/config coverage focused on consent and local-only paths.
Stubs heavy dependencies so tests stay lightweight.
"""
import sys
import types
from pathlib import Path

import pytest

# Ensure project root on path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def _ensure_module(name: str, module: types.ModuleType) -> None:
    if name not in sys.modules:
        sys.modules[name] = module


# Stub heavy optional dependencies
for mod_name, stub in [
    ("cv2", types.ModuleType("cv2")),
    ("pytesseract", types.ModuleType("pytesseract")),
    ("pyzbar", types.ModuleType("pyzbar")),
]:
    _ensure_module(mod_name, stub)
_ensure_module("pyzbar.pyzbar", types.ModuleType("pyzbar.pyzbar"))

if "skimage" not in sys.modules:
    skimage_pkg = types.ModuleType("skimage")
    _ensure_module("skimage", skimage_pkg)
    feature_stub = types.ModuleType("skimage.feature")
    feature_stub.graycomatrix = lambda *args, **kwargs: None
    feature_stub.graycoprops = lambda *args, **kwargs: None
    sys.modules["skimage.feature"] = feature_stub
    sys.modules["skimage.filters"] = types.ModuleType("skimage.filters")
    sys.modules["skimage.measure"] = types.ModuleType("skimage.measure")
    color_stub = types.ModuleType("skimage.color")
    color_stub.rgb2gray = lambda *args, **kwargs: None
    sys.modules["skimage.color"] = color_stub

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

whisper_stub = types.ModuleType("whisper")
whisper_stub.load_model = lambda *args, **kwargs: None
_ensure_module("whisper", whisper_stub)

from src.config import config_manager  # noqa: E402
from src.pipeline import orchestrator  # noqa: E402


def test_format_bytes_and_prompt(monkeypatch):
    pipeline = orchestrator.ArtifactPipeline(enable_insights=False)
    assert pipeline._format_bytes(1024) == "1.00 KB"
    assert pipeline._format_bytes(2048) == "2.00 KB"

    answers = iter(["maybe", "Y"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    assert orchestrator._prompt_for_llm_consent() is True


def test_request_llm_consent_helpers(monkeypatch):
    answers = iter(["", "no", "y"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    assert config_manager._prompt_yes_no("?", default=True) is True
    assert config_manager._request_llm_consent(default=None) is False


def test_identify_projects_wrapper(tmp_path):
    wrapper = tmp_path / "outer"
    wrapper.mkdir()
    (wrapper / "inner").mkdir()
    (wrapper / ".DS_Store").write_text("ignore")

    pipeline = orchestrator.ArtifactPipeline(enable_insights=False)
    pipeline.temp_dir = tmp_path
    projects, loose = pipeline._identify_projects()
    assert "inner" in projects
    assert loose == []


def test_identify_projects_no_dirs(tmp_path):
    (tmp_path / "file.txt").write_text("data")
    pipeline = orchestrator.ArtifactPipeline(enable_insights=False)
    pipeline.temp_dir = tmp_path
    projects, loose = pipeline._identify_projects()
    assert "root" in projects
    assert loose == []


def test_process_project_local_only(monkeypatch, tmp_path):
    proj = tmp_path / "proj"
    (proj / "docs").mkdir(parents=True)
    (proj / "docs" / "README.md").write_text("hello")
    (proj / "src").mkdir()
    (proj / "src" / "main.py").write_text("print('hi')")

    pipeline = orchestrator.ArtifactPipeline(enable_insights=False)

    monkeypatch.setattr(
        orchestrator,
        "categorize_folder_structure",
        lambda path: {
            "code": [str(proj / "src" / "main.py")],
            "code_by_language": {"python": [str(proj / "src" / "main.py")]},
            "documentation": [str(proj / "docs" / "README.md")],
            "images": [],
            "other": [],
        },
    )

    class StubAnalysisResult:
        def __init__(self):
            self.file_path = "main.py"
            self.language = "python"
            self.frameworks = []
            self.skills = []
            self.lines_of_code = 1
            self.file_type = "code"

        def to_dict(self):
            return self.__dict__

    from src.analyze.text_analyzer import TextMetrics

    class StubTextAnalyzer:
        def analyze_file(self, file_path):
            return TextMetrics(
                file_path=str(file_path),
                file_name=Path(file_path).name,
                file_type="txt",
                file_size_bytes=1,
                created_time="now",
                modified_time="now",
                page_count=None,
                word_count=1,
                sentence_count=1,
                paragraph_count=1,
                character_count=1,
                estimated_reading_time_minutes=0.01,
                lexical_diversity=1.0,
                avg_word_length=1.0,
                avg_sentence_length=1.0,
                top_keywords=[("test", 1)],
                heading_count=None,
                heading_breakdown=None,
            )

        def _calculate_totals(self, results):
            return {
                "total_files": len(results),
                "total_words": sum(r.word_count for r in results),
            }

    pipeline.text_analyzer = StubTextAnalyzer()
    pipeline.image_processor.batch_analyze = lambda files: []
    pipeline.code_analyzer.analyze_file = lambda f: StubAnalysisResult()
    pipeline.code_analyzer.calculate_contribution_metrics = lambda results: types.SimpleNamespace(
        to_dict=lambda: {
            "total_files": len(results),
            "total_lines": 1,
            "languages": ["python"],
            "frameworks": [],
            "skills": [],
        }
    )
    pipeline.video_analyzer.analyze_file = lambda f, transcribe=False: None
    pipeline.video_analyzer.calculate_collection_metrics = lambda results: types.SimpleNamespace(to_dict=lambda: {"total_videos": 0, "total_duration": 0.0})

    monkeypatch.setattr(orchestrator, "generate_portfolio_item", lambda project, **_: {"tagline": "t"})
    monkeypatch.setattr(orchestrator, "generate_resume_item", lambda project, **_: {"bullets": ["b1"]})

    result = pipeline._process_project("proj", proj)
    assert result["project_name"] == "proj"
    assert result["categorized_contents"]["code"]
    assert result["analysis_results"]["documentation"]["totals"]["total_files"] == 1
    assert result["analysis_results"]["code"]["metrics"]["total_files"] == 1


def test_process_project_with_git(monkeypatch, tmp_path):
    proj = tmp_path / "gitproj"
    proj.mkdir()
    (proj / ".git").mkdir()
    (proj / "file.py").write_text("print('hi')")

    pipeline = orchestrator.ArtifactPipeline(enable_insights=False)
    monkeypatch.setattr(pipeline, "_analyze_git_project", lambda path: {"total_commits": 1, "total_contributors": 1, "contributors": []})
    monkeypatch.setattr(
        orchestrator,
        "categorize_folder_structure",
        lambda path: {
            "code": [str(proj / "file.py")],
            "code_by_language": {"python": [str(proj / "file.py")]},
            "documentation": [],
            "images": [],
            "other": [],
        },
    )

    class StubAnalysisResult:
        def __init__(self):
            self.file_path = "file.py"
            self.language = "python"
            self.frameworks = []
            self.skills = []
            self.lines_of_code = 1
            self.file_type = "code"

        def to_dict(self):
            return self.__dict__

    pipeline.text_analyzer.analyze_batch = lambda files: {"files": [], "totals": {"total_files": len(files), "total_words": 0}}
    pipeline.image_processor.batch_analyze = lambda files: []
    pipeline.code_analyzer.analyze_file = lambda f: StubAnalysisResult()
    pipeline.code_analyzer.calculate_contribution_metrics = lambda results: types.SimpleNamespace(
        to_dict=lambda: {
            "total_files": len(results),
            "total_lines": 1,
            "languages": ["python"],
            "frameworks": [],
            "skills": [],
        }
    )
    pipeline.video_analyzer.analyze_file = lambda f, transcribe=False: None
    pipeline.video_analyzer.calculate_collection_metrics = lambda results: types.SimpleNamespace(to_dict=lambda: {"total_videos": 0, "total_duration": 0.0})

    monkeypatch.setattr(orchestrator, "generate_portfolio_item", lambda project, **_: {"tagline": "t"})
    monkeypatch.setattr(orchestrator, "generate_resume_item", lambda project, **_: {"bullets": ["b1"]})

    result = pipeline._process_project("gitproj", proj)
    assert result["is_git_repo"] is True
    assert result["git_analysis"]["total_commits"] == 1


def test_process_loose_files(monkeypatch, tmp_path):
    loose_txt = tmp_path / "notes.txt"
    loose_txt.write_text("hello")
    pipeline = orchestrator.ArtifactPipeline(enable_insights=False)
    pipeline._analyze_categorized_files = lambda categorized: {"documentation": {"totals": {"total_files": 1}}}
    result = pipeline._process_loose_files([loose_txt])
    assert result["categorized_contents"]["documentation"]
    assert result["analysis_results"]["documentation"]["totals"]["total_files"] == 1


def test_config_manager_cli_save_load_update(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "cli.db"
    monkeypatch.setattr(config_manager, "DB_PATH", str(db_path))

    # Save
    monkeypatch.setattr(
        sys,
        "argv",
        ["prog", "--user-id", "cli", "--save", "--zip-file", "/tmp/cli.zip", "--llm-consent", "yes"],
    )
    config_manager.run_cli()

    # Load
    monkeypatch.setattr(sys, "argv", ["prog", "--user-id", "cli", "--load", "--pretty"])
    config_manager.run_cli()

    # Update
    monkeypatch.setattr(
        sys,
        "argv",
        ["prog", "--user-id", "cli", "--update", "--zip-file", "/tmp/new.zip", "--llm-consent", "no"],
    )
    config_manager.run_cli()

    out = capsys.readouterr().out
    assert "Config updated" in out or "Config saved" in out

    cfg = config_manager.UserConfigManager(db_path=str(db_path)).load_config("cli")
    assert cfg.zip_file == "/tmp/new.zip"
    assert cfg.llm_consent is False


def test_config_manager_full_flow(monkeypatch, tmp_path):
    db_path = tmp_path / "config.db"
    monkeypatch.setattr(config_manager, "DB_PATH", str(db_path))

    manager = config_manager.UserConfigManager(db_path=str(db_path))
    manager.init_db()
    assert manager.create_config("user1", "/tmp/file.zip", False) is True
    loaded = manager.load_config("user1")
    assert loaded.zip_file == "/tmp/file.zip"
    assert loaded.llm_consent is False

    assert manager.update_config("user1", zip_file="/tmp/other.zip", llm_consent=True) is True
    loaded = manager.load_config("user1")
    assert loaded.zip_file == "/tmp/other.zip"
    assert loaded.llm_consent is True

    saved = config_manager.save_config_to_db({"zip_file": "/tmp/new.zip", "llm_consent": False}, "user1")
    assert saved is True
    assert config_manager.load_config_from_db("missing") == {}

    assert config_manager.update_config_in_db("user1", llm_consent=True) is True

    parser = types.SimpleNamespace(error=lambda msg: (_ for _ in ()).throw(SystemExit()))
    assert config_manager._parse_bool_arg("yes", parser) is True
    assert config_manager._parse_bool_arg("no", parser) is False
    with pytest.raises(SystemExit):
        config_manager._parse_bool_arg("maybe", parser)

    args = types.SimpleNamespace(zip_file=None)
    responses = iter(["", "/tmp/final.zip"])
    monkeypatch.setattr("builtins.input", lambda _: next(responses))
    assert config_manager._request_zip_file(args, current=None) == "/tmp/final.zip"

    answers = iter(["n", "y"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    assert config_manager._request_llm_consent(default=None) is False


def test_analyze_categorized_files_all_paths(monkeypatch):
    pipeline = orchestrator.ArtifactPipeline(enable_insights=False)

    class StubTextAnalyzer:
        def analyze_file(self, file_path):
            from src.analyze.text_analyzer import TextMetrics

            return TextMetrics(
                file_path=str(file_path),
                file_name=Path(file_path).name,
                file_type="txt",
                file_size_bytes=1,
                created_time="now",
                modified_time="now",
                page_count=None,
                word_count=10,
                sentence_count=1,
                paragraph_count=1,
                character_count=10,
                estimated_reading_time_minutes=0.05,
                lexical_diversity=1.0,
                avg_word_length=1.0,
                avg_sentence_length=1.0,
                top_keywords=[("test", 1)],
                heading_count=None,
                heading_breakdown=None,
            )

        def _calculate_totals(self, results):
            return {
                "total_files": len(results),
                "total_words": sum(r.word_count for r in results),
            }

    class StubImageProcessor:
        def analyze_image(self, file_path):
            return {
                "file_name": Path(file_path).name,
                "file_stats": {"size_mb": 1},
                "resolution": {"width": 1, "height": 1},
                "format": {"format": "png"},
                "content_classification": {"primary_type": "image"},
            }

    class StubCodeAnalyzer:
        def analyze_file(self, f):
            class R:
                def to_dict(self_inner):
                    return {
                        "file_path": f,
                        "language": "python",
                        "frameworks": [],
                        "skills": [],
                        "lines_of_code": 1,
                        "file_type": "code",
                    }
            return R()

        def calculate_contribution_metrics(self, analysis_objs):
            class M:
                def to_dict(self_inner):
                    return {"total_files": len(analysis_objs), "total_lines": 1, "languages": ["python"], "frameworks": [], "skills": []}
            return M()

    class StubVideoAnalyzer:
        def analyze_file(self, f, transcribe=False):
            class V:
                def to_dict(self_inner):
                    return {
                        "file_path": f,
                        "duration_seconds": 1.0,
                        "resolution": "1x1",
                        "frame_rate": 1.0,
                        "total_frames": 1,
                        "has_audio": False,
                        "file_type": "video",
                        "format": "mp4",
                    }
            return V()

        def calculate_collection_metrics(self, results):
            class M:
                def to_dict(self_inner):
                    return {"total_videos": len(results), "total_duration": 1.0}
            return M()

    pipeline.text_analyzer = StubTextAnalyzer()
    pipeline.image_processor = StubImageProcessor()
    pipeline.code_analyzer = StubCodeAnalyzer()
    pipeline.video_analyzer = StubVideoAnalyzer()

    categorized = {
        "documentation": ["docs/readme.md"],
        "images": ["img/pic.png"],
        "code": ["src/app.py"],
        "other": ["vid/movie.mp4"],
        "code_by_language": {"python": ["src/app.py"]},
    }
    results = pipeline._analyze_categorized_files(categorized)
    assert results["documentation"]["totals"]["total_files"] == 1
    assert results["images"][0]["file_name"] == "pic.png"
    assert results["code"]["metrics"]["total_files"] == 1
    assert results["videos"]["metrics"]["total_videos"] == 1


def test_analyze_git_project(monkeypatch, tmp_path):
    pipeline = orchestrator.ArtifactPipeline(enable_insights=False)

    def fake_iter_commits(path):
        return [
            {"author_name": "A", "author_email": "a@example.com"},
            {"author_name": "B", "author_email": "b@example.com"},
        ]

    def fake_summarize(project_path, email, prefer_email=True, fuzzy=False):
        return {"author": {"name": email, "email": email}, "commits": 1, "insertions": 1, "deletions": 0, "files_touched": 1, "active_weeks": 1, "first_commit_at": "2024-01-01", "last_commit_at": "2024-01-02", "activity_mix": {"feature": 1, "bugfix": 0, "test": 0, "refactor": 0, "docs": 0, "other": 0}, "share_of_commits_pct": 50.0, "top_files": [{"path": "f.py", "touches": 1}]}

    monkeypatch.setattr("src.git._git_utils.iter_commits", fake_iter_commits)
    monkeypatch.setattr(orchestrator, "summarize_author_contrib", fake_summarize)

    result = pipeline._analyze_git_project(tmp_path)
    assert result["total_commits"] == 2
    assert result["total_contributors"] == 2


def test_run_llm_summarization_success_and_error(monkeypatch, tmp_path):
    project_docs = {
        "demo": {
            "categorized_contents": {"documentation": [str(tmp_path / "a.md")]},
        },
        "no_docs": {
            "categorized_contents": {"documentation": []},
        },
    }
    (tmp_path / "a.md").write_text("content")

    class StubSummarizer:
        def summarize_document(self, path):
            return {"file_path": path, "summary": "ok"}

    import src.services.summarization_service as ss
    monkeypatch.setattr(ss, "SummarizationService", StubSummarizer)
    pipeline = orchestrator.ArtifactPipeline(enable_insights=False)
    summaries = pipeline._run_llm_summarization(project_docs)
    assert "demo" in summaries
    assert summaries["demo"][0]["summary"] == "ok"

    class BoomSummarizer:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("no llm")

    monkeypatch.setattr(ss, "SummarizationService", BoomSummarizer)
    assert "error" in pipeline._run_llm_summarization(project_docs)


def test_print_summary_with_misc_and_llm(monkeypatch, capsys):
    pipeline = orchestrator.ArtifactPipeline(enable_insights=False)
    result = {
        "zip_metadata": {"file_count": 2, "total_uncompressed_bytes": 1024, "total_compressed_bytes": 512},
        "projects": {
            "proj": {
                "project_name": "proj",
                "is_git_repo": True,
                "git_analysis": {"total_commits": 1, "total_contributors": 1, "contributors": [{"author": {"name": "a"}, "commits": 1}]},
                "categorized_contents": {
                    "code": ["a.py"],
                    "code_by_language": {"python": ["a.py"]},
                    "documentation": ["README.md"],
                    "images": [],
                    "other": [],
                },
                "analysis_results": {
                    "documentation": {"totals": {"total_files": 1, "total_words": 10}},
                    "images": [],
                    "code": {"metrics": {"total_files": 1, "total_lines": 10, "languages": ["python"]}},
                    "videos": {"metrics": {"total_videos": 0, "total_duration": 0}},
                },
                "portfolio_item": {"tagline": "t", "is_collaborative": False},
                "resume_item": {"bullets": ["b"]},
            },
            "_misc_files": {
                "categorized_contents": {
                    "code": ["b.py"],
                    "code_by_language": {"python": ["b.py"]},
                    "documentation": [],
                    "images": [],
                    "other": [],
                },
                "analysis_results": {
                    "documentation": {"totals": {"total_files": 0, "total_words": 0}},
                    "images": [],
                    "code": {"metrics": {"total_files": 1, "total_lines": 5}},
                    "videos": {"metrics": {"total_videos": 0, "total_duration": 0}},
                },
            },
        },
        "llm_summaries": {"proj": [{"file_path": "README.md", "summary": "ok"}]},
    }
    pipeline._print_summary(result)
    captured = capsys.readouterr().out
    assert "Pipeline Complete" in captured
    assert "proj" in captured


def test_main_smoke(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(orchestrator, "resolve_llm_consent", lambda zip_path, user_id: False)
    monkeypatch.setattr(orchestrator, "resolve_data_access_consent", lambda zip_path, user_id: True)
    called = {}

    def fake_start(self, zip_path, use_llm=False, data_access_consent=True, **_):
        called["zip"] = zip_path
        called["llm"] = use_llm
        return {
            "projects": {
                "proj": {
                    "is_git_repo": False,
                    "analysis_results": {"documentation": None, "images": None, "code": None, "videos": None},
                    "categorized_contents": {},
                }
            }
        }

    monkeypatch.setattr(orchestrator.ArtifactPipeline, "start", fake_start)
    monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path / "z.zip")])
    orchestrator.main()
    assert called["zip"] == str(tmp_path / "z.zip")


def test_start_happy_path(monkeypatch, tmp_path):
    zip_file = tmp_path / "demo.zip"
    (tmp_path / "inner").mkdir()
    (tmp_path / "inner" / "file.txt").write_text("data")
    import zipfile
    with zipfile.ZipFile(zip_file, "w") as zf:
        zf.write(tmp_path / "inner" / "file.txt", arcname="inner/file.txt")

    class StubZipIndex:
        file_count = 1
        root_name = "demo"
        total_uncompressed_bytes = 10
        total_compressed_bytes = 8

    monkeypatch.setattr(orchestrator, "parse_zip", lambda path: StubZipIndex())

    pipeline = orchestrator.ArtifactPipeline(enable_insights=False)
    monkeypatch.setattr(pipeline, "_identify_projects", lambda: ({"proj": tmp_path / "inner"}, []))
    monkeypatch.setattr(pipeline, "_process_project", lambda name, path: {"project_name": name, "categorized_contents": {}, "analysis_results": {}})
    monkeypatch.setattr(pipeline, "_process_loose_files", lambda files: {})
    monkeypatch.setattr(pipeline, "_persist_insights", lambda zip_path, payload: None)
    monkeypatch.setattr(pipeline, "_print_summary", lambda result: None)

    result = pipeline.start(str(zip_file), use_llm=False)
    assert result["zip_metadata"]["file_count"] == 1
    assert "proj" in result["projects"]
