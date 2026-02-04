from __future__ import annotations

import argparse # CLI argument parsing
import json
import os
import sys
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


DEFAULT_API_URL = "http://localhost:5001"
DEFAULT_STATE_PATH = ".artifactminer_state.json"


# ----------------------------
# Utilities
# ----------------------------

def _eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def _pretty(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, default=str)


def _api_url(args: argparse.Namespace) -> str:
    return (args.api_url or os.environ.get("ARTIFACT_MINER_API_URL") or DEFAULT_API_URL).rstrip("/")


def _bool_flag(s: str) -> bool:
    v = s.strip().lower()
    if v in ("1", "true", "t", "yes", "y", "on"):
        return True
    if v in ("0", "false", "f", "no", "n", "off"):
        return False
    raise argparse.ArgumentTypeError(f"invalid boolean: {s}")


def _require_file(path: str) -> Path:
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise argparse.ArgumentTypeError(f"file not found: {p}")
    return p


def _require_zip(path: str) -> Path:
    p = _require_file(path)
    if p.suffix.lower() != ".zip":
        raise argparse.ArgumentTypeError("expected a .zip file")
    return p


# ----------------------------
# State (for demos)
# ----------------------------

@dataclass
class DemoState:
    api_url: str = DEFAULT_API_URL
    user_id: Optional[str] = None
    portfolio_id: Optional[str] = None
    last_upload: Dict[str, Any] = field(default_factory=dict)
    last_project_id: Optional[str] = None
    last_snapshot_id: Optional[str] = None
    last_analysis_id: Optional[str] = None
    last_resume_id: Optional[str] = None
    last_showcase_id: Optional[str] = None

    def apply_upload_response(self, res: Dict[str, Any]) -> None:
        self.last_upload = res or {}
        self.user_id = str(res.get("user_id") or self.user_id or "") or self.user_id
        self.portfolio_id = str(res.get("portfolio_id") or self.portfolio_id or "") or self.portfolio_id

        created = (res.get("created") or [])
        if created:
            c0 = created[0] or {}
            if c0.get("project_id"):
                self.last_project_id = str(c0["project_id"])
            if c0.get("snapshot_id"):
                self.last_snapshot_id = str(c0["snapshot_id"])

    def apply_projects_response(self, res: Dict[str, Any]) -> None:
        projects = res.get("projects") or []
        if projects:
            self.last_project_id = str(projects[0].get("id") or self.last_project_id or "") or self.last_project_id
            latest = (projects[0].get("latest_snapshot") or {}).get("id")
            if latest:
                self.last_snapshot_id = str(latest)

    def apply_portfolio_generate(self, res: Dict[str, Any]) -> None:
        showcases = res.get("showcases") or []
        if showcases:
            sc0 = showcases[0] or {}
            if sc0.get("id"):
                self.last_showcase_id = str(sc0["id"])

    def apply_resume_generate(self, res: Dict[str, Any]) -> None:
        if res.get("resume_id"):
            self.last_resume_id = str(res["resume_id"])


def _load_state(path: Path) -> DemoState:
    if not path.exists():
        return DemoState()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        st = DemoState()
        for k, v in (data or {}).items():
            if hasattr(st, k):
                setattr(st, k, v)
        return st
    except Exception:
        return DemoState()


def _save_state(path: Path, st: DemoState) -> None:
    path.write_text(_pretty(asdict(st)) + "\n", encoding="utf-8")


# ----------------------------
# HTTP client
# ----------------------------

class ApiClient:
    def __init__(self, base_url: str, timeout_s: float = 30.0):
        self.base = base_url.rstrip("/")
        self.timeout_s = float(timeout_s)
        self.sess = requests.Session()

    def _req(self, method: str, path: str, *, params=None, json_body=None, data=None, files=None, timeout_s=None) -> requests.Response:
        url = f"{self.base}{path}"
        t = self.timeout_s if timeout_s is None else float(timeout_s)
        r = self.sess.request(method, url, params=params, json=json_body, data=data, files=files, timeout=t)
        return r

    def get(self, path: str, *, params=None, timeout_s=None) -> Dict[str, Any]:
        r = self._req("GET", path, params=params, timeout_s=timeout_s)
        self._raise_for_status(r)
        return r.json()

    def post(self, path: str, *, json_body=None, data=None, files=None, timeout_s=None) -> Dict[str, Any]:
        r = self._req("POST", path, json_body=json_body, data=data, files=files, timeout_s=timeout_s)
        self._raise_for_status(r)
        return r.json()

    def put(self, path: str, *, json_body=None, timeout_s=None) -> Dict[str, Any]:
        r = self._req("PUT", path, json_body=json_body, timeout_s=timeout_s)
        self._raise_for_status(r)
        return r.json()

    def patch(self, path: str, *, json_body=None, timeout_s=None) -> Dict[str, Any]:
        r = self._req("PATCH", path, json_body=json_body, timeout_s=timeout_s)
        self._raise_for_status(r)
        return r.json()

    def delete(self, path: str, *, timeout_s=None) -> Dict[str, Any]:
        r = self._req("DELETE", path, timeout_s=timeout_s)
        self._raise_for_status(r)
        return r.json()

    def get_bytes(self, path: str, *, params=None, timeout_s=None) -> Tuple[bytes, Dict[str, str]]:
        r = self._req("GET", path, params=params, timeout_s=timeout_s)
        self._raise_for_status(r)
        headers = {k: v for k, v in (r.headers or {}).items()}
        return r.content, headers

    @staticmethod
    def _raise_for_status(r: requests.Response) -> None:
        if 200 <= r.status_code < 300:
            return
        try:
            detail = r.json()
        except Exception:
            detail = r.text
        raise RuntimeError(f"HTTP {r.status_code}: {detail}")


# ----------------------------
# API helpers (existing behavior)
# ----------------------------

def wait_for_snapshot(
    api: ApiClient,
    snapshot_id: str,
    *,
    want_types: Tuple[str, ...] = ("parser", "local_ml"),
    timeout_s: float = 600.0,
    poll_interval_s: float = 2.0,
) -> Tuple[bool, List[Dict[str, Any]]]:
    deadline = time.time() + float(timeout_s)
    last: List[Dict[str, Any]] = []

    while True:
        out = api.get(f"/snapshots/{snapshot_id}/analyses")
        last = list(out.get("analyses") or [])

        by_type = {a.get("analysis_type"): a for a in last if isinstance(a, dict)}
        relevant = [by_type.get(t) for t in want_types]
        if all(x is not None for x in relevant):
            if any((x or {}).get("status") == "failed" for x in relevant):
                return False, last
            if all((x or {}).get("status") == "complete" for x in relevant):
                return True, last

        if time.time() >= deadline:
            return False, last

        time.sleep(float(poll_interval_s))


def upload_zip(
    api: ApiClient,
    *,
    zip_path: Path,
    user_id: Optional[str],
    portfolio_id: Optional[str],
    project_name: Optional[str],
    snapshot_label: Optional[str],
) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    if user_id:
        data["user_id"] = user_id
    if portfolio_id:
        data["portfolio_id"] = portfolio_id
    if project_name:
        data["project_name"] = project_name
    if snapshot_label:
        data["snapshot_label"] = snapshot_label

    with zip_path.open("rb") as fp:
        files = {"file": (zip_path.name, fp, "application/zip")}
        return api.post("/projects/upload", data=data, files=files, timeout_s=300.0)


# ----------------------------
# Command handlers
# ----------------------------

def cmd_health(args: argparse.Namespace, st: DemoState) -> int:
    api = ApiClient(st.api_url)
    out = api.get("/health")
    print(_pretty(out))
    return 0


def cmd_state_show(args: argparse.Namespace, st: DemoState) -> int:
    print(_pretty(asdict(st)))
    return 0


def cmd_state_clear(args: argparse.Namespace, st: DemoState, state_path: Path) -> int:
    st = DemoState(api_url=st.api_url)
    _save_state(state_path, st)
    print(_pretty(asdict(st)))
    return 0


def cmd_consent(args: argparse.Namespace, st: DemoState, state_path: Path) -> int:
    api = ApiClient(st.api_url)
    payload = {
        "user_id": args.user_id,
        "consent_type": args.consent_type,
        "granted": bool(args.granted),
        "version": int(args.version),
    }
    out = api.post("/privacy-consent", json_body=payload)
    st.user_id = str(out.get("user_id") or st.user_id)
    _save_state(state_path, st)
    print(_pretty(out))
    return 0


def cmd_config_get(args: argparse.Namespace, st: DemoState) -> int:
    api = ApiClient(st.api_url)
    user_id = args.user_id or st.user_id
    if not user_id:
        _eprint("missing user_id (pass --user-id or create consent first)")
        return 2
    out = api.get(f"/users/{user_id}/config")
    print(_pretty(out))
    return 0


def cmd_config_put(args: argparse.Namespace, st: DemoState) -> int:
    api = ApiClient(st.api_url)
    user_id = args.user_id or st.user_id
    if not user_id:
        _eprint("missing user_id (pass --user-id or create consent first)")
        return 2
    cfg = json.loads(Path(args.json_file).read_text(encoding="utf-8"))
    out = api.put(f"/users/{user_id}/config", json_body={"config": cfg})
    print(_pretty(out))
    return 0


def cmd_config_patch(args: argparse.Namespace, st: DemoState) -> int:
    api = ApiClient(st.api_url)
    user_id = args.user_id or st.user_id
    if not user_id:
        _eprint("missing user_id (pass --user-id or create consent first)")
        return 2
    patch = json.loads(Path(args.json_file).read_text(encoding="utf-8"))
    out = api.patch(f"/users/{user_id}/config", json_body=patch)
    print(_pretty(out))
    return 0

def cmd_config_set_prefs(args: argparse.Namespace, st: DemoState) -> int:
    api = ApiClient(st.api_url)
    user_id = args.user_id or st.user_id
    if not user_id:
        _eprint("missing user_id (pass --user-id or create consent first)")
        return 2

    # Build the preferences object based on user flags
    # We only include keys the user actually specified in the command
    prefs = {}
    if args.show_summary is not None:
        prefs["show_summary"] = args.show_summary
    if args.show_bullets is not None:
        prefs["show_bullets"] = args.show_bullets
    if args.max_bullets is not None:
        prefs["max_bullets"] = args.max_bullets
    
    # NEW: Toggle for Resume ID and Timestamp
    if args.show_metadata is not None:
        prefs["show_metadata"] = args.show_metadata

    if not prefs:
        _eprint("No preferences specified. Use --show-summary, --show-bullets, --show-metadata, etc.")
        return 2

    # We wrap it in a 'resume_filters' key so it doesn't clutter the top level of config_json
    payload = {"resume_filters": prefs}
    
    # We use PATCH so it merges with existing config instead of wiping it
    out = api.patch(f"/users/{user_id}/config", json_body=payload)
    
    print("✨ Preferences updated in database:")
    print(_pretty(out))
    return 0

def cmd_identity_rules(args: argparse.Namespace, st: DemoState, state_path: Path) -> int:
    api = ApiClient(st.api_url)
    user_id = args.user_id or st.user_id
    if not user_id:
        _eprint("missing user_id (pass --user-id or create consent first)")
        return 2
    payload = {
        "match_emails": args.match_emails or [],
        "match_names": args.match_names or [],
    }
    out = api.post(f"/users/{user_id}/identity/rules", json_body=payload)
    st.user_id = str(user_id)
    _save_state(state_path, st)
    print(_pretty(out))
    return 0


def cmd_identity_autolink(args: argparse.Namespace, st: DemoState) -> int:
    api = ApiClient(st.api_url)
    user_id = args.user_id or st.user_id
    if not user_id:
        _eprint("missing user_id (pass --user-id or create consent first)")
        return 2
    payload = {
        "portfolio_id": args.portfolio_id or st.portfolio_id,
        "dry_run": bool(args.dry_run),
        "persist_project_map": bool(args.persist_project_map),
    }
    out = api.post(f"/users/{user_id}/identity/auto-link", json_body=payload)
    print(_pretty(out))
    return 0


def cmd_upload(args: argparse.Namespace, st: DemoState, state_path: Path) -> int:
    api = ApiClient(st.api_url)

    # Consent: data_access is required before upload (API enforces it).
    # The CLI does not prompt; it expects you to run `consent` explicitly for a clean demo flow.
    zip_path = _require_zip(args.zip)

    res = upload_zip(
        api,
        zip_path=zip_path,
        user_id=args.user_id or st.user_id,
        portfolio_id=args.portfolio_id or st.portfolio_id,
        project_name=args.project_name,
        snapshot_label=args.snapshot_label,
    )

    st.apply_upload_response(res)
    _save_state(state_path, st)

    print(_pretty(res))

    if not args.wait:
        return 0

    created = list((res.get("created") or []))
    for c in created:
        sid = str((c or {}).get("snapshot_id") or "")
        pid = str((c or {}).get("project_id") or "")
        name = (c or {}).get("project_name")
        if not sid:
            continue

        print(f"\nWAIT project_id={pid} snapshot_id={sid} name={name}")
        ok, analyses = wait_for_snapshot(
            api,
            sid,
            want_types=("parser", "local_ml"),
            timeout_s=float(args.timeout),
            poll_interval_s=float(args.poll_interval),
        )
        if not ok:
            print("analysis did not complete successfully")
            print(_pretty({"snapshot_id": sid, "analyses": analyses}))
            continue

        skills = api.get(f"/snapshots/{sid}/skills", params={"limit": int(args.skills_limit)})
        print(_pretty(skills))

    return 0


def cmd_snapshot_analyses(args: argparse.Namespace, st: DemoState) -> int:
    api = ApiClient(st.api_url)
    sid = args.snapshot_id or st.last_snapshot_id
    if not sid:
        _eprint("missing snapshot_id (pass SNAPSHOT_ID or upload first)")
        return 2
    out = api.get(f"/snapshots/{sid}/analyses")
    print(_pretty(out))
    return 0


def cmd_snapshot_skills(args: argparse.Namespace, st: DemoState) -> int:
    api = ApiClient(st.api_url)
    sid = args.snapshot_id or st.last_snapshot_id
    if not sid:
        _eprint("missing snapshot_id (pass SNAPSHOT_ID or upload first)")
        return 2
    out = api.get(f"/snapshots/{sid}/skills", params={"limit": int(args.limit)})
    print(_pretty(out))
    return 0


def cmd_snapshot_external_request(args: argparse.Namespace, st: DemoState) -> int:
    api = ApiClient(st.api_url)
    sid = args.snapshot_id or st.last_snapshot_id
    if not sid:
        _eprint("missing snapshot_id")
        return 2
    out = api.post(f"/snapshots/{sid}/external-analysis")
    print(_pretty(out))
    return 0


def cmd_snapshot_external_get(args: argparse.Namespace, st: DemoState) -> int:
    api = ApiClient(st.api_url)
    sid = args.snapshot_id or st.last_snapshot_id
    if not sid:
        _eprint("missing snapshot_id")
        return 2
    out = api.get(f"/snapshots/{sid}/external-analysis")
    print(_pretty(out))
    return 0


def cmd_projects_list(args: argparse.Namespace, st: DemoState, state_path: Path) -> int:
    api = ApiClient(st.api_url)
    params: Dict[str, Any] = {}
    if args.portfolio_id or st.portfolio_id:
        params["portfolio_id"] = args.portfolio_id or st.portfolio_id
    if args.user_id or st.user_id:
        params["user_id"] = args.user_id or st.user_id

    out = api.get("/projects", params=params)
    st.apply_projects_response(out)
    if out.get("portfolio_id"):
        st.portfolio_id = str(out["portfolio_id"])
    _save_state(state_path, st)

    print(_pretty(out))
    return 0


def cmd_project_report(args: argparse.Namespace, st: DemoState) -> int:
    api = ApiClient(st.api_url)
    pid = args.project_id or st.last_project_id
    if not pid:
        _eprint("missing project_id (pass PROJECT_ID or list projects/upload first)")
        return 2
    out = api.get(f"/projects/{pid}/report", params={"include_raw_analyses": bool(args.include_raw_analyses), "include_framework_detection": bool(args.include_framework_detection)})
    print(_pretty(out))
    return 0

def cmd_project_update(args: argparse.Namespace, st: DemoState) -> int:
    api = ApiClient(st.api_url)
    pid = args.project_id or st.last_project_id
    
    if not pid:
        _eprint("missing project_id")
        return 2

    payload = {"display_name": args.display_name}
    out = api.patch(f"/projects/{pid}", json_body=payload)
    print(_pretty(out))
    return 0

def cmd_project_contributors(args: argparse.Namespace, st: DemoState) -> int:
    api = ApiClient(st.api_url)
    pid = args.project_id or st.last_project_id
    if not pid:
        _eprint("missing project_id")
        return 2
    out = api.get(f"/projects/{pid}/contributors")
    print(_pretty(out))
    return 0


def cmd_project_set_user(args: argparse.Namespace, st: DemoState) -> int:
    api = ApiClient(st.api_url)
    pid = args.project_id or st.last_project_id
    if not pid:
        _eprint("missing project_id")
        return 2
    payload = {
        "is_user": bool(args.is_user),
        "unset_others": bool(args.unset_others),
        "persist_to_config": bool(args.persist_to_config),
    }
    out = api.post(f"/projects/{pid}/contributors/{args.contributor_id}/set-user", json_body=payload)
    print(_pretty(out))
    return 0


def cmd_project_refresh_collab(args: argparse.Namespace, st: DemoState) -> int:
    api = ApiClient(st.api_url)
    pid = args.project_id or st.last_project_id
    if not pid:
        _eprint("missing project_id")
        return 2
    out = api.post(f"/projects/{pid}/refresh-collaboration")
    print(_pretty(out))
    return 0


def cmd_portfolio_get(args: argparse.Namespace, st: DemoState, state_path: Path) -> int:
    api = ApiClient(st.api_url)
    pf = args.portfolio_id or st.portfolio_id
    if not pf:
        _eprint("missing portfolio_id (pass PORTFOLIO_ID or upload first)")
        return 2
    out = api.get(f"/portfolio/{pf}")
    st.portfolio_id = str(out.get("id") or pf)
    _save_state(state_path, st)
    print(_pretty(out))
    return 0


def cmd_portfolio_top(args: argparse.Namespace, st: DemoState) -> int:
    api = ApiClient(st.api_url)
    pf = args.portfolio_id or st.portfolio_id
    if not pf:
        _eprint("missing portfolio_id")
        return 2
    out = api.get(f"/portfolio/{pf}/top-projects", params={"limit": int(args.limit)})
    print(_pretty(out))
    return 0


def cmd_portfolio_generate(args: argparse.Namespace, st: DemoState, state_path: Path) -> int:
    api = ApiClient(st.api_url)
    pf = args.portfolio_id or st.portfolio_id
    if not pf:
        _eprint("missing portfolio_id")
        return 2
    payload = {"portfolio_id": pf, "limit": int(args.limit), "persist": bool(args.persist)}
    out = api.post("/portfolio/generate", json_body=payload)
    st.apply_portfolio_generate(out)
    _save_state(state_path, st)
    print(_pretty(out))
    return 0


def cmd_portfolio_generated(args: argparse.Namespace, st: DemoState) -> int:
    api = ApiClient(st.api_url)
    pf = args.portfolio_id or st.portfolio_id
    if not pf:
        _eprint("missing portfolio_id")
        return 2
    out = api.get(f"/portfolio/{pf}/generated", params={"limit": int(args.limit)})
    print(_pretty(out))
    return 0


def cmd_portfolio_projects_chrono(args: argparse.Namespace, st: DemoState) -> int:
    api = ApiClient(st.api_url)
    pf = args.portfolio_id or st.portfolio_id
    if not pf:
        _eprint("missing portfolio_id")
        return 2
    out = api.get(f"/portfolio/{pf}/projects/chronological", params={"direction": args.direction, "limit": int(args.limit)})
    print(_pretty(out))
    return 0


def cmd_portfolio_skills_chrono(args: argparse.Namespace, st: DemoState) -> int:
    api = ApiClient(st.api_url)
    pf = args.portfolio_id or st.portfolio_id
    if not pf:
        _eprint("missing portfolio_id")
        return 2
    out = api.get(f"/portfolio/{pf}/skills/chronological", params={"direction": args.direction, "limit": int(args.limit)})
    print(_pretty(out))
    return 0


def cmd_resume_generate(args: argparse.Namespace, st: DemoState, state_path: Path) -> int:
    api = ApiClient(st.api_url)
    pid = args.project_id or st.last_project_id
    if not pid:
        _eprint("missing project_id")
        return 2
    payload = {"project_id": pid, "prefer_external_bullets": bool(args.prefer_external_bullets)}
    out = api.post("/resume/generate", json_body=payload)
    st.apply_resume_generate(out)
    _save_state(state_path, st)
    print(_pretty(out))
    return 0


def cmd_resume_get(args: argparse.Namespace, st: DemoState) -> int:
    api = ApiClient(st.api_url)
    rid = args.resume_id or st.last_resume_id
    if not rid:
        _eprint("missing resume_id")
        return 2
    out = api.get(f"/resume/{rid}")
    print(_pretty(out))
    return 0


def cmd_resume_pdf(args: argparse.Namespace, st: DemoState) -> int:
    api = ApiClient(st.api_url)
    rid = args.resume_id or st.last_resume_id
    if not rid:
        _eprint("missing resume_id")
        return 2
    content, headers = api.get_bytes(f"/resume/{rid}/pdf", timeout_s=120.0)

    out_path = Path(args.output).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(content)

    print(_pretty({"resume_id": rid, "bytes": len(content), "output": str(out_path), "headers": headers}))
    return 0


def cmd_delete_snapshot(args: argparse.Namespace, st: DemoState, state_path: Path) -> int:
    api = ApiClient(st.api_url)
    sid = args.snapshot_id or st.last_snapshot_id
    if not sid:
        _eprint("missing snapshot_id")
        return 2
    out = api.delete(f"/snapshots/{sid}")
    st.last_snapshot_id = None if st.last_snapshot_id == sid else st.last_snapshot_id
    _save_state(state_path, st)
    print(_pretty(out))
    return 0


def cmd_delete_analysis(args: argparse.Namespace, st: DemoState) -> int:
    api = ApiClient(st.api_url)
    aid = args.analysis_id
    out = api.delete(f"/analyses/{aid}")
    print(_pretty(out))
    return 0


def cmd_delete_resume(args: argparse.Namespace, st: DemoState, state_path: Path) -> int:
    api = ApiClient(st.api_url)
    rid = args.resume_id or st.last_resume_id
    if not rid:
        _eprint("missing resume_id")
        return 2
    out = api.delete(f"/resume/{rid}")
    st.last_resume_id = None if st.last_resume_id == rid else st.last_resume_id
    _save_state(state_path, st)
    print(_pretty(out))
    return 0


def cmd_delete_showcase(args: argparse.Namespace, st: DemoState, state_path: Path) -> int:
    api = ApiClient(st.api_url)
    sc = args.showcase_id or st.last_showcase_id
    if not sc:
        _eprint("missing showcase_id")
        return 2
    out = api.delete(f"/portfolio/showcases/{sc}")
    st.last_showcase_id = None if st.last_showcase_id == sc else st.last_showcase_id
    _save_state(state_path, st)
    print(_pretty(out))
    return 0

def cmd_project_set_image(args: argparse.Namespace, st: DemoState) -> int:
    api = ApiClient(st.api_url)

    # Determine project_id
    pid = args.project_id or st.last_project_id
    if not pid:
        _eprint("missing project_id (pass --project-id or upload/list first)")
        return 2

    # Validate file path
    file_path = _require_file(args.file)

    # Auto-detect MIME type (simple but effective)
    ext = file_path.suffix.lower()
    mime = "image/png"
    if ext in [".jpg", ".jpeg"]:
        mime = "image/jpeg"
    elif ext == ".gif":
        mime = "image/gif"

    # Upload
    with open(file_path, "rb") as fp:
        files = {"file": (file_path.name, fp, mime)}
        r = api._req("PUT", f"/projects/{pid}/image", files=files)

    # Raise if not 2xx
    api._raise_for_status(r)

    # Parse JSON
    out = r.json()

    # Update state
    st.last_project_id = pid
    st.last_upload = out

    print(_pretty(out))
    return 0



def cmd_demo(args: argparse.Namespace, st: DemoState, state_path: Path) -> int:
    """
    A single-command demo path for marking:
      1) data_access consent
      2) upload zip
      3) wait for parser+local_ml
      4) list projects (ranked)
      5) portfolio top-projects + generate showcases
      6) project report
      7) chronological projects + skills
      8) generate resume + download pdf
    """
    api = ApiClient(st.api_url)

    # 1) Consent
    consent_out = api.post(
        "/privacy-consent",
        json_body={"user_id": args.user_id or st.user_id, "consent_type": "data_access", "granted": True, "version": 1},
    )
    st.user_id = str(consent_out.get("user_id") or st.user_id)
    _save_state(state_path, st)
    print("STEP consent(data_access)=true")
    print(_pretty(consent_out))

    # 2) Upload
    zip_path = _require_zip(args.zip)
    up = upload_zip(
        api,
        zip_path=zip_path,
        user_id=st.user_id,
        portfolio_id=args.portfolio_id or st.portfolio_id,
        project_name=args.project_name,
        snapshot_label=args.snapshot_label,
    )
    st.apply_upload_response(up)
    _save_state(state_path, st)
    print("\nSTEP upload")
    print(_pretty(up))

    # 3) Wait for created snapshots
    created = list((up.get("created") or []))
    for c in created:
        sid = str((c or {}).get("snapshot_id") or "")
        if not sid:
            continue
        ok, analyses = wait_for_snapshot(api, sid, timeout_s=float(args.timeout), poll_interval_s=float(args.poll_interval))
        print(f"\nSTEP wait snapshot={sid} ok={ok}")
        print(_pretty({"snapshot_id": sid, "analyses": analyses}))
        skills = api.get(f"/snapshots/{sid}/skills", params={"limit": 10})
        print("\nSTEP snapshot skills (top 10)")
        print(_pretty(skills))

    # 4) List projects (ranked)
    pr = api.get("/projects", params={"portfolio_id": st.portfolio_id})
    st.apply_projects_response(pr)
    _save_state(state_path, st)
    print("\nSTEP list projects (ranked)")
    print(_pretty(pr))

    # 5) Portfolio top-projects + generate showcases
    pf = st.portfolio_id
    if pf:
        top = api.get(f"/portfolio/{pf}/top-projects", params={"limit": int(args.limit)})
        print("\nSTEP portfolio top-projects")
        print(_pretty(top))

        gen = api.post("/portfolio/generate", json_body={"portfolio_id": pf, "limit": int(args.limit), "persist": True})
        st.apply_portfolio_generate(gen)
        _save_state(state_path, st)
        print("\nSTEP portfolio generate (persist showcases)")
        print(_pretty(gen))

        got = api.get(f"/portfolio/{pf}/generated", params={"limit": 50})
        print("\nSTEP portfolio generated artifacts")
        print(_pretty(got))

        chrono_proj = api.get(f"/portfolio/{pf}/projects/chronological", params={"direction": "asc", "limit": 200})
        print("\nSTEP portfolio projects chronological")
        print(_pretty(chrono_proj))

        chrono_sk = api.get(f"/portfolio/{pf}/skills/chronological", params={"direction": "asc", "limit": 200})
        print("\nSTEP portfolio skills chronological")
        print(_pretty(chrono_sk))

    # 6) Project report (first project)
    pid = st.last_project_id
    if pid:
        rep = api.get(f"/projects/{pid}/report", params={"include_raw_analyses": False, "include_framework_detection": True})
        print("\nSTEP project report")
        print(_pretty(rep))

    # 7) Resume generate + pdf
    if pid:
        rgen = api.post("/resume/generate", json_body={"project_id": pid, "prefer_external_bullets": True})
        st.apply_resume_generate(rgen)
        _save_state(state_path, st)
        print("\nSTEP resume generate")
        print(_pretty(rgen))

        rid = st.last_resume_id
        if rid:
            out_path = Path(args.resume_pdf_out).expanduser().resolve()
            content, headers = api.get_bytes(f"/resume/{rid}/pdf", timeout_s=120.0)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(content)
            print("\nSTEP resume pdf saved")
            print(_pretty({"resume_id": rid, "output": str(out_path), "bytes": len(content), "headers": headers}))

    return 0


# ----------------------------
# Argparse wiring
# ----------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="artifact-miner", description="Artifact Miner Demo CLI (API client)")
    p.add_argument("--api-url", default=None, help=f"API base URL (default: ARTIFACT_MINER_API_URL or {DEFAULT_API_URL})")
    p.add_argument("--state", default=DEFAULT_STATE_PATH, help=f"State file for demo convenience (default: {DEFAULT_STATE_PATH})")

    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("health", help="GET /health")
    sp.set_defaults(_handler="health")

    sp = sub.add_parser("state", help="Show or clear local demo state")
    ssub = sp.add_subparsers(dest="state_cmd", required=True)
    sp1 = ssub.add_parser("show", help="Print state JSON")
    sp1.set_defaults(_handler="state_show")
    sp2 = ssub.add_parser("clear", help="Reset state (keeps api_url)")
    sp2.set_defaults(_handler="state_clear")

    sp = sub.add_parser("consent", help="POST /privacy-consent (grant/revoke consents)")
    sp.add_argument("consent_type", choices=["data_access", "external_services"])
    sp.add_argument("granted", type=_bool_flag, help="true/false")
    sp.add_argument("--user-id", default=None, help="Existing user_id; omit to create new user_id")
    sp.add_argument("--version", type=int, default=1)
    sp.set_defaults(_handler="consent")

    sp = sub.add_parser("config", help="User config endpoints")
    csub = sp.add_subparsers(dest="config_cmd", required=True)

    sp1 = csub.add_parser("get", help="GET /users/{user_id}/config")
    sp1.add_argument("--user-id", default=None)
    sp1.set_defaults(_handler="config_get")

    sp2 = csub.add_parser("put", help="PUT /users/{user_id}/config (replace)")
    sp2.add_argument("json_file", help="Path to JSON file containing full config object")
    sp2.add_argument("--user-id", default=None)
    sp2.set_defaults(_handler="config_put")

    sp3 = csub.add_parser("patch", help="PATCH /users/{user_id}/config (merge)")
    sp3.add_argument("json_file", help="Path to JSON file containing patch object")
    sp3.add_argument("--user-id", default=None)
    sp3.set_defaults(_handler="config_patch")

    sp_prefs = csub.add_parser("set-preferences", help="Toggle resume visibility settings")
    sp_prefs.add_argument("--user-id", default=None)
    sp_prefs.add_argument("--show-summary", type=_bool_flag, help="Toggle project summary (on/off)")
    sp_prefs.add_argument("--show-metadata", type=_bool_flag, help="Toggle metadata (on/off)")
    sp_prefs.add_argument("--show-bullets", type=_bool_flag, help="Toggle resume bullets (on/off)")
    sp_prefs.add_argument("--max-bullets", type=int, help="Limit number of bullets shown")
    sp_prefs.set_defaults(_handler="config_set_prefs")

    sp = sub.add_parser("identity", help="Identity mapping utilities (user contribution linking)")
    isub = sp.add_subparsers(dest="identity_cmd", required=True)

    sp1 = isub.add_parser("rules", help="POST /users/{user_id}/identity/rules")
    sp1.add_argument("--user-id", default=None)
    sp1.add_argument("--match-emails", nargs="*", default=[], help="List of emails to treat as 'the user'")
    sp1.add_argument("--match-names", nargs="*", default=[], help="List of canonical names to treat as 'the user'")
    sp1.set_defaults(_handler="identity_rules")

    sp2 = isub.add_parser("auto-link", help="POST /users/{user_id}/identity/auto-link")
    sp2.add_argument("--user-id", default=None)
    sp2.add_argument("--portfolio-id", default=None)
    sp2.add_argument("--dry-run", action="store_true", help="Only compute; do not write project_contributors.is_user")
    sp2.add_argument("--persist-project-map", action="store_true", help="Persist mapping into user_config (recommended)")
    sp2.set_defaults(_handler="identity_autolink")

    sp = sub.add_parser("upload", help="POST /projects/upload (+ optional wait)")
    sp.add_argument("zip", help="Path to .zip", type=str)
    sp.add_argument("--user-id", default=None)
    sp.add_argument("--portfolio-id", default=None)
    sp.add_argument("--project-name", default=None)
    sp.add_argument("--snapshot-label", default=None)
    sp.add_argument("--wait", action="store_true", help="Poll until parser+local_ml complete for created snapshots")
    sp.add_argument("--timeout", type=float, default=600.0)
    sp.add_argument("--poll-interval", type=float, default=2.0)
    sp.add_argument("--skills-limit", type=int, default=20)
    sp.set_defaults(_handler="upload")

    sp = sub.add_parser("snapshot", help="Snapshot operations")
    ssub = sp.add_subparsers(dest="snapshot_cmd", required=True)

    sp1 = ssub.add_parser("analyses", help="GET /snapshots/{id}/analyses")
    sp1.add_argument("snapshot_id", nargs="?", default=None)
    sp1.set_defaults(_handler="snapshot_analyses")

    sp2 = ssub.add_parser("skills", help="GET /snapshots/{id}/skills")
    sp2.add_argument("snapshot_id", nargs="?", default=None)
    sp2.add_argument("--limit", type=int, default=20)
    sp2.set_defaults(_handler="snapshot_skills")

    sp3 = ssub.add_parser("external-request", help="POST /snapshots/{id}/external-analysis")
    sp3.add_argument("snapshot_id", nargs="?", default=None)
    sp3.set_defaults(_handler="snapshot_external_request")

    sp4 = ssub.add_parser("external-get", help="GET /snapshots/{id}/external-analysis")
    sp4.add_argument("snapshot_id", nargs="?", default=None)
    sp4.set_defaults(_handler="snapshot_external_get")

    sp = sub.add_parser("projects", help="Project queries")
    psub = sp.add_subparsers(dest="projects_cmd", required=True)

    sp_upd = psub.add_parser("update", help="Update project details")
    sp_upd.add_argument("project_id", nargs="?", default=None)
    sp_upd.add_argument("--display-name", required=True, help="New name for resume")
    sp_upd.set_defaults(_handler="project_update")

    sp1 = psub.add_parser("list", help="GET /projects (ranked)")
    sp1.add_argument("--portfolio-id", default=None)
    sp1.add_argument("--user-id", default=None)
    sp1.set_defaults(_handler="projects_list")

    sp2 = psub.add_parser("report", help="GET /projects/{id}/report")
    sp2.add_argument("project_id", nargs="?", default=None)
    sp2.add_argument("--include-raw-analyses", action="store_true")
    sp2.add_argument("--include-framework-detection", type=_bool_flag, default=True)
    sp2.set_defaults(_handler="project_report")

    sp3 = psub.add_parser("contributors", help="GET /projects/{id}/contributors")
    sp3.add_argument("project_id", nargs="?", default=None)
    sp3.set_defaults(_handler="project_contributors")

    sp4 = psub.add_parser("set-user", help="POST /projects/{id}/contributors/{contributor_id}/set-user")
    sp4.add_argument("project_id", nargs="?", default=None)
    sp4.add_argument("contributor_id")
    sp4.add_argument("--is-user", type=_bool_flag, default=True)
    sp4.add_argument("--unset-others", type=_bool_flag, default=True)
    sp4.add_argument("--persist-to-config", type=_bool_flag, default=True)
    sp4.set_defaults(_handler="project_set_user")

    sp5 = psub.add_parser("refresh-collaboration", help="POST /projects/{id}/refresh-collaboration")
    sp5.add_argument("project_id", nargs="?", default=None)
    sp5.set_defaults(_handler="project_refresh_collab")

    sp = sub.add_parser("portfolio", help="Portfolio endpoints")
    pfsub = sp.add_subparsers(dest="portfolio_cmd", required=True)

    sp1 = pfsub.add_parser("get", help="GET /portfolio/{id}")
    sp1.add_argument("portfolio_id", nargs="?", default=None)
    sp1.set_defaults(_handler="portfolio_get")

    sp2 = pfsub.add_parser("top", help="GET /portfolio/{id}/top-projects")
    sp2.add_argument("portfolio_id", nargs="?", default=None)
    sp2.add_argument("--limit", type=int, default=5)
    sp2.set_defaults(_handler="portfolio_top")

    sp3 = pfsub.add_parser("generate", help="POST /portfolio/generate")
    sp3.add_argument("portfolio_id", nargs="?", default=None)
    sp3.add_argument("--limit", type=int, default=5)
    sp3.add_argument("--persist", type=_bool_flag, default=True)
    sp3.set_defaults(_handler="portfolio_generate")

    sp4 = pfsub.add_parser("generated", help="GET /portfolio/{id}/generated")
    sp4.add_argument("portfolio_id", nargs="?", default=None)
    sp4.add_argument("--limit", type=int, default=50)
    sp4.set_defaults(_handler="portfolio_generated")

    sp5 = pfsub.add_parser("projects-chronological", help="GET /portfolio/{id}/projects/chronological")
    sp5.add_argument("portfolio_id", nargs="?", default=None)
    sp5.add_argument("--direction", choices=["asc", "desc"], default="asc")
    sp5.add_argument("--limit", type=int, default=200)
    sp5.set_defaults(_handler="portfolio_projects_chrono")

    sp6 = pfsub.add_parser("skills-chronological", help="GET /portfolio/{id}/skills/chronological")
    sp6.add_argument("portfolio_id", nargs="?", default=None)
    sp6.add_argument("--direction", choices=["asc", "desc"], default="asc")
    sp6.add_argument("--limit", type=int, default=200)
    sp6.set_defaults(_handler="portfolio_skills_chrono")

    sp = sub.add_parser("resume", help="Resume endpoints")
    rsub = sp.add_subparsers(dest="resume_cmd", required=True)

    sp1 = rsub.add_parser("generate", help="POST /resume/generate")
    sp1.add_argument("project_id", nargs="?", default=None)
    sp1.add_argument("--prefer-external-bullets", type=_bool_flag, default=True)
    sp1.set_defaults(_handler="resume_generate")

    sp2 = rsub.add_parser("get", help="GET /resume/{id}")
    sp2.add_argument("resume_id", nargs="?", default=None)
    sp2.set_defaults(_handler="resume_get")

    sp3 = rsub.add_parser("pdf", help="GET /resume/{id}/pdf (download)")
    sp3.add_argument("resume_id", nargs="?", default=None)
    sp3.add_argument("-o", "--output", default="resume.pdf")
    sp3.set_defaults(_handler="resume_pdf")

    sp = sub.add_parser("delete", help="Deletion endpoints (safe deletion)")
    dsub = sp.add_subparsers(dest="delete_cmd", required=True)

    sp1 = dsub.add_parser("snapshot", help="DELETE /snapshots/{id}")
    sp1.add_argument("snapshot_id", nargs="?", default=None)
    sp1.set_defaults(_handler="delete_snapshot")

    sp2 = dsub.add_parser("analysis", help="DELETE /analyses/{id}")
    sp2.add_argument("analysis_id")
    sp2.set_defaults(_handler="delete_analysis")

    sp3 = dsub.add_parser("resume", help="DELETE /resume/{id}")
    sp3.add_argument("resume_id", nargs="?", default=None)
    sp3.set_defaults(_handler="delete_resume")

    sp4 = dsub.add_parser("showcase", help="DELETE /portfolio/showcases/{id}")
    sp4.add_argument("showcase_id", nargs="?", default=None)
    sp4.set_defaults(_handler="delete_showcase")

    sp = sub.add_parser("project-set-image", help="Upload a thumbnail image for a project")
    sp.add_argument("file", help="Path to the image file (PNG recommended)")
    sp.add_argument("--project-id", default=None, help="Project ID (defaults to last_project_id)")
    sp.set_defaults(_handler="project_set_image")



    sp = sub.add_parser("demo", help="One-command end-to-end marking flow (consent -> upload -> outputs -> pdf)")
    sp.add_argument("zip", help="Path to .zip containing one or more projects")
    sp.add_argument("--user-id", default=None)
    sp.add_argument("--portfolio-id", default=None)
    sp.add_argument("--project-name", default=None)
    sp.add_argument("--snapshot-label", default="demo")
    sp.add_argument("--timeout", type=float, default=600.0)
    sp.add_argument("--poll-interval", type=float, default=2.0)
    sp.add_argument("--limit", type=int, default=5)
    sp.add_argument("--resume-pdf-out", default="demo_resume.pdf")
    sp.set_defaults(_handler="demo")

    return p


def main(argv: Optional[List[str]] = None) -> int:
    p = build_parser()
    args = p.parse_args(argv)

    state_path = Path(args.state).expanduser().resolve()
    st = _load_state(state_path)
    st.api_url = _api_url(args)

    try:
        h = getattr(args, "_handler")
        if h == "health":
            rc = cmd_health(args, st)
        elif h == "state_show":
            rc = cmd_state_show(args, st)
        elif h == "state_clear":
            rc = cmd_state_clear(args, st, state_path)
        elif h == "consent":
            rc = cmd_consent(args, st, state_path)
        elif h == "config_get":
            rc = cmd_config_get(args, st)
        elif h == "config_put":
            rc = cmd_config_put(args, st)
        elif h == "config_patch":
            rc = cmd_config_patch(args, st)
        elif h == "config_set_prefs":
            rc = cmd_config_set_prefs(args, st)
        elif h == "identity_rules":
            rc = cmd_identity_rules(args, st, state_path)
        elif h == "identity_autolink":
            rc = cmd_identity_autolink(args, st)
        elif h == "upload":
            rc = cmd_upload(args, st, state_path)
        elif h == "snapshot_analyses":
            rc = cmd_snapshot_analyses(args, st)
        elif h == "snapshot_skills":
            rc = cmd_snapshot_skills(args, st)
        elif h == "snapshot_external_request":
            rc = cmd_snapshot_external_request(args, st)
        elif h == "snapshot_external_get":
            rc = cmd_snapshot_external_get(args, st)
        elif h == "projects_list":
            rc = cmd_projects_list(args, st, state_path)
        elif h == "project_report":
            rc = cmd_project_report(args, st)
        elif h == "project_contributors":
            rc = cmd_project_contributors(args, st)
        elif h == "project_set_user":
            rc = cmd_project_set_user(args, st)
        elif h == "project_refresh_collab":
            rc = cmd_project_refresh_collab(args, st)
        elif h == "portfolio_get":
            rc = cmd_portfolio_get(args, st, state_path)
        elif h == "project_update":
            rc = cmd_project_update(args, st)
        elif h == "portfolio_top":
            rc = cmd_portfolio_top(args, st)
        elif h == "portfolio_generate":
            rc = cmd_portfolio_generate(args, st, state_path)
        elif h == "portfolio_generated":
            rc = cmd_portfolio_generated(args, st)
        elif h == "portfolio_projects_chrono":
            rc = cmd_portfolio_projects_chrono(args, st)
        elif h == "portfolio_skills_chrono":
            rc = cmd_portfolio_skills_chrono(args, st)
        elif h == "resume_generate":
            rc = cmd_resume_generate(args, st, state_path)
        elif h == "resume_get":
            rc = cmd_resume_get(args, st)
        elif h == "resume_pdf":
            rc = cmd_resume_pdf(args, st)
        elif h == "delete_snapshot":
            rc = cmd_delete_snapshot(args, st, state_path)
        elif h == "delete_analysis":
            rc = cmd_delete_analysis(args, st)
        elif h == "delete_resume":
            rc = cmd_delete_resume(args, st, state_path)
        elif h == "delete_showcase":
            rc = cmd_delete_showcase(args, st, state_path)
        elif h == "project_set_image":
            rc = cmd_project_set_image(args, st)
        elif h == "demo":
            rc = cmd_demo(args, st, state_path)
        else:
            _eprint(f"unknown handler: {h}")
            rc = 2

        return int(rc)

    except RuntimeError as e:
        _eprint(str(e))
        return 1
    except requests.RequestException as e:
        _eprint(f"request error: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
