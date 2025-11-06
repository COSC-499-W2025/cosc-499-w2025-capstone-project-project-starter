import json
from datetime import datetime

class ResumeFormatter:
    @staticmethod
    def format_json(resume_data):
        try:
            if not resume_data:
                return None
            
            return json.dumps(resume_data, indent=2, default=str)
            
        except Exception as e:
            print(f"[ERROR] Error formatting resume as JSON: {e}")
            return None
    
    @staticmethod
    def format_markdown(resume_data):
        try:
            if not resume_data:
                return None
            
            lines = []
            lines.append("# Resume")
            lines.append("")
            
            lines.append(f"## Overview")
            lines.append(f"- Total Projects Analyzed: {resume_data.get('total_projects_analyzed', 0)}")
            lines.append(f"- Top Projects Displayed: {resume_data.get('top_projects_displayed', 0)}")
            lines.append("")
            
            lines.append("## Skills")
            skills = resume_data.get('all_skills', [])
            if skills:
                lines.append(", ".join(skills))
            else:
                lines.append("No skills identified")
            lines.append("")
            
            lines.append("## Top Projects")
            top_projects = resume_data.get('top_projects', [])
            
            if top_projects:
                for idx, project in enumerate(top_projects, 1):
                    lines.append(f"### {idx}. {project.get('project_name', 'Unknown')}")
                    lines.append(f"**Type:** {project.get('project_type', 'General')}")
                    lines.append(f"**Score:** {project.get('score', 0)}")
                    project_skills = project.get('skills', [])
                    if project_skills:
                        lines.append(f"**Technologies:** {', '.join(project_skills)}")
                    lines.append("")
            else:
                lines.append("No projects to display")
                lines.append("")
            
            lines.append(f"*Generated: {resume_data.get('generated_at', 'Unknown')}*")
            
            return "\n".join(lines)
            
        except Exception as e:
            print(f"[ERROR] Error formatting resume as Markdown: {e}")
            return None
    
    @staticmethod
    def format_text(resume_data):
        try:
            if not resume_data:
                return None
            
            lines = []
            lines.append("=" * 60)
            lines.append("RESUME")
            lines.append("=" * 60)
            lines.append("")
            
            lines.append("OVERVIEW:")
            lines.append(f"Total Projects Analyzed: {resume_data.get('total_projects_analyzed', 0)}")
            lines.append(f"Top Projects Displayed: {resume_data.get('top_projects_displayed', 0)}")
            lines.append("")
            
            lines.append("SKILLS:")
            skills = resume_data.get('all_skills', [])
            if skills:
                for skill in skills:
                    lines.append(f"  - {skill}")
            else:
                lines.append("  No skills identified")
            lines.append("")
            
            lines.append("TOP PROJECTS:")
            top_projects = resume_data.get('top_projects', [])
            
            if top_projects:
                for idx, project in enumerate(top_projects, 1):
                    lines.append(f"{idx}. {project.get('project_name', 'Unknown')}")
                    lines.append(f"   Type: {project.get('project_type', 'General')}")
                    lines.append(f"   Score: {project.get('score', 0)}")
                    project_skills = project.get('skills', [])
                    if project_skills:
                        lines.append(f"   Technologies: {', '.join(project_skills)}")
                    lines.append("")
            else:
                lines.append("  No projects to display")
                lines.append("")
            
            lines.append("=" * 60)
            lines.append(f"Generated: {resume_data.get('generated_at', 'Unknown')}")
            lines.append("=" * 60)
            
            return "\n".join(lines)
            
        except Exception as e:
            print(f"[ERROR] Error formatting resume as text: {e}")
            return None
    
    @staticmethod
    def get_formatted_resume(resume_data, format_type='text'):
        if not resume_data:
            print("[ERROR] No resume data provided")
            return None
        
        format_type = format_type.lower().strip()
        
        if format_type == 'json':
            return ResumeFormatter.format_json(resume_data)
        elif format_type == 'markdown':
            return ResumeFormatter.format_markdown(resume_data)
        elif format_type == 'text':
            return ResumeFormatter.format_text(resume_data)
        else:
            print(f"[ERROR] Unknown format type: {format_type}. Using text format.")
            return ResumeFormatter.format_text(resume_data)