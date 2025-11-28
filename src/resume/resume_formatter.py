import json
import os
from datetime import datetime


class ResumeFormatter:
    """Formats resume data into various output formats including PDF."""
    
    @staticmethod
    def format_json(resume_data):
        """
        Format resume as JSON.
        
        Args:
            resume_data: Resume data dictionary
            
        Returns:
            str: JSON formatted string or None if error
        """
        try:
            if not resume_data:
                return None
            
            return json.dumps(resume_data, indent=2, default=str)
            
        except Exception as e:
            print(f"[ERROR] Error formatting resume as JSON: {e}")
            return None
    
    @staticmethod
    def format_markdown(resume_data):
        """
        Format resume as Markdown.
        
        Args:
            resume_data: Resume data dictionary
            
        Returns:
            str: Markdown formatted string or None if error
        """
        try:
            if not resume_data:
                return None
            
            lines = []
            lines.append("# Resume")
            lines.append("")
            
            # Overview section
            lines.append("## Overview")
            lines.append(f"- Total Projects Analyzed: {resume_data.get('total_projects_analyzed', 0)}")
            lines.append(f"- Top Projects Displayed: {resume_data.get('top_projects_displayed', 0)}")
            
            summary_stats = resume_data.get('summary_stats', {})
            if summary_stats:
                lines.append(f"- Total Lines of Code: {summary_stats.get('total_lines_of_code', 0):,}")
                lines.append(f"- Total Files: {summary_stats.get('total_files', 0):,}")
                lines.append(f"- Unique Languages: {summary_stats.get('unique_languages', 0)}")
                lines.append(f"- Unique Frameworks: {summary_stats.get('unique_frameworks', 0)}")
            lines.append("")
            
            # Skills section
            lines.append("## Technical Skills")
            
            categorized_skills = resume_data.get('categorized_skills', {})
            if categorized_skills:
                for category, skill_list in categorized_skills.items():
                    if skill_list:
                        lines.append(f"### {category}")
                        lines.append(", ".join(skill_list))
                        lines.append("")
            else:
                skills = resume_data.get('all_skills', [])
                if skills:
                    lines.append(", ".join(skills))
                else:
                    lines.append("No skills identified")
            lines.append("")
            
            # Languages section
            languages = resume_data.get('languages', [])
            if languages:
                lines.append("## Programming Languages")
                lines.append(", ".join(languages))
                lines.append("")
            
            # Frameworks section
            frameworks = resume_data.get('frameworks', [])
            if frameworks:
                lines.append("## Frameworks and Tools")
                lines.append(", ".join(frameworks))
                lines.append("")
            
            # Projects section
            lines.append("## Top Projects")
            top_projects = resume_data.get('top_projects', [])
            
            if top_projects:
                for idx, project in enumerate(top_projects, 1):
                    project_name = project.get('project_name', 'Unknown')
                    clean_name = project_name.replace('.zip', '').replace('-master', '').replace('-main', '')
                    lines.append(f"### {idx}. {clean_name}")
                    lines.append(f"**Score:** {project.get('score', 0)}")
                    lines.append(f"**Primary Language:** {project.get('primary_language', 'Unknown')}")
                    
                    if project.get('lines_of_code', 0) > 0:
                        lines.append(f"**Scale:** {project.get('lines_of_code', 0):,} lines across {project.get('file_count', 0)} files")
                    
                    if project.get('frameworks'):
                        lines.append(f"**Frameworks:** {', '.join(project.get('frameworks', []))}")
                    
                    if project.get('collaboration_level') and project.get('collaboration_level') != 'Unknown':
                        lines.append(f"**Collaboration:** {project.get('collaboration_level')}")
                    
                    if project.get('code_quality_score', 0) > 0:
                        lines.append(f"**Code Quality Score:** {project.get('code_quality_score', 0)}/100")
                    
                    highlights = []
                    if project.get('has_tests'):
                        highlights.append("Unit Testing")
                    if project.get('has_docs'):
                        highlights.append("Documentation")
                    if project.get('oop_principles_count', 0) > 0:
                        highlights.append(f"OOP Principles ({project.get('oop_principles_count')} instances)")
                    if project.get('optimization_count', 0) > 0:
                        highlights.append(f"Code Optimizations ({project.get('optimization_count')} patterns)")
                    
                    if highlights:
                        lines.append(f"**Highlights:** {', '.join(highlights)}")
                    
                    project_skills = project.get('skills', [])
                    if project_skills:
                        lines.append(f"**Technologies:** {', '.join(project_skills[:8])}")
                    
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
        """
        Format resume as plain text.
        
        Args:
            resume_data: Resume data dictionary
            
        Returns:
            str: Plain text formatted string or None if error
        """
        try:
            if not resume_data:
                return None
            
            lines = []
            lines.append("=" * 70)
            lines.append("RESUME")
            lines.append("=" * 70)
            lines.append("")
            
            # Overview section
            lines.append("OVERVIEW")
            lines.append("-" * 70)
            lines.append(f"Total Projects Analyzed: {resume_data.get('total_projects_analyzed', 0)}")
            lines.append(f"Top Projects Displayed: {resume_data.get('top_projects_displayed', 0)}")
            
            summary_stats = resume_data.get('summary_stats', {})
            if summary_stats:
                lines.append(f"Total Lines of Code: {summary_stats.get('total_lines_of_code', 0):,}")
                lines.append(f"Total Files: {summary_stats.get('total_files', 0):,}")
                lines.append(f"Unique Languages: {summary_stats.get('unique_languages', 0)}")
                lines.append(f"Unique Frameworks: {summary_stats.get('unique_frameworks', 0)}")
            lines.append("")
            
            # Skills section
            lines.append("TECHNICAL SKILLS")
            lines.append("-" * 70)
            
            categorized_skills = resume_data.get('categorized_skills', {})
            if categorized_skills:
                for category, skill_list in categorized_skills.items():
                    if skill_list:
                        lines.append(f"{category}:")
                        for skill in skill_list:
                            lines.append(f"  - {skill}")
                        lines.append("")
            else:
                skills = resume_data.get('all_skills', [])
                if skills:
                    for skill in skills:
                        lines.append(f"  - {skill}")
                else:
                    lines.append("  No skills identified")
            lines.append("")
            
            # Languages section
            languages = resume_data.get('languages', [])
            if languages:
                lines.append("PROGRAMMING LANGUAGES")
                lines.append("-" * 70)
                lines.append(", ".join(languages))
                lines.append("")
            
            # Frameworks section
            frameworks = resume_data.get('frameworks', [])
            if frameworks:
                lines.append("FRAMEWORKS AND TOOLS")
                lines.append("-" * 70)
                lines.append(", ".join(frameworks))
                lines.append("")
            
            # Projects section
            lines.append("TOP PROJECTS")
            lines.append("-" * 70)
            top_projects = resume_data.get('top_projects', [])
            
            if top_projects:
                for idx, project in enumerate(top_projects, 1):
                    project_name = project.get('project_name', 'Unknown')
                    clean_name = project_name.replace('.zip', '').replace('-master', '').replace('-main', '')
                    lines.append(f"{idx}. {clean_name}")
                    lines.append(f"   Score: {project.get('score', 0)}")
                    lines.append(f"   Primary Language: {project.get('primary_language', 'Unknown')}")
                    
                    if project.get('lines_of_code', 0) > 0:
                        lines.append(f"   Scale: {project.get('lines_of_code', 0):,} lines across {project.get('file_count', 0)} files")
                    
                    if project.get('frameworks'):
                        lines.append(f"   Frameworks: {', '.join(project.get('frameworks', []))}")
                    
                    if project.get('collaboration_level') and project.get('collaboration_level') != 'Unknown':
                        lines.append(f"   Collaboration: {project.get('collaboration_level')}")
                    
                    if project.get('code_quality_score', 0) > 0:
                        lines.append(f"   Code Quality Score: {project.get('code_quality_score', 0)}/100")
                    
                    highlights = []
                    if project.get('has_tests'):
                        highlights.append("Unit Testing")
                    if project.get('has_docs'):
                        highlights.append("Documentation")
                    if project.get('oop_principles_count', 0) > 0:
                        highlights.append(f"OOP Principles ({project.get('oop_principles_count')} instances)")
                    if project.get('optimization_count', 0) > 0:
                        highlights.append(f"Code Optimizations ({project.get('optimization_count')} patterns)")
                    
                    if highlights:
                        lines.append(f"   Highlights: {', '.join(highlights)}")
                    
                    project_skills = project.get('skills', [])
                    if project_skills:
                        lines.append(f"   Technologies: {', '.join(project_skills[:8])}")
                    
                    lines.append("")
            else:
                lines.append("  No projects to display")
                lines.append("")
            
            lines.append("=" * 70)
            lines.append(f"Generated: {resume_data.get('generated_at', 'Unknown')}")
            lines.append("=" * 70)
            
            return "\n".join(lines)
            
        except Exception as e:
            print(f"[ERROR] Error formatting resume as text: {e}")
            return None
    
    @staticmethod
    def format_pdf(resume_data, output_path):
        """
        Format resume as PDF document with structured sections.
        
        Uses reportlab library to create a professional PDF document
        with headers, sections, and proper formatting.
        
        Args:
            resume_data: Resume data dictionary
            output_path: Full path where PDF should be saved
            
        Returns:
            bool: True if PDF creation successful, False otherwise
        """
        try:
            if not resume_data:
                print("[ERROR] No resume data provided for PDF generation")
                return False
            
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib import colors
            from reportlab.platypus import (
                SimpleDocTemplate, 
                Paragraph, 
                Spacer, 
                Table, 
                TableStyle,
                HRFlowable
            )
            
            # Create document
            doc = SimpleDocTemplate(
                output_path,
                pagesize=letter,
                rightMargin=0.75 * inch,
                leftMargin=0.75 * inch,
                topMargin=0.75 * inch,
                bottomMargin=0.75 * inch
            )
            
            # Get base styles and create custom styles
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Title'],
                fontSize=24,
                spaceAfter=20,
                textColor=colors.HexColor('#2c3e50')
            )
            
            heading1_style = ParagraphStyle(
                'CustomHeading1',
                parent=styles['Heading1'],
                fontSize=16,
                spaceBefore=15,
                spaceAfter=10,
                textColor=colors.HexColor('#2c3e50'),
                borderColor=colors.HexColor('#3498db'),
                borderWidth=0,
                borderPadding=0
            )
            
            heading2_style = ParagraphStyle(
                'CustomHeading2',
                parent=styles['Heading2'],
                fontSize=12,
                spaceBefore=10,
                spaceAfter=5,
                textColor=colors.HexColor('#34495e')
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=6,
                leading=14
            )
            
            small_style = ParagraphStyle(
                'CustomSmall',
                parent=styles['Normal'],
                fontSize=9,
                spaceAfter=4,
                textColor=colors.HexColor('#7f8c8d')
            )
            
            # Build document content
            story = []
            
            # Title
            story.append(Paragraph("Resume", title_style))
            story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#3498db')))
            story.append(Spacer(1, 15))
            
            # Overview Section
            story.append(Paragraph("Overview", heading1_style))
            
            summary_stats = resume_data.get('summary_stats', {})
            overview_data = [
                ["Total Projects Analyzed:", str(resume_data.get('total_projects_analyzed', 0))],
                ["Top Projects Displayed:", str(resume_data.get('top_projects_displayed', 0))],
            ]
            if summary_stats:
                overview_data.extend([
                    ["Total Lines of Code:", f"{summary_stats.get('total_lines_of_code', 0):,}"],
                    ["Total Files:", f"{summary_stats.get('total_files', 0):,}"],
                    ["Unique Languages:", str(summary_stats.get('unique_languages', 0))],
                    ["Unique Frameworks:", str(summary_stats.get('unique_frameworks', 0))],
                ])
            
            overview_table = Table(overview_data, colWidths=[2.5 * inch, 4 * inch])
            overview_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#34495e')),
                ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#2c3e50')),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(overview_table)
            story.append(Spacer(1, 15))
            
            # Technical Skills Section
            story.append(Paragraph("Technical Skills", heading1_style))
            
            categorized_skills = resume_data.get('categorized_skills', {})
            if categorized_skills:
                for category, skill_list in categorized_skills.items():
                    if skill_list:
                        story.append(Paragraph(f"<b>{category}</b>", heading2_style))
                        skills_text = ", ".join(skill_list)
                        story.append(Paragraph(skills_text, normal_style))
            else:
                skills = resume_data.get('all_skills', [])
                if skills:
                    skills_text = ", ".join(skills)
                    story.append(Paragraph(skills_text, normal_style))
                else:
                    story.append(Paragraph("No skills identified", normal_style))
            
            story.append(Spacer(1, 10))
            
            # Programming Languages Section
            languages = resume_data.get('languages', [])
            if languages:
                story.append(Paragraph("Programming Languages", heading1_style))
                languages_text = ", ".join(languages)
                story.append(Paragraph(languages_text, normal_style))
                story.append(Spacer(1, 10))
            
            # Frameworks Section
            frameworks = resume_data.get('frameworks', [])
            if frameworks:
                story.append(Paragraph("Frameworks and Tools", heading1_style))
                frameworks_text = ", ".join(frameworks)
                story.append(Paragraph(frameworks_text, normal_style))
                story.append(Spacer(1, 10))
            
            # Top Projects Section
            story.append(Paragraph("Top Projects", heading1_style))
            
            top_projects = resume_data.get('top_projects', [])
            if top_projects:
                for idx, project in enumerate(top_projects, 1):
                    project_name = project.get('project_name', 'Unknown')
                    clean_name = project_name.replace('.zip', '').replace('-master', '').replace('-main', '')
                    
                    # Project header
                    story.append(Paragraph(f"<b>{idx}. {clean_name}</b>", heading2_style))
                    
                    # Project details table
                    project_details = []
                    
                    project_details.append(["Score:", f"{project.get('score', 0)}"])
                    project_details.append(["Primary Language:", project.get('primary_language', 'Unknown')])
                    
                    if project.get('lines_of_code', 0) > 0:
                        scale_text = f"{project.get('lines_of_code', 0):,} lines across {project.get('file_count', 0)} files"
                        project_details.append(["Scale:", scale_text])
                    
                    if project.get('frameworks'):
                        project_details.append(["Frameworks:", ", ".join(project.get('frameworks', []))])
                    
                    if project.get('collaboration_level') and project.get('collaboration_level') != 'Unknown':
                        project_details.append(["Collaboration:", project.get('collaboration_level')])
                    
                    if project.get('code_quality_score', 0) > 0:
                        project_details.append(["Code Quality:", f"{project.get('code_quality_score', 0)}/100"])
                    
                    # Build highlights
                    highlights = []
                    if project.get('has_tests'):
                        highlights.append("Unit Testing")
                    if project.get('has_docs'):
                        highlights.append("Documentation")
                    if project.get('oop_principles_count', 0) > 0:
                        highlights.append(f"OOP Principles ({project.get('oop_principles_count')})")
                    if project.get('optimization_count', 0) > 0:
                        highlights.append(f"Optimizations ({project.get('optimization_count')})")
                    
                    if highlights:
                        project_details.append(["Highlights:", ", ".join(highlights)])
                    
                    project_skills = project.get('skills', [])
                    if project_skills:
                        project_details.append(["Technologies:", ", ".join(project_skills[:6])])
                    
                    if project_details:
                        project_table = Table(project_details, colWidths=[1.5 * inch, 5 * inch])
                        project_table.setStyle(TableStyle([
                            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                            ('FONTSIZE', (0, 0), (-1, -1), 9),
                            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#7f8c8d')),
                            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#2c3e50')),
                            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                            ('TOPPADDING', (0, 0), (-1, -1), 3),
                            ('LEFTPADDING', (0, 0), (-1, -1), 15),
                        ]))
                        story.append(project_table)
                    
                    story.append(Spacer(1, 10))
            else:
                story.append(Paragraph("No projects to display", normal_style))
            
            # Footer with generation timestamp
            story.append(Spacer(1, 20))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#bdc3c7')))
            story.append(Spacer(1, 5))
            generated_at = resume_data.get('generated_at', 'Unknown')
            story.append(Paragraph(f"Generated: {generated_at}", small_style))
            
            # Build PDF
            doc.build(story)
            
            return True
            
        except ImportError as e:
            print(f"[ERROR] reportlab library not installed. Please install it with: pip install reportlab")
            print(f"[ERROR] Import error details: {e}")
            return False
        except Exception as e:
            print(f"[ERROR] Error generating PDF: {e}")
            return False
    
    @staticmethod
    def get_formatted_resume(resume_data, format_type='text'):
        """
        Get resume in specified format.
        
        Args:
            resume_data: Resume data dictionary
            format_type: Format type ('text', 'markdown', 'json')
            
        Returns:
            str: Formatted resume string or None if error
        """
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