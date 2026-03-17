"""
Resume builder service (team-3 style).
Builds resume model: name, email, links, education[], skills: {Skills: []}, projects: [{project_id, title, dates, skills, bullets}].
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from config.db_config import with_db_cursor
from database.user_preferences import get_user_git_username
from database.user_profile import get_profile as get_user_profile
from resume.resume_builder_db import init_resume_builder_tables
from resume.resume_manager import ResumeManager


class ResumeBuilderError(Exception):
    pass


class ResumeNotFoundError(ResumeBuilderError):
    pass


class ResumePersistenceError(ResumeBuilderError):
    pass


def _format_dates(start: str, end: str) -> str:
    """Format dates to 'Mon YYYY – Mon YYYY'."""
    try:
        if start:
            s = datetime.fromisoformat(str(start).replace("Z", "+00:00")[:10])
            start_str = s.strftime("%b %Y")
        else:
            start_str = ""
        if end:
            e = datetime.fromisoformat(str(end).replace("Z", "+00:00")[:10])
            end_str = e.strftime("%b %Y")
        else:
            end_str = ""
        if start_str and end_str:
            return f"{start_str} – {end_str}"
        if start_str:
            return f"{start_str} – Present"
        return ""
    except Exception:
        return ""


def _load_user_for_resume(user_name: str) -> Dict[str, Any]:
    """Return user info in team-3 shape: name, email, links, education (list of {school, degree, dates, gpa})."""
    name = user_name
    email = ""
    links: List[Dict[str, str]] = []
    education: List[Dict[str, Any]] = []

    profile = get_user_profile(user_name)
    if profile:
        if profile.get("display_name"):
            name = profile["display_name"]
        if profile.get("email"):
            email = profile["email"]
        if profile.get("education"):
            education = profile["education"]
        if profile.get("linkedin"):
            url = profile["linkedin"]
            if url and not url.startswith("http"):
                url = f"https://{url}"
            links.append({"label": "LinkedIn", "url": url or "#"})
        if profile.get("github"):
            gh = profile["github"].strip()
            if gh and not gh.startswith("http"):
                gh = f"https://github.com/{gh}" if not gh.startswith("github.com") else f"https://{gh}"
            links.append({"label": "GitHub", "url": gh or "#"})
        if profile.get("website"):
            url = profile["website"]
            if url and not url.startswith("http"):
                url = f"https://{url}"
            links.append({"label": "Website", "url": url or "#"})

    if not any(l.get("label") == "GitHub" for l in links):
        git_user = get_user_git_username(user_name)
        if git_user:
            links.append({"label": "GitHub", "url": f"https://github.com/{git_user}"})

    if not email and not profile:
        try:
            existing = ResumeManager.get_user_resume(user_name)
            if existing and isinstance(existing.get("resume_data"), dict):
                data = existing["resume_data"]
                if data.get("display_name"):
                    name = data["display_name"]
                pi = data.get("personal_info") or {}
                if pi.get("email"):
                    email = pi["email"]
        except Exception:
            pass

    summary = (profile.get("summary") or "").strip() if profile else ""
    location = (profile.get("location") or "").strip() if profile else ""
    phone = (profile.get("phone") or "").strip() if profile else ""
    return {
        "name": name,
        "email": email or f"{user_name}@user",
        "links": links,
        "education": education,
        "summary": summary,
        "location": location,
        "phone": phone,
    }


def _project_summaries_to_resume_projects(
    project_summaries: List[Dict], user_name: str
) -> List[Dict[str, Any]]:
    """Convert internal project_summaries to team-3 project entries with project_id, title, dates, skills, bullets."""
    out = []
    for p in project_summaries:
        project_id = p.get("project_id")
        first_file = (p.get("first_file") or "")[:10] if p.get("first_file") else ""
        last_file = (p.get("last_file") or "")[:10] if p.get("last_file") else ""
        dates = _format_dates(first_file, last_file)
        skills = (p.get("skills") or [])[:5]
        bullets = p.get("evidence") or []
        out.append({
            "project_id": str(project_id),
            "title": p.get("project_name", ""),
            "dates": dates,
            "skills": skills,
            "bullets": bullets,
        })
    return out


def build_resume_model(user_name: str, project_ids: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Build resume model (team-3 shape) from DB.
    If project_ids is None or empty, include all projects for the user (master resume).
    """
    init_resume_builder_tables()
    user = _load_user_for_resume(user_name)
    selection = None
    if project_ids is not None and len(project_ids) > 0:
        selection = {"selected_project_ids": project_ids, "top_projects_count": max(len(project_ids), 1)}
    resume_data = ResumeManager.generate_user_resume(
        user_name, top_projects_count=100, selection=selection
    )
    if not resume_data:
        return {
            "name": user["name"],
            "email": user["email"],
            "links": user["links"],
            "education": user["education"],
            "skills": {"Skills": []},
            "projects": [],
        }
    projects = _project_summaries_to_resume_projects(
        resume_data.get("top_projects") or [], user_name
    )
    all_skills = resume_data.get("all_skills") or []
    return {
        "name": user["name"],
        "email": user["email"],
        "links": user["links"],
        "education": user["education"],
        "summary": user.get("summary") or "",
        "phone": user.get("phone") or "",
        "location": user.get("location") or "",
        "skills": {"Skills": all_skills},
        "projects": projects,
        "experience": [],
    }


def load_saved_resume(user_name: str, resume_id: int) -> Dict[str, Any]:
    """Load a saved resume by id (resume_projects, resume_skills, resume_experience, contact/education overrides)."""
    init_resume_builder_tables()
    with with_db_cursor() as cursor:
        cursor.execute(
            "SELECT id, name, summary, contact, education FROM resumes WHERE id = %s AND user_name = %s",
            (resume_id, user_name),
        )
        row = cursor.fetchone()
        if not row:
            raise ResumeNotFoundError(f"Resume {resume_id} not found")
        summary_val = row[2] if len(row) > 2 else None
        contact_json = row[3] if len(row) > 3 else None
        education_json = row[4] if len(row) > 4 else None
        cursor.execute(
            """
            SELECT rp.project_id, rp.project_name, rp.start_date, rp.end_date, rp.skills, rp.bullets, rp.display_order,
                   uf.filename, uf.created_at, uf.last_modified_at
            FROM resume_projects rp
            LEFT JOIN uploaded_files uf ON uf.id = rp.project_id
            WHERE rp.resume_id = %s
            ORDER BY rp.display_order
            """,
            (resume_id,),
        )
        rows = cursor.fetchall()
        cursor.execute(
            """
            SELECT company_name, job_title, location, is_remote, start_date, end_date, is_current,
                   responsibilities, achievements, display_order
            FROM resume_experience WHERE resume_id = %s ORDER BY display_order, id
            """,
            (resume_id,),
        )
        exp_rows = cursor.fetchall()
        cursor.execute("SELECT skills FROM resume_skills WHERE resume_id = %s", (resume_id,))
        rs = cursor.fetchone()

    user = _load_user_for_resume(user_name)
    if contact_json:
        try:
            c = json.loads(contact_json) if isinstance(contact_json, str) else contact_json
            if isinstance(c, dict):
                user["name"] = c.get("name") or user["name"]
                user["email"] = c.get("email") or user["email"]
                user["phone"] = c.get("phone") or user.get("phone") or ""
                user["location"] = c.get("location") or user.get("location") or ""
                links = []
                if c.get("linkedin_url"):
                    links.append({"label": "LinkedIn", "url": c["linkedin_url"]})
                if c.get("github_url"):
                    links.append({"label": "GitHub", "url": c["github_url"]})
                if c.get("portfolio_url"):
                    links.append({"label": "Website", "url": c["portfolio_url"]})
                if links:
                    user["links"] = links
        except Exception:
            pass
    if education_json:
        try:
            edu = json.loads(education_json) if isinstance(education_json, str) else education_json
            if isinstance(edu, list):
                user["education"] = edu
        except Exception:
            pass

    base_projects_by_id = {}
    if rows:
        project_ids = [r[0] for r in rows]
        base_model = build_resume_model(user_name, project_ids=project_ids)
        base_projects_by_id = {p["project_id"]: p for p in base_model.get("projects", [])}

    projects_out = []
    for r in rows:
        pid, override_name, start_d, end_d, skills_json, bullets_json, order, base_name, created_at, last_modified = r
        pid_str = str(pid)
        base = base_projects_by_id.get(pid_str, {})
        if skills_json is not None:
            skills = json.loads(skills_json) if isinstance(skills_json, str) else skills_json
        else:
            skills = base.get("skills", [])[:5]
        if not isinstance(skills, list):
            skills = list(skills) if skills else []
        if bullets_json is not None:
            bullets = json.loads(bullets_json) if isinstance(bullets_json, str) else bullets_json
        else:
            bullets = base.get("bullets", [])
        if not isinstance(bullets, list):
            bullets = list(bullets) if bullets else []
        title = override_name or base.get("title") or base_name or "(Removed project)"
        start_val = start_d or (created_at.strftime("%Y-%m-%d") if created_at else "")
        end_val = end_d or (last_modified.strftime("%Y-%m-%d") if last_modified else (created_at.strftime("%Y-%m-%d") if created_at else ""))
        dates = _format_dates(start_val, end_val) if (start_val and end_val) else ""
        projects_out.append({
            "project_id": pid_str,
            "title": title,
            "dates": dates,
            "skills": skills[:5],
            "bullets": bullets,
        })

    if rs and rs[0]:
        raw_skills = json.loads(rs[0]) if isinstance(rs[0], str) else rs[0]
        if isinstance(raw_skills, dict):
            all_skills_dict = raw_skills
        else:
            all_skills_dict = {"Skills": raw_skills if isinstance(raw_skills, list) else []}
    else:
        all_skills_dict = {"Skills": sorted(set(s for p in projects_out for s in p["skills"]))}

    experience_out = []
    for er in exp_rows:
        (company_name, job_title, location, is_remote, start_date, end_date, is_current,
         resp_json, ach_json, _order) = er
        resp = json.loads(resp_json) if isinstance(resp_json, str) else (resp_json or [])
        ach = json.loads(ach_json) if isinstance(ach_json, str) else (ach_json or [])
        if not isinstance(resp, list):
            resp = []
        if not isinstance(ach, list):
            ach = []
        experience_out.append({
            "company_name": company_name or "",
            "job_title": job_title or "",
            "location": location,
            "is_remote": bool(is_remote),
            "start_date": start_date,
            "end_date": end_date,
            "is_current": bool(is_current),
            "responsibilities": resp,
            "achievements": ach,
        })

    return {
        "name": user["name"],
        "email": user["email"],
        "links": user["links"],
        "education": user["education"],
        "summary": summary_val or user.get("summary") or "",
        "phone": user.get("phone") or "",
        "location": user.get("location") or "",
        "skills": all_skills_dict,
        "projects": projects_out,
        "experience": experience_out,
    }


def create_resume(user_name: str, name: str) -> int:
    """Create a new resume row; returns resume id."""
    init_resume_builder_tables()
    with with_db_cursor() as cursor:
        cursor.execute(
            "INSERT INTO resumes (user_name, name) VALUES (%s, %s) RETURNING id",
            (user_name, name),
        )
        resume_id = cursor.fetchone()[0]
    return resume_id


def attach_projects_to_resume(user_name: str, resume_id: int, project_ids: List[int]) -> None:
    """Attach projects to a resume with display_order by last_modified DESC."""
    init_resume_builder_tables()
    with with_db_cursor() as cursor:
        cursor.execute("SELECT 1 FROM resumes WHERE id = %s AND user_name = %s", (resume_id, user_name))
        if not cursor.fetchone():
            raise ResumeNotFoundError(f"Resume {resume_id} not found")
        # Get last_modified for ordering
        placeholders = ",".join(["%s"] * len(project_ids))
        cursor.execute(
            f"""
            SELECT id, COALESCE(last_modified_at, created_at)
            FROM uploaded_files
            WHERE id IN ({placeholders}) AND user_name = %s
            """,
            (*project_ids, user_name),
        )
        rows = cursor.fetchall()
    if not rows:
        return
    ordered = sorted(rows, key=lambda x: x[1] or "", reverse=True)
    with with_db_cursor() as cursor:
        for idx, (pid, _) in enumerate(ordered):
            cursor.execute(
                """
                INSERT INTO resume_projects (resume_id, project_id, display_order)
                VALUES (%s, %s, %s)
                ON CONFLICT (resume_id, project_id) DO NOTHING
                """,
                (resume_id, pid, idx + 1),
            )


def list_resumes(user_name: str) -> List[Dict[str, Any]]:
    """Return list of resumes for sidebar: {id, name, is_master}. Master is virtual (id=0 or first)."""
    init_resume_builder_tables()
    with with_db_cursor() as cursor:
        cursor.execute(
            "SELECT id, name FROM resumes WHERE user_name = %s ORDER BY id",
            (user_name,),
        )
        rows = cursor.fetchall()
    result = [
        {"id": r[0], "name": (r[1] or f"Resume-{r[0]}").strip() or f"Resume-{r[0]}", "is_master": False}
        for r in rows
    ]
    # Prepend master resume (virtual; id=0 so DB saved resumes can use 1,2,3...)
    result.insert(0, {"id": 0, "name": "Master Resume", "is_master": True})
    return result


def resume_exists(user_name: str, resume_id: int) -> bool:
    if resume_id == 0:
        return True
    with with_db_cursor() as cursor:
        cursor.execute("SELECT 1 FROM resumes WHERE id = %s AND user_name = %s", (resume_id, user_name))
        return cursor.fetchone() is not None


def save_resume_edits(user_name: str, resume_id: int, payload: Dict[str, Any]) -> None:
    """Save edits: contact, summary, education, experience, skills (list or dict), projects."""
    if resume_id == 0:
        raise ResumePersistenceError("Cannot edit Master Resume")
    init_resume_builder_tables()
    with with_db_cursor() as cursor:
        cursor.execute("SELECT 1 FROM resumes WHERE id = %s AND user_name = %s", (resume_id, user_name))
        if not cursor.fetchone():
            raise ResumeNotFoundError(f"Resume {resume_id} not found")

        if "contact" in payload and isinstance(payload["contact"], dict):
            cursor.execute(
                "UPDATE resumes SET contact = %s WHERE id = %s AND user_name = %s",
                (json.dumps(payload["contact"]), resume_id, user_name),
            )
        if "summary" in payload:
            cursor.execute(
                "UPDATE resumes SET summary = %s WHERE id = %s AND user_name = %s",
                (payload["summary"] or None, resume_id, user_name),
            )
        if "education" in payload and isinstance(payload["education"], list):
            cursor.execute(
                "UPDATE resumes SET education = %s WHERE id = %s AND user_name = %s",
                (json.dumps(payload["education"]), resume_id, user_name),
            )

        if "experience" in payload and isinstance(payload["experience"], list):
            cursor.execute("DELETE FROM resume_experience WHERE resume_id = %s", (resume_id,))
            for idx, exp in enumerate(payload["experience"]):
                if not isinstance(exp, dict):
                    continue
                cursor.execute(
                    """
                    INSERT INTO resume_experience
                    (resume_id, company_name, job_title, location, is_remote, start_date, end_date,
                     is_current, responsibilities, achievements, display_order)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        resume_id,
                        exp.get("company_name"),
                        exp.get("job_title"),
                        exp.get("location"),
                        bool(exp.get("is_remote")),
                        exp.get("start_date"),
                        exp.get("end_date"),
                        bool(exp.get("is_current")),
                        json.dumps(exp.get("responsibilities") or []),
                        json.dumps(exp.get("achievements") or []),
                        idx,
                    ),
                )

        if "skills" in payload:
            raw = payload["skills"]
            if isinstance(raw, dict):
                skills_json = json.dumps(raw)
            else:
                skills_json = json.dumps({"Skills": raw if isinstance(raw, list) else []})
            cursor.execute(
                """
                INSERT INTO resume_skills (resume_id, skills)
                VALUES (%s, %s)
                ON CONFLICT (resume_id) DO UPDATE SET skills = EXCLUDED.skills, updated_at = CURRENT_TIMESTAMP
                """,
                (resume_id, skills_json),
            )

        for idx, project in enumerate(payload.get("projects", [])):
            pid = project.get("project_id")
            if pid is None:
                continue
            pid_int = int(pid) if isinstance(pid, str) and pid.isdigit() else (int(pid) if isinstance(pid, int) else None)
            if pid_int is None:
                continue
            proj_skills = project.get("skills") or project.get("technologies") or []
            proj_bullets = project.get("bullets") or project.get("highlights") or []
            display_order = project.get("display_order")
            if display_order is None:
                display_order = idx
            cursor.execute(
                """
                INSERT INTO resume_projects (resume_id, project_id, project_name, start_date, end_date, skills, bullets, display_order)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (resume_id, project_id) DO UPDATE SET
                    project_name  = COALESCE(EXCLUDED.project_name, resume_projects.project_name),
                    start_date    = COALESCE(EXCLUDED.start_date, resume_projects.start_date),
                    end_date      = COALESCE(EXCLUDED.end_date, resume_projects.end_date),
                    skills        = COALESCE(EXCLUDED.skills, resume_projects.skills),
                    bullets       = COALESCE(EXCLUDED.bullets, resume_projects.bullets),
                    display_order = COALESCE(EXCLUDED.display_order, resume_projects.display_order)
                """,
                (
                    resume_id,
                    pid_int,
                    project.get("project_name") or project.get("title"),
                    project.get("start_date"),
                    project.get("end_date"),
                    json.dumps(proj_skills) if proj_skills else None,
                    json.dumps(proj_bullets) if proj_bullets else None,
                    display_order,
                ),
            )


def add_projects_to_resume(user_name: str, resume_id: int, project_ids: List[int]) -> None:
    """Append projects to an existing resume (skip if already on resume)."""
    if resume_id == 0:
        raise ResumePersistenceError("Cannot add projects to Master Resume")
    if not resume_exists(user_name, resume_id):
        raise ResumeNotFoundError(f"Resume {resume_id} not found")
    with with_db_cursor() as cursor:
        cursor.execute(
            "SELECT project_id, display_order FROM resume_projects WHERE resume_id = %s",
            (resume_id,),
        )
        existing = {row[0]: row[1] for row in cursor.fetchall()}
    max_order = max(existing.values(), default=0)
    new_ids = [pid for pid in project_ids if pid not in existing]
    if not new_ids:
        return
    with with_db_cursor() as cursor:
        placeholders = ",".join(["%s"] * len(new_ids))
        cursor.execute(
            f"""
            SELECT id, COALESCE(last_modified_at, created_at)
            FROM uploaded_files
            WHERE id IN ({placeholders}) AND user_name = %s
            """,
            (*new_ids, user_name),
        )
        rows = cursor.fetchall()
    ordered = sorted(rows, key=lambda x: x[1] or "", reverse=True)
    with with_db_cursor() as cursor:
        for idx, (pid, _) in enumerate(ordered):
            cursor.execute(
                "INSERT INTO resume_projects (resume_id, project_id, display_order) VALUES (%s, %s, %s)",
                (resume_id, pid, max_order + 1 + idx),
            )


def remove_project_from_resume(user_name: str, resume_id: int, project_id: int) -> None:
    """Remove a project from a resume."""
    if not resume_exists(user_name, resume_id):
        raise ResumeNotFoundError(f"Resume {resume_id} not found")
    with with_db_cursor() as cursor:
        cursor.execute(
            "DELETE FROM resume_projects WHERE resume_id = %s AND project_id = %s",
            (resume_id, project_id),
        )


def delete_resume(user_name: str, resume_id: int) -> None:
    """Delete a saved resume (not master)."""
    if resume_id == 0:
        raise ResumePersistenceError("Cannot delete Master Resume")
    if not resume_exists(user_name, resume_id):
        raise ResumeNotFoundError(f"Resume {resume_id} not found")
    with with_db_cursor() as cursor:
        cursor.execute("DELETE FROM resumes WHERE id = %s AND user_name = %s", (resume_id, user_name))
