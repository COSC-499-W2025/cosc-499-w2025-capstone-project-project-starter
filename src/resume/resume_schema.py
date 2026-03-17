"""Pydantic schemas for full resume composition and export (team-4 style)."""
from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict


class ResumeContact(BaseModel):
    name: str = ""
    email: str = ""
    phone: str | None = None
    location: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None


class ResumeEducation(BaseModel):
    institution: str = ""
    degree: str = ""
    field_of_study: str = ""
    location: str | None = None
    start_date: str | None = None  # "YYYY-MM"
    end_date: str | None = None
    is_current: bool = False
    gpa: str | None = None


class ResumeExperience(BaseModel):
    company_name: str = ""
    job_title: str = ""
    location: str | None = None
    is_remote: bool = False
    start_date: str | None = None
    end_date: str | None = None
    is_current: bool = False
    responsibilities: List[str] = []
    achievements: List[str] = []


class ResumeProject(BaseModel):
    project_id: int | None = None
    title: str = ""
    technologies: List[str] = []
    highlights: List[str] = []
    date_label: str | None = None


class FullResumeData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    contact: ResumeContact = ResumeContact()
    summary: str | None = None
    education: List[ResumeEducation] = []
    experience: List[ResumeExperience] = []
    projects: List[ResumeProject] = []
    skills: Dict[str, List[str]] = {}

    @classmethod
    def from_legacy_model(cls, data: Dict[str, Any]) -> "FullResumeData":
        """Build FullResumeData from current API shape (name, email, links, education, skills, projects)."""
        links = data.get("links") or []
        link_map = {l.get("label", "").lower(): l.get("url") for l in links if l.get("label")}
        contact = ResumeContact(
            name=(data.get("name") or "").strip(),
            email=(data.get("email") or "").strip(),
            phone=None,
            location=None,
            linkedin_url=link_map.get("linkedin"),
            github_url=link_map.get("github"),
            portfolio_url=link_map.get("website"),
        )
        education_raw = data.get("education") or []
        education = [
            ResumeEducation(
                institution=e.get("school") or "",
                degree=e.get("degree") or "",
                field_of_study=e.get("major") or "",
                location=e.get("location"),
                start_date=e.get("start_date"),
                end_date=e.get("end_date"),
                is_current=False,
                gpa=str(e.get("gpa", "") or "") or None,
            )
            for e in education_raw
        ]
        skills_raw = data.get("skills") or {}
        if isinstance(skills_raw, dict) and "Skills" in skills_raw:
            skills = {"Skills": skills_raw["Skills"] or []}
        elif isinstance(skills_raw, dict):
            skills = {k: (v if isinstance(v, list) else []) for k, v in skills_raw.items()}
        else:
            skills = {}
        projects_raw = data.get("projects") or []
        projects = [
            ResumeProject(
                project_id=int(p["project_id"]) if p.get("project_id") and str(p["project_id"]).isdigit() else None,
                title=(p.get("title") or "").strip(),
                technologies=(p.get("skills") or p.get("technologies") or [])[:20],
                highlights=(p.get("bullets") or p.get("highlights") or [])[:15],
                date_label=(p.get("dates") or p.get("date_label")) or None,
            )
            for p in projects_raw
        ]
        return cls(
            contact=contact,
            summary=data.get("summary"),
            education=education,
            experience=[],
            projects=projects,
            skills=skills,
        )

    def to_legacy_model(self) -> Dict[str, Any]:
        """Convert to legacy API shape for backward compatibility."""
        links = []
        if self.contact.linkedin_url:
            links.append({"label": "LinkedIn", "url": self.contact.linkedin_url})
        if self.contact.github_url:
            links.append({"label": "GitHub", "url": self.contact.github_url})
        if self.contact.portfolio_url:
            links.append({"label": "Website", "url": self.contact.portfolio_url})
        education = [
            {
                "school": e.institution,
                "degree": e.degree,
                "major": e.field_of_study,
                "location": e.location,
                "dates": f"{e.start_date or ''} – {e.end_date or 'Present'}" if e.start_date else "",
                "gpa": e.gpa,
            }
            for e in self.education
        ]
        projects = [
            {
                "project_id": str(p.project_id) if p.project_id else None,
                "title": p.title,
                "dates": p.date_label or "",
                "skills": p.technologies,
                "bullets": p.highlights,
            }
            for p in self.projects
        ]
        return {
            "name": self.contact.name,
            "email": self.contact.email,
            "links": links,
            "education": education,
            "skills": {"Skills": self.skills.get("Skills", []) if self.skills else []},
            "projects": projects,
            "summary": self.summary,
        }
