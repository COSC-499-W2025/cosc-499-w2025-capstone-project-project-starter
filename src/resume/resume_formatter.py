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
            
            # Header with user name
            user_name = resume_data.get('user_name', 'Your Name')
            lines.append(f"# {user_name}")
            lines.append("")
            lines.append("---")
            lines.append("")
            
            # Skills section
            lines.append("## Technical Skills")
            lines.append("")
            
            categorized_skills = resume_data.get('categorized_skills', {})
            if categorized_skills:
                for category, skill_list in categorized_skills.items():
                    if skill_list:
                        lines.append(f"**{category}:** {', '.join(skill_list)}")
                        lines.append("")
            else:
                skills = resume_data.get('all_skills', [])
                if skills:
                    lines.append(", ".join(skills))
                else:
                    lines.append("No skills identified")
            lines.append("")
            
            # Projects section
            lines.append("## Projects")
            lines.append("")
            top_projects = resume_data.get('top_projects', [])
            
            if top_projects:
                for project in top_projects:
                    project_name = project.get('project_name', 'Unknown')
                    lines.append(f"### {project_name}")
                    
                    # Project date/period
                    first_file = project.get('first_file', '')
                    last_file = project.get('last_file', '')
                    if first_file and last_file:
                        if first_file == last_file:
                            lines.append(f"*{first_file}*")
                        else:
                            lines.append(f"*{first_file} - {last_file}*")
                    elif project.get('intensity') and project.get('intensity') != 'Unknown':
                        lines.append(f"*{project.get('intensity')}*")
                    
                    lines.append("")
                    
                    # Project description from database summary
                    project_summary = project.get('summary', '')
                    if project_summary:
                        # Clean up the summary text - extract meaningful content
                        summary_lines = project_summary.split('\n')
                        summary_count = 0
                        for summary_line in summary_lines:
                            summary_line = summary_line.strip()
                            # Skip separator lines, headers, and metadata
                            if (summary_line.startswith('=') or 
                                not summary_line or 
                                summary_line.isupper() and len(summary_line) > 30 or
                                summary_line.startswith('   Created:') or
                                'PROJECT SUMMARY' in summary_line.upper()):
                                continue
                            # Capture meaningful content lines
                            if len(summary_line) > 15:
                                lines.append(f"{summary_line}")
                                summary_count += 1
                                if summary_count >= 8:  # Limit to 8 lines
                                    break
                        if summary_count > 0:
                            lines.append("")
                    
                    # Technologies used
                    project_skills = project.get('skills', [])
                    if project_skills:
                        lines.append(f"**Technologies:** {', '.join(project_skills[:12])}")
                        lines.append("")
                    
                    # Evidence bullets if available
                    evidence = project.get('evidence', [])
                    if evidence:
                        lines.append("**Evidence:**")
                        for ev in evidence[:3]:
                            lines.append(f"- {ev}")
                        lines.append("")
                    
                    # Collaboration info if available
                    collab_level = project.get('collaboration_level', '')
                    if collab_level and collab_level != 'Unknown' and 'individual' not in collab_level.lower():
                        lines.append(f"*Collaborative project*")
                        lines.append("")
                    
                    lines.append("")
            else:
                lines.append("No projects to display")
                lines.append("")
            
            lines.append("---")
            lines.append(f"*Resume generated: {resume_data.get('generated_at', 'Unknown')[:10]}*")
            
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
            
            # Header with user name
            user_name = resume_data.get('user_name', 'Your Name')
            lines.append("=" * 70)
            lines.append(user_name.upper().center(70))
            lines.append("=" * 70)
            lines.append("")
            
            # Skills section
            lines.append("TECHNICAL SKILLS")
            lines.append("-" * 70)
            
            categorized_skills = resume_data.get('categorized_skills', {})
            if categorized_skills:
                for category, skill_list in categorized_skills.items():
                    if skill_list:
                        lines.append(f"{category}: {', '.join(skill_list)}")
                        lines.append("")
            else:
                skills = resume_data.get('all_skills', [])
                if skills:
                    lines.append(", ".join(skills))
                else:
                    lines.append("No skills identified")
            lines.append("")
            
            # Projects section
            lines.append("PROJECTS")
            lines.append("-" * 70)
            top_projects = resume_data.get('top_projects', [])
            
            if top_projects:
                for project in top_projects:
                    project_name = project.get('project_name', 'Unknown')
                    lines.append(f"{project_name.upper()}")
                    
                    # Project date/period
                    first_file = project.get('first_file', '')
                    last_file = project.get('last_file', '')
                    if first_file and last_file:
                        if first_file == last_file:
                            lines.append(f"  {first_file}")
                        else:
                            lines.append(f"  {first_file} - {last_file}")
                    elif project.get('intensity') and project.get('intensity') != 'Unknown':
                        lines.append(f"  {project.get('intensity')}")
                    
                    lines.append("")
                    
                    # Project description from database summary
                    project_summary = project.get('summary', '')
                    if project_summary:
                        # Clean up the summary text - extract meaningful content
                        summary_lines = project_summary.split('\n')
                        summary_count = 0
                        for summary_line in summary_lines:
                            summary_line = summary_line.strip()
                            # Skip separator lines, headers, and metadata
                            if (summary_line.startswith('=') or 
                                not summary_line or 
                                summary_line.isupper() and len(summary_line) > 30 or
                                summary_line.startswith('   Created:') or
                                'PROJECT SUMMARY' in summary_line.upper()):
                                continue
                            # Capture meaningful content lines
                            if len(summary_line) > 15:
                                # Wrap long lines
                                if len(summary_line) > 65:
                                    words = summary_line.split()
                                    current_line = "  "
                                    for word in words:
                                        if len(current_line) + len(word) + 1 > 65:
                                            lines.append(current_line)
                                            current_line = "  " + word
                                        else:
                                            current_line += " " + word if current_line != "  " else word
                                    if current_line.strip():
                                        lines.append(current_line)
                                else:
                                    lines.append(f"  {summary_line}")
                                summary_count += 1
                                if summary_count >= 8:  # Limit to 8 lines
                                    break
                        if summary_count > 0:
                            lines.append("")
                    
                    # Technologies used
                    project_skills = project.get('skills', [])
                    if project_skills:
                        lines.append(f"  Technologies: {', '.join(project_skills[:12])}")
                        lines.append("")
                    
                    # Evidence bullets if available
                    evidence = project.get('evidence', [])
                    if evidence:
                        lines.append("  Evidence:")
                        for ev in evidence[:3]:
                            lines.append(f"   - {ev}")
                        lines.append("")

                    # Collaboration info if available
                    collab_level = project.get('collaboration_level', '')
                    if collab_level and collab_level != 'Unknown' and 'individual' not in collab_level.lower():
                        lines.append(f"  Collaborative project")
                        lines.append("")
                    
                    lines.append("")
            else:
                lines.append("  No projects to display")
                lines.append("")
            
            lines.append("=" * 70)
            lines.append(f"Resume generated: {resume_data.get('generated_at', 'Unknown')[:10]}")
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
            
            # Header with user name
            user_name = resume_data.get('user_name', 'Your Name')
            story.append(Paragraph(user_name, title_style))
            story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#3498db')))
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
            
            # Projects Section
            story.append(Paragraph("Projects", heading1_style))
            
            top_projects = resume_data.get('top_projects', [])
            if top_projects:
                for project in top_projects:
                    project_name = project.get('project_name', 'Unknown')
                    
                    # Project header
                    story.append(Paragraph(f"<b>{project_name}</b>", heading2_style))
                    
                    # Project date/period
                    first_file = project.get('first_file', '')
                    last_file = project.get('last_file', '')
                    date_text = ""
                    if first_file and last_file:
                        if first_file == last_file:
                            date_text = first_file
                        else:
                            date_text = f"{first_file} - {last_file}"
                    elif project.get('intensity') and project.get('intensity') != 'Unknown':
                        date_text = project.get('intensity')
                    
                    if date_text:
                        story.append(Paragraph(f"<i>{date_text}</i>", small_style))
                    
                    story.append(Spacer(1, 5))
                    
                    # Project description from database summary
                    project_summary = project.get('summary', '')
                    if project_summary:
                        # Clean up the summary text - extract meaningful content
                        summary_lines = project_summary.split('\n')
                        summary_count = 0
                        in_content_section = False
                        for summary_line in summary_lines:
                            summary_line = summary_line.strip()
                            # Skip separator lines and headers
                            if summary_line.startswith('=') or not summary_line:
                                continue
                            # Skip section headers that are all caps or have specific patterns
                            if summary_line.isupper() and len(summary_line) > 30:
                                continue
                            # Start capturing after project info section
                            if 'PROJECT SUMMARY' in summary_line.upper() or 'OVERVIEW' in summary_line.upper():
                                in_content_section = True
                                continue
                            # Capture meaningful content lines
                            if len(summary_line) > 15 and not summary_line.startswith('   Created:'):
                                # Escape HTML and add paragraph
                                summary_line_escaped = summary_line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                                story.append(Paragraph(summary_line_escaped, normal_style))
                                summary_count += 1
                                if summary_count >= 8:  # Limit to 8 paragraphs
                                    break
                        if summary_count > 0:
                            story.append(Spacer(1, 5))
                    
                    # Technologies used
                    project_skills = project.get('skills', [])
                    if project_skills:
                        tech_text = f"<b>Technologies:</b> {', '.join(project_skills[:12])}"
                        story.append(Paragraph(tech_text, normal_style))
                        story.append(Spacer(1, 5))
                    
                    # Evidence bullets if available
                    evidence = project.get('evidence', [])
                    if evidence:
                        story.append(Paragraph("<b>Evidence:</b>", normal_style))
                        for ev in evidence[:3]:
                            ev_escaped = ev.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                            story.append(Paragraph(ev_escaped, normal_style))
                        story.append(Spacer(1, 5))

                    # Collaboration info if available
                    collab_level = project.get('collaboration_level', '')
                    if collab_level and collab_level != 'Unknown' and 'individual' not in collab_level.lower():
                        story.append(Paragraph("<i>Collaborative project</i>", small_style))
                        story.append(Spacer(1, 5))
                    
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