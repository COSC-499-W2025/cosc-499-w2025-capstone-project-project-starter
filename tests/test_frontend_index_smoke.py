from pathlib import Path

def _read_index_html() -> str:
    for p in (Path("frontend/index.html"), Path("index.html")):
        if p.exists():
            return p.read_text(encoding="utf-8")
    raise AssertionError("index.html not found")

def test_index_message_boxes_have_aria_live():
    text = _read_index_html()
    assert 'id="messageBox"' in text
    assert 'aria-live="polite"' in text
    assert 'aria-atomic="true"' in text

def test_index_has_postjson_helper():
    text = _read_index_html()
    assert "async function postJson" in text
    assert "/api/auth/login" in text
    assert "/api/auth/register" in text