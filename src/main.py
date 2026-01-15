from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


def _prompt_yes_no(prompt: str) -> bool:
    while True:
        s = input(f"{prompt} [y/n]: ").strip().lower()
        if s in ("y", "yes"):
            return True
        if s in ("n", "no"):
            return False


def _api_url(args: argparse.Namespace) -> str:
    return (args.api_url or os.environ.get("ARTIFACT_MINER_API_URL") or "http://localhost:5001").rstrip("/")


def _post_consent(api: str, *, user_id: Optional[str], consent_type: str, granted: bool, version: int = 1) -> str:
    payload = {
        "user_id": user_id,
        "consent_type": consent_type,
        "granted": granted,
        "version": version,
    }
    r = requests.post(f"{api}/privacy-consent", json=payload, timeout=30)
    r.raise_for_status()
    out = r.json()
    return str(out["user_id"])


def _upload_zip(
    api: str,
    *,
    zip_path: Path,
    user_id: Optional[str],
    portfolio_id: Optional[str],
    project_name: Optional[str],
    snapshot_label: Optional[str],
) -> Dict[str, Any]:
    data = {}
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
        r = requests.post(f"{api}/projects/upload", data=data, files=files, timeout=300)
        r.raise_for_status()
        return r.json()


def _get_snapshot_analyses(api: str, snapshot_id: str) -> List[Dict[str, Any]]:
    r = requests.get(f"{api}/snapshots/{snapshot_id}/analyses", timeout=30)
    r.raise_for_status()
    return list(r.json().get("analyses", []))


def _get_snapshot_skills(api: str, snapshot_id: str, limit: int) -> List[Dict[str, Any]]:
    r = requests.get(f"{api}/snapshots/{snapshot_id}/skills", params={"limit": limit}, timeout=30)
    r.raise_for_status()
    return list(r.json().get("skills", []))


def _wait_for_snapshot(
    api: str,
    snapshot_id: str,
    *,
    want_types: Tuple[str, ...] = ("parser", "local_ml"),
    timeout_s: float = 600.0,
    poll_interval_s: float = 2.0,
) -> Tuple[bool, List[Dict[str, Any]]]:
    deadline = time.time() + timeout_s
    last = []

    while True:
        last = _get_snapshot_analyses(api, snapshot_id)

        by_type = {a["analysis_type"]: a for a in last}
        relevant = [by_type.get(t) for t in want_types]
        if all(r is not None for r in relevant):
            # If any failed, stop.
            if any(r["status"] == "failed" for r in relevant if r is not None):
                return False, last
            # If all complete, stop.
            if all(r["status"] == "complete" for r in relevant if r is not None):
                return True, last

        if time.time() >= deadline:
            return False, last

        time.sleep(poll_interval_s)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="artifact-miner", description="Artifact Miner CLI (API client)")
    p.add_argument("zip", nargs="?", help="Path to a .zip file to upload")
    p.add_argument("--api-url", default=None, help="API base URL (default: ARTIFACT_MINER_API_URL or http://localhost:5001)")
    p.add_argument("--user-id", default=None, help="Existing user_id (UUID). If omitted, a new user is created on consent.")
    p.add_argument("--portfolio-id", default=None, help="Target portfolio_id (UUID). If omitted, API uses/creates default portfolio.")
    p.add_argument("--project-name", default=None, help="Force single project name for the upload.")
    p.add_argument("--snapshot-label", default=None, help="Optional snapshot label.")

    p.add_argument("--data-consent", action="store_true", help="Grant data_access consent without prompting.")
    p.add_argument("--no-data-consent", action="store_true", help="Do not grant data_access consent (will exit).")

    p.add_argument("--external-consent", action="store_true", help="Grant external_services consent without prompting.")
    p.add_argument("--wait", action="store_true", help="Poll until parser + local_ml complete for created snapshots.")
    p.add_argument("--timeout", type=float, default=600.0, help="Wait timeout in seconds (default 600).")
    p.add_argument("--poll-interval", type=float, default=2.0, help="Polling interval in seconds (default 2).")
    p.add_argument("--skills-limit", type=int, default=20, help="Skills to print per snapshot when --wait completes (default 20).")

    args = p.parse_args(argv)

    api = _api_url(args)

    if not args.zip:
        print("Missing ZIP path.", file=sys.stderr)
        return 2

    zip_path = Path(args.zip).expanduser().resolve()
    if not zip_path.exists():
        print(f"File not found: {zip_path}", file=sys.stderr)
        return 2
    if zip_path.suffix.lower() != ".zip":
        print("Expected a .zip file.", file=sys.stderr)
        return 2

    # Consent: data_access is required before upload (API enforces it).
    if args.no_data_consent:
        print("data_access consent not granted; exiting.", file=sys.stderr)
        return 1

    user_id = args.user_id

    if args.data_consent:
        user_id = _post_consent(api, user_id=user_id, consent_type="data_access", granted=True)
    else:
        ok = _prompt_yes_no("Grant consent for data access (required to proceed)?")
        if not ok:
            print("data_access consent not granted; exiting.", file=sys.stderr)
            return 1
        user_id = _post_consent(api, user_id=user_id, consent_type="data_access", granted=True)

    # Optional external services consent (not currently used by worker unless you later enqueue external_llm).
    if args.external_consent:
        user_id = _post_consent(api, user_id=user_id, consent_type="external_services", granted=True)
    else:
        # Do not prompt by default. Only prompt if user explicitly asked by providing the flag.
        pass

    # Upload
    res = _upload_zip(
        api,
        zip_path=zip_path,
        user_id=user_id,
        portfolio_id=args.portfolio_id,
        project_name=args.project_name,
        snapshot_label=args.snapshot_label,
    )

    created = res.get("created", [])
    skipped = res.get("skipped", [])

    print(f"API: {api}")
    print(f"user_id: {res.get('user_id')}")
    print(f"portfolio_id: {res.get('portfolio_id')}")
    print(f"created: {len(created)}")
    for c in created:
        print(f"  project_id={c.get('project_id')} snapshot_id={c.get('snapshot_id')} name={c.get('project_name')} files={c.get('file_count')}")

    print(f"skipped: {len(skipped)}")
    for s in skipped:
        print(f"  project_id={s.get('project_id')} snapshot_id={s.get('snapshot_id')} name={s.get('project_name')}")

    if not args.wait:
        return 0

    # Wait for parser + local_ml on created snapshots
    for c in created:
        sid = str(c.get("snapshot_id"))
        pid = str(c.get("project_id"))
        name = c.get("project_name")

        print(f"waiting: project={pid} snapshot={sid} name={name}")
        ok, analyses = _wait_for_snapshot(
            api,
            sid,
            want_types=("parser", "local_ml"),
            timeout_s=args.timeout,
            poll_interval_s=args.poll_interval,
        )

        if not ok:
            # Print statuses and any error fields.
            print("analysis did not complete successfully:")
            for a in analyses:
                if a.get("analysis_type") in ("parser", "local_ml", "git_metrics"):
                    err = a.get("error")
                    if err:
                        print(f"  {a['analysis_type']}: {a['status']} error={err}")
                    else:
                        print(f"  {a['analysis_type']}: {a['status']}")
            continue

        # Print skills summary for this snapshot
        skills = _get_snapshot_skills(api, sid, limit=args.skills_limit)
        print(f"skills: snapshot={sid} (top {args.skills_limit})")
        for row in skills:
            # confidence is max_prob (as stored by local_ml executor)
            print(f"  {row.get('skill_name')}  confidence={row.get('confidence')}  category={row.get('category')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
