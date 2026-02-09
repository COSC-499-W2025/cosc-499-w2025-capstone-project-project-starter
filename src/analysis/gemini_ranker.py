"""
Gemini-powered Project Ranking Module

Uses Gemini LLM to comparatively rank all of a user's projects.
Complements the formula-based ranking in project_ranking.py with AI judgement.
"""

import json
import re
import time
from typing import Any, Dict, List, Optional

from external_services.gemini_client import generate_text
from config.db_config import get_connection
from parsing.file_contents_manager import get_file_contents_by_upload_id
from account.user_manager import AuthManager

MAX_PROJECTS = 20
MAX_FILES_PER_PROJECT = 5
MAX_CHARS_PER_FILE = 1500
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 2


class GeminiRanker:
    """Uses Gemini AI to comparatively rank a user's projects."""

    def rank_projects(self, projects_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Rank projects using Gemini. Each dict needs project_id, filename,
        and file_snippets (list of {path, content}).
        Returns dict with success, rankings (best-first), reasoning.
        """
        if not projects_data:
            return {"success": False, "error": "No projects provided", "rankings": []}

        if len(projects_data) == 1:
            p = projects_data[0]
            return {
                "success": True,
                "rankings": [{
                    "project_id": p["project_id"], "filename": p["filename"],
                    "score": 100, "strengths": [], "weaknesses": [],
                    "one_line_summary": "Only project — ranked #1 by default.",
                }],
                "reasoning": "Only one project provided.",
            }

        prompt = self._build_ranking_prompt(projects_data)
        try:
            response = self._call_with_retry(prompt)
            result = self._parse_response(response, projects_data)
            result["success"] = True
            return result
        except Exception as e:
            msg = str(e)
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                msg = "API rate limit reached. Please wait a minute and try again."
            return {"success": False, "error": f"Gemini ranking failed: {msg}", "rankings": []}

    def gather_projects_data(self, user_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Gather lightweight project data for all of a user's projects."""
        if user_name is None:
            user_name = AuthManager.get_current_username()
            if not user_name:
                return []
        try:
            with get_connection() as conn, conn.cursor() as cur:
                cur.execute(
                    "SELECT id, filename, metadata FROM uploaded_files WHERE user_name = %s ORDER BY filename",
                    (user_name,),
                )
                rows = cur.fetchall()
        except Exception as e:
            print(f"Error fetching projects: {e}")
            return []

        results: List[Dict[str, Any]] = []
        for project_id, filename, metadata_raw in rows[:MAX_PROJECTS]:
            languages, file_count = [], 0
            if metadata_raw:
                try:
                    meta = json.loads(metadata_raw) if isinstance(metadata_raw, str) else metadata_raw
                    file_count = len([f for f in meta.get("files", []) if not f.endswith("/")])
                    languages = meta.get("languages", [])
                except (json.JSONDecodeError, TypeError):
                    pass
            results.append({
                "project_id": project_id, "filename": filename,
                "file_count": file_count, "languages": languages,
                "file_snippets": self._get_snippets(project_id),
            })
        return results

    # -- internal helpers --------------------------------------------------

    def _get_snippets(self, project_id: int) -> List[Dict[str, str]]:
        code_exts = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".c", ".go", ".rs", ".rb", ".php"}
        priority_names = {"main", "app", "index", "server", "api"}
        try:
            all_files = get_file_contents_by_upload_id(project_id)
        except Exception:
            return []
        if not all_files:
            return []

        candidates = []
        for f in all_files:
            if f.get("is_binary"):
                continue
            ext = (f.get("file_extension") or "").lower()
            if ext not in code_exts:
                continue
            content = f.get("file_content", "")
            if isinstance(content, (bytes, memoryview)):
                try:
                    content = bytes(content).decode("utf-8", errors="ignore")
                except Exception:
                    continue
            if not isinstance(content, str) or len(content.strip()) < 50:
                continue
            name_lower = (f.get("file_name") or "").lower()
            pri = sum(1 for p in priority_names if p in name_lower)
            candidates.append({"path": f.get("file_path", ""), "content": content, "priority": pri})

        candidates.sort(key=lambda x: (-x["priority"], len(x["content"])))
        return [{"path": c["path"], "content": c["content"][:MAX_CHARS_PER_FILE]} for c in candidates[:MAX_FILES_PER_PROJECT]]

    def _build_ranking_prompt(self, projects_data: List[Dict[str, Any]]) -> str:
        sections = []
        for i, proj in enumerate(projects_data, 1):
            langs = ", ".join(proj.get("languages", [])) or "Unknown"
            code = ""
            for s in proj.get("file_snippets", []):
                code += f"\n--- {s['path']} ---\n{s['content']}\n"
            sections.append(
                f"### Project {i}: {proj['filename']}\n"
                f"- Languages: {langs}\n- Files: {proj.get('file_count', 0)}\n"
                f"- Code samples:{code if code else ' (none)'}\n"
            )

        return (
            f"Compare and rank these {len(projects_data)} projects from best to worst.\n\n"
            + "\n".join(sections)
            + "\nEvaluate on: code quality, complexity, skills demonstrated, best practices.\n"
            "Return JSON:\n"
            '{"rankings": [{"project_index": <1-based>, "score": <1-100 int>, '
            '"strengths": [...], "weaknesses": [...], '
            '"one_line_summary": "..."}], '
            '"overall_reasoning": "..."}\n'
            "Order best-first. Every project exactly once. Unique scores."
        )

    def _call_with_retry(self, prompt: str) -> str:
        last_err = None
        for attempt in range(MAX_RETRIES):
            try:
                return generate_text(
                    prompt,
                    system_instruction=(
                        "You are an expert software engineering evaluator. "
                        "Rank coding projects objectively. Respond ONLY with valid JSON."
                    ),
                    temperature=0.3,
                )
            except Exception as e:
                last_err = e
                if ("429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)) and attempt < MAX_RETRIES - 1:
                    time.sleep(INITIAL_RETRY_DELAY * (2 ** attempt))
                    continue
                raise
        raise last_err

    def _parse_response(self, response: str, projects_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        parsed = self._extract_json(response)
        if not parsed or not isinstance(parsed.get("rankings"), list):
            return self._fallback(response, projects_data)

        idx_map = {i + 1: p for i, p in enumerate(projects_data)}
        rankings, seen = [], set()
        for entry in parsed["rankings"]:
            idx = entry.get("project_index")
            if idx not in idx_map:
                continue
            proj = idx_map[idx]
            seen.add(proj["project_id"])
            rankings.append({
                "project_id": proj["project_id"], "filename": proj["filename"],
                "score": int(entry.get("score", 0)),
                "strengths": entry.get("strengths", []),
                "weaknesses": entry.get("weaknesses", []),
                "one_line_summary": entry.get("one_line_summary", ""),
            })

        for proj in projects_data:
            if proj["project_id"] not in seen:
                rankings.append({
                    "project_id": proj["project_id"], "filename": proj["filename"],
                    "score": 0, "strengths": [], "weaknesses": ["Not evaluated"],
                    "one_line_summary": "",
                })

        return {"rankings": rankings, "reasoning": parsed.get("overall_reasoning", "")}

    @staticmethod
    def _extract_json(text: str) -> Optional[Dict[str, Any]]:
        try:
            m = re.search(r"\{[\s\S]*\}", text)
            if m:
                return json.loads(m.group())
        except json.JSONDecodeError:
            pass
        return None

    def _fallback(self, raw: str, projects_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "rankings": [
                {"project_id": p["project_id"], "filename": p["filename"],
                 "score": 0, "strengths": [], "weaknesses": ["Parse error"],
                 "one_line_summary": ""}
                for p in projects_data
            ],
            "reasoning": f"Parse error. Raw: {raw[:300]}",
        }


def rank_projects_with_gemini(user_name: Optional[str] = None) -> Dict[str, Any]:
    """End-to-end: gather user's projects, send to Gemini, return rankings."""
    ranker = GeminiRanker()
    data = ranker.gather_projects_data(user_name=user_name)
    if not data:
        return {"success": False, "error": "No projects found for user", "rankings": []}
    return ranker.rank_projects(data)
