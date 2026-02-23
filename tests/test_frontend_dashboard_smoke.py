from pathlib import Path

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