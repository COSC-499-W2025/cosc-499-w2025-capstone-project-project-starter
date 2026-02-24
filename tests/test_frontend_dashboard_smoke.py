from pathlib import Path
import re

def test_dashboard_has_state_key_and_helpers():
    dashboard = Path("frontend/dashboard.html").read_text(encoding="utf-8")

    assert "dashboard_state_v1" in dashboard
    assert "loadDashboardState" in dashboard
    assert "saveDashboardState" in dashboard
    assert "apiRequest" in dashboard

def test_dashboard_select_project_uses_event_param():
    dashboard = Path("frontend/dashboard.html").read_text(encoding="utf-8")
    # to ensure the selectProject function uses the event parameter for selection, we check if it looks for 'event' in its implementation
    assert "selectProject(event," in dashboard

def test_dashboard_response_ok_only_used_in_api_wrappers():
    """
    Regression: `response.ok` should only be used inside our fetch wrapper(s),
    e.g. apiCall()/apiRequest(), not inside feature functions.
    """
    candidates = [Path("dashboard.html"), Path("frontend/dashboard.html")]
    dashboard_path = next((p for p in candidates if p.exists()), None)
    assert dashboard_path is not None, "dashboard.html not found"

    text = dashboard_path.read_text(encoding="utf-8")

    allowed = {"apiCall", "apiRequest"}

    for m in re.finditer(r"response\.ok", text):
        pos = m.start()
        before = text[:pos]

        # Find the nearest preceding "function <name>(" (covers async too if written as "async function")
        func_matches = list(re.finditer(r"(?:async\s+)?function\s+([A-Za-z0-9_]+)\s*\(", before))
        assert func_matches, "response.ok found but no enclosing function detected"

        func_name = func_matches[-1].group(1)
        assert func_name in allowed, f"response.ok used inside '{func_name}', not an API wrapper"

def _read_dashboard_html() -> str:
    for p in (Path("frontend/dashboard.html"), Path("dashboard.html")):
        if p.exists():
            return p.read_text(encoding="utf-8")
    raise AssertionError("dashboard.html not found in expected locations")

def _extract_function_body(text: str, name: str) -> str:
    # very lightweight extractor: find "function name" and take a chunk after it
    i = text.find(f"function {name}")
    assert i != -1, f"function {name} not found"
    return text[i:i+2500]  # enough to include the function body

def test_dashboard_api_wrapper_uses_defined_base_url_and_helpers_do_not_overwrite():
    text = _read_dashboard_html()

    api_call_chunk = _extract_function_body(text, "apiCall")

    # 1) Guard: apiCall should build fetch URL from API_BASE_URL and endpoint (avoid undefined API_BASE)
    assert "fetch(" in api_call_chunk
    assert "API_BASE_URL" in api_call_chunk, "apiCall should reference API_BASE_URL"
    assert "endpoint" in api_call_chunk, "apiCall should reference endpoint when building URL"

    # 2) Guard: helpers should not overwrite container.innerHTML
    assert "function renderSuccess" in text and "function renderError" in text
    assert "insertAdjacentHTML" in text, "Expected helpers to use insertAdjacentHTML (no overwrite)"