"""Tests for Gemini-powered project ranking."""
import sys, os, json, pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from analysis.gemini_ranker import GeminiRanker, rank_projects_with_gemini


# -- fixtures --------------------------------------------------------------

def _make_projects(n=3):
    """Create n fake project dicts."""
    return [
        {
            "project_id": i,
            "filename": f"project{i}.zip",
            "file_count": i * 5,
            "languages": ["Python"],
            "file_snippets": [{"path": "main.py", "content": f"print('hello {i}')"}],
        }
        for i in range(1, n + 1)
    ]


GOOD_GEMINI_RESPONSE = json.dumps({
    "rankings": [
        {"project_index": 2, "score": 90, "strengths": ["clean code"], "weaknesses": [], "one_line_summary": "Great"},
        {"project_index": 1, "score": 70, "strengths": ["simple"], "weaknesses": ["no tests"], "one_line_summary": "OK"},
        {"project_index": 3, "score": 50, "strengths": [], "weaknesses": ["messy"], "one_line_summary": "Meh"},
    ],
    "overall_reasoning": "Project 2 is the best because ...",
})


# -- GeminiRanker.rank_projects tests --------------------------------------

class TestRankProjects:
    def test_empty_input(self):
        r = GeminiRanker().rank_projects([])
        assert r["success"] is False
        assert r["rankings"] == []

    def test_single_project(self):
        r = GeminiRanker().rank_projects(_make_projects(1))
        assert r["success"] is True
        assert len(r["rankings"]) == 1
        assert r["rankings"][0]["score"] == 100
        assert r["rankings"][0]["project_id"] == 1

    @patch("analysis.gemini_ranker.generate_text", return_value=GOOD_GEMINI_RESPONSE)
    def test_multiple_projects_success(self, mock_gen):
        r = GeminiRanker().rank_projects(_make_projects(3))
        assert r["success"] is True
        assert len(r["rankings"]) == 3
        # best-first ordering preserved from Gemini
        assert r["rankings"][0]["project_id"] == 2
        assert r["rankings"][0]["score"] == 90
        assert r["reasoning"] == "Project 2 is the best because ..."
        mock_gen.assert_called_once()

    @patch("analysis.gemini_ranker.generate_text", side_effect=RuntimeError("boom"))
    def test_gemini_error(self, _):
        r = GeminiRanker().rank_projects(_make_projects(2))
        assert r["success"] is False
        assert "boom" in r["error"]

    @patch("analysis.gemini_ranker.generate_text", side_effect=RuntimeError("429 rate limit"))
    def test_rate_limit_message(self, _):
        r = GeminiRanker().rank_projects(_make_projects(2))
        assert r["success"] is False
        assert "rate limit" in r["error"].lower()

    @patch("analysis.gemini_ranker.generate_text", return_value="not json at all")
    def test_unparseable_response_fallback(self, _):
        r = GeminiRanker().rank_projects(_make_projects(2))
        assert r["success"] is True
        assert len(r["rankings"]) == 2
        # fallback gives score 0
        assert all(rank["score"] == 0 for rank in r["rankings"])
        assert "Parse error" in r["reasoning"]

    @patch("analysis.gemini_ranker.generate_text")
    def test_partial_response_fills_missing(self, mock_gen):
        """If Gemini only returns 2 of 3 projects, the third gets score 0."""
        partial = json.dumps({
            "rankings": [
                {"project_index": 1, "score": 80, "strengths": [], "weaknesses": [], "one_line_summary": ""},
            ],
            "overall_reasoning": "partial",
        })
        mock_gen.return_value = partial
        r = GeminiRanker().rank_projects(_make_projects(3))
        assert r["success"] is True
        assert len(r["rankings"]) == 3
        ids = [x["project_id"] for x in r["rankings"]]
        assert 1 in ids and 2 in ids and 3 in ids
        missing = [x for x in r["rankings"] if x["project_id"] in (2, 3)]
        assert all(x["score"] == 0 for x in missing)


# -- prompt building -------------------------------------------------------

class TestBuildPrompt:
    def test_prompt_contains_project_info(self):
        ranker = GeminiRanker()
        prompt = ranker._build_ranking_prompt(_make_projects(2))
        assert "project1.zip" in prompt
        assert "project2.zip" in prompt
        assert "Python" in prompt
        assert "main.py" in prompt

    def test_prompt_no_snippets(self):
        projects = [{"project_id": 1, "filename": "empty.zip", "file_count": 0,
                      "languages": [], "file_snippets": []}]
        prompt = GeminiRanker()._build_ranking_prompt(projects)
        assert "(none)" in prompt


# -- response parsing -------------------------------------------------------

class TestParseResponse:
    def test_valid_json(self):
        ranker = GeminiRanker()
        result = ranker._parse_response(GOOD_GEMINI_RESPONSE, _make_projects(3))
        assert len(result["rankings"]) == 3
        assert result["rankings"][0]["score"] == 90

    def test_bad_json(self):
        result = GeminiRanker()._parse_response("garbage", _make_projects(2))
        assert all(r["score"] == 0 for r in result["rankings"])
        assert "Parse error" in result["reasoning"]

    def test_extract_json_embedded(self):
        text = "Here is the result:\n" + GOOD_GEMINI_RESPONSE + "\nDone."
        parsed = GeminiRanker._extract_json(text)
        assert parsed is not None
        assert "rankings" in parsed

    def test_extract_json_none(self):
        assert GeminiRanker._extract_json("no json here") is None

    def test_invalid_project_index_skipped(self):
        resp = json.dumps({
            "rankings": [{"project_index": 999, "score": 50, "strengths": [], "weaknesses": [], "one_line_summary": ""}],
            "overall_reasoning": "",
        })
        result = GeminiRanker()._parse_response(resp, _make_projects(2))
        # Both projects should appear via the missing-fill logic
        assert len(result["rankings"]) == 2
        assert all(r["score"] == 0 for r in result["rankings"])


# -- retry logic -----------------------------------------------------------

class TestRetry:
    @patch("analysis.gemini_ranker.generate_text")
    @patch("analysis.gemini_ranker.time.sleep")
    def test_retries_on_429(self, mock_sleep, mock_gen):
        mock_gen.side_effect = [RuntimeError("429"), "ok"]
        result = GeminiRanker()._call_with_retry("prompt")
        assert result == "ok"
        mock_sleep.assert_called_once_with(2)

    @patch("analysis.gemini_ranker.generate_text")
    @patch("analysis.gemini_ranker.time.sleep")
    def test_exhausted_retries(self, mock_sleep, mock_gen):
        mock_gen.side_effect = RuntimeError("429 exhausted")
        with pytest.raises(RuntimeError, match="429"):
            GeminiRanker()._call_with_retry("prompt")
        assert mock_sleep.call_count == 2  # retried twice before final raise

    @patch("analysis.gemini_ranker.generate_text", side_effect=ValueError("bad input"))
    def test_non_429_not_retried(self, _):
        with pytest.raises(ValueError, match="bad input"):
            GeminiRanker()._call_with_retry("prompt")


# -- gather_projects_data ---------------------------------------------------

class TestGatherData:
    @patch("analysis.gemini_ranker.get_file_contents_by_upload_id", return_value=[])
    @patch("analysis.gemini_ranker.get_connection")
    def test_gather_success(self, mock_conn, mock_files):
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = [
            (1, "proj.zip", json.dumps({"files": ["a.py"], "languages": ["Python"]})),
        ]
        mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cur

        data = GeminiRanker().gather_projects_data(user_name="alice")
        assert len(data) == 1
        assert data[0]["filename"] == "proj.zip"
        assert data[0]["languages"] == ["Python"]

    @patch("analysis.gemini_ranker.AuthManager")
    def test_gather_no_user(self, mock_auth):
        mock_auth.get_current_username.return_value = None
        assert GeminiRanker().gather_projects_data() == []

    @patch("analysis.gemini_ranker.get_connection", side_effect=Exception("db down"))
    def test_gather_db_error(self, _):
        assert GeminiRanker().gather_projects_data(user_name="x") == []


# -- get_snippets -----------------------------------------------------------

class TestGetSnippets:
    @patch("analysis.gemini_ranker.get_file_contents_by_upload_id")
    def test_filters_and_sorts(self, mock_files):
        mock_files.return_value = [
            {"file_path": "readme.md", "file_name": "readme.md", "file_extension": ".md",
             "file_content": "# hi", "is_binary": False},
            {"file_path": "main.py", "file_name": "main.py", "file_extension": ".py",
             "file_content": "x = 1\n" * 20, "is_binary": False},
            {"file_path": "utils.py", "file_name": "utils.py", "file_extension": ".py",
             "file_content": "y = 2\n" * 20, "is_binary": False},
        ]
        snips = GeminiRanker()._get_snippets(1)
        assert len(snips) == 2  # .md filtered out
        assert snips[0]["path"] == "main.py"  # priority name first

    @patch("analysis.gemini_ranker.get_file_contents_by_upload_id", return_value=[])
    def test_empty_files(self, _):
        assert GeminiRanker()._get_snippets(1) == []

    @patch("analysis.gemini_ranker.get_file_contents_by_upload_id", side_effect=Exception("err"))
    def test_exception(self, _):
        assert GeminiRanker()._get_snippets(1) == []

    @patch("analysis.gemini_ranker.get_file_contents_by_upload_id")
    def test_binary_skipped(self, mock_files):
        mock_files.return_value = [
            {"file_path": "img.py", "file_name": "img.py", "file_extension": ".py",
             "file_content": "data", "is_binary": True},
        ]
        assert GeminiRanker()._get_snippets(1) == []

    @patch("analysis.gemini_ranker.get_file_contents_by_upload_id")
    def test_bytes_content_decoded(self, mock_files):
        mock_files.return_value = [
            {"file_path": "app.py", "file_name": "app.py", "file_extension": ".py",
             "file_content": b"print('hello world')\n" * 5, "is_binary": False},
        ]
        snips = GeminiRanker()._get_snippets(1)
        assert len(snips) == 1
        assert "hello world" in snips[0]["content"]


# -- convenience function --------------------------------------------------

class TestConvenienceFunction:
    @patch("analysis.gemini_ranker.GeminiRanker.gather_projects_data", return_value=[])
    def test_no_projects(self, _):
        r = rank_projects_with_gemini(user_name="bob")
        assert r["success"] is False
        assert "No projects" in r["error"]

    @patch("analysis.gemini_ranker.GeminiRanker.rank_projects")
    @patch("analysis.gemini_ranker.GeminiRanker.gather_projects_data")
    def test_delegates(self, mock_gather, mock_rank):
        mock_gather.return_value = _make_projects(2)
        mock_rank.return_value = {"success": True, "rankings": [], "reasoning": ""}
        r = rank_projects_with_gemini(user_name="alice")
        assert r["success"] is True
        mock_rank.assert_called_once()
