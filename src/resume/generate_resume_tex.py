"""Generate LaTeX resume from resume model (team-3 style)."""
import json
import re
from typing import Any, Dict, List


def escape_latex(text: str) -> str:
    text = (
        (text or "")
        .replace("–", "--")
        .replace("—", "---")
        .replace(""", "``")
        .replace(""", "''")
        .replace("'", "'")
    )
    mapping = {
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
        "\\": r"\textbackslash{}",
    }
    for k, v in mapping.items():
        text = text.replace(k, v)
    return text


def render_skills(skills: Dict[str, List[str]]) -> str:
    rows = []
    for category, items in skills.items():
        escaped = ", ".join(escape_latex(i) for i in items)
        rows.append(f"{escape_latex(category)}: & {escaped} \\\\")
    return "\n".join(rows)


def render_projects(projects: List[Dict]) -> str:
    blocks = []
    for project in projects:
        raw_bullets = project.get("bullets", [])
        if isinstance(raw_bullets, str):
            try:
                bullet_list = json.loads(raw_bullets) if raw_bullets.strip().startswith("[") else [raw_bullets]
            except Exception:
                bullet_list = [raw_bullets]
        elif isinstance(raw_bullets, (list, tuple)):
            bullet_list = list(raw_bullets)
        else:
            bullet_list = [str(raw_bullets)] if raw_bullets else []
        flat = []
        for b in bullet_list:
            if b is None:
                continue
            if isinstance(b, (list, tuple)):
                flat.extend(str(x) for x in b if x is not None)
            else:
                flat.append(str(b))
        bullets_tex = "\n".join(f"\\item {escape_latex(item)}" for item in flat if str(item).strip())
        title = (project.get("title") or "")[:1].upper() + (project.get("title") or "")[1:]
        raw_skills = project.get("skills", [])
        skills_str = ", ".join(raw_skills) if isinstance(raw_skills, (list, tuple)) else str(raw_skills)
        block = rf""" \vspace*{{3mm}}
	\textbf{{{escape_latex(title)}}} \hfill {escape_latex(project.get('dates', ''))}\\
    {{\textbf{{Skills: }}\sl {escape_latex(skills_str)}}}\\[1mm]
    \begin{{itemize}}[leftmargin=2em]
{bullets_tex}
\end{{itemize}}
"""
        blocks.append(block)
    return "\n".join(blocks)


def render_links(links: List[Dict]) -> str:
    if not links:
        return ""
    parts = []
    for link in links:
        parts.append(rf"\textbf{{\href{{{escape_latex(link.get('url',''))}}}{{{escape_latex(link.get('label',''))}}}}}")
    return " \\quad ".join(parts)


def render_education(education_list: List[Dict[str, Any]]) -> str:
    if not education_list:
        return ""
    blocks = []
    for edu in education_list:
        school = escape_latex(edu.get("school", ""))
        degree = escape_latex(edu.get("degree", ""))
        dates = escape_latex(edu.get("dates", ""))
        gpa = escape_latex(str(edu.get("gpa", "")).strip())
        gpa_line = rf"{{\sl GPA: {gpa}}}\\" if gpa else ""
        block = rf"""{school} \hfill {dates}\\
{{\sl {degree}}}\\
{gpa_line}"""
        blocks.append(block.strip())
    return "\n\n".join(blocks)


def generate_resume_tex(resume: Dict[str, Any]) -> str:
    from resume.latex_template import ResumeTemplate

    tex = ResumeTemplate.LATEX_TEMPLATE
    tex = tex.replace("{name}", escape_latex(resume.get("name", "")))
    tex = tex.replace("{email}", escape_latex(resume.get("email", "")))
    tex = tex.replace("{links_block}", render_links(resume.get("links", [])))
    education_list = resume.get("education", [])
    if isinstance(education_list, list):
        education_block = render_education(education_list)
    else:
        education_block = render_education([education_list])
    tex = tex.replace("{education_section}", education_block)
    tex = tex.replace("{skills_table}", render_skills(resume.get("skills", {"Skills": []})))
    tex = tex.replace("{projects}", render_projects(resume.get("projects", [])))
    return tex
