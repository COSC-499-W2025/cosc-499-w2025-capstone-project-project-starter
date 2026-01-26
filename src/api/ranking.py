from __future__ import annotations

from typing import Any, Dict, List, Optional


def _as_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def _as_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return int(default)


def normalize_ranking_config(cfg: Any) -> Dict[str, Any]:
    """Normalize ranking config (typically from user_config.config_json['ranking'])."""
    if not isinstance(cfg, dict):
        cfg = {}

    mode = str(cfg.get("mode") or "auto").strip().lower()
    if mode not in {"auto", "weighted", "manual"}:
        mode = "auto"

    weights = cfg.get("weights")
    if not isinstance(weights, dict):
        weights = {}

    # Keep defaults aligned with the existing behavior.
    w_user = _as_float(weights.get("user_commits"), 1.0)
    w_other = _as_float(weights.get("other_commits"), 0.10)
    w_contrib = _as_float(weights.get("contributor_count"), 0.0)

    allow_no_user_score = bool(cfg.get("allow_no_user_score", False))

    manual_order = cfg.get("manual_project_order") or cfg.get("manual_order") or []
    if not isinstance(manual_order, list):
        manual_order = []
    manual_order = [str(x) for x in manual_order if str(x).strip()]

    manual_ranks = cfg.get("manual_ranks") or {}
    if not isinstance(manual_ranks, dict):
        manual_ranks = {}
    # project_id -> numeric rank (lower is better)
    mr: Dict[str, float] = {}
    for k, v in manual_ranks.items():
        ks = str(k).strip()
        if not ks:
            continue
        try:
            mr[ks] = float(v)
        except Exception:
            continue

    return {
        "mode": mode,
        "weights": {
            "user_commits": w_user,
            "other_commits": w_other,
            "contributor_count": w_contrib,
        },
        "allow_no_user_score": allow_no_user_score,
        "manual_project_order": manual_order,
        "manual_ranks": mr,
    }


def compute_rank_score(
    *,
    user_commits: Optional[int],
    total_commits: int,
    contributor_count: int,
    ranking_cfg: Dict[str, Any],
) -> Optional[float]:
    cfg = normalize_ranking_config(ranking_cfg)
    mode = cfg["mode"]

    uc = None if user_commits is None else _as_int(user_commits, 0)
    tc = _as_int(total_commits, 0)
    cc = _as_int(contributor_count, 0)
    other = max(0, tc - (uc or 0))

    # Default semantics: scores are only meaningful when user_commits > 0.
    if (uc is None or uc <= 0) and not bool(cfg.get("allow_no_user_score")):
        return None

    if mode == "weighted":
        w = cfg["weights"]
        return float(w["user_commits"]) * float(uc or 0) + float(w["other_commits"]) * float(other) + float(
            w["contributor_count"]
        ) * float(cc)

    # auto/manual both compute the same default score for display.
    return float(uc or 0) + 0.10 * float(other)


def sort_projects(projects: List[Dict[str, Any]], ranking_cfg: Any) -> List[Dict[str, Any]]:
    """Returns a new list sorted according to ranking config.

    Expected project shape (minimum):
      {"id": str, "created_at": Any, "metrics": {"rank_score": Optional[float], "total_commits": int}}
    """
    cfg = normalize_ranking_config(ranking_cfg)

    # Precompute manual indices / ranks.
    order_index = {pid: i for i, pid in enumerate(cfg.get("manual_project_order") or [])}
    manual_ranks = cfg.get("manual_ranks") or {}

    def auto_key(p: Dict[str, Any]):
        m = p.get("metrics") or {}
        rs = m.get("rank_score")
        tc = _as_int(m.get("total_commits"), 0)
        ca = p.get("created_at")
        # Keep stable fallback ordering.
        return (
            1 if rs is None else 0,
            0.0 if rs is None else -float(rs),
            -int(tc),
            str(ca or ""),
            str(p.get("id") or ""),
        )

    def key(p: Dict[str, Any]):
        pid = str(p.get("id") or "")

        # manual_ranks takes precedence (explicit numeric ordering).
        if pid in manual_ranks:
            return (0, float(manual_ranks[pid]), pid)

        if cfg["mode"] == "manual" and pid in order_index:
            return (1, int(order_index[pid]), pid)

        # Remaining projects fall back to computed ranking.
        return (2,) + auto_key(p)

    return sorted(list(projects), key=key)
