"""
Portfolio Formatter Module

Formats portfolio data into human-readable output formats AND structured API responses.
"""

import json
from typing import Dict, Any, Optional, List
from src.common.schemas import PortfolioCardResponse, TechStack

class PortfolioFormatter:
    """Formats portfolio data into various output formats."""
    
    @staticmethod
    def format_text(portfolio_data: Dict[str, Any]) -> Optional[str]:
        """
        Format portfolio as plain text.
        
        Args:
            portfolio_data: Portfolio data dictionary
            
        Returns:
            Formatted text string or None if error
        """
        try:
            if not portfolio_data or not isinstance(portfolio_data, dict):
                return "ERROR: Invalid portfolio data"
            if 'error' in portfolio_data:
                return f"ERROR: {portfolio_data.get('error', 'Unknown error')}"
            
            lines = []
            
            # Welcome introduction
            summary = portfolio_data.get('summary', {})
            total_projects = summary.get('total_projects', 0)
            total_files = summary.get('total_files', 0)
            total_lines = summary.get('total_lines_of_code', 0)
            total_size = summary.get('total_size_mb', 0)
            
            lines.append("=" * 80)
            lines.append("PORTFOLIO OVERVIEW")
            lines.append("=" * 80)
            lines.append("")
            lines.append(f"This portfolio represents {total_projects} projects, containing")
            lines.append(f"{total_files:,} files and {total_lines:,} lines of code")
            lines.append(f"({total_size:.1f} MB total).")
            lines.append("")
            lines.append("Each project below represents a unique challenge and learning opportunity.")
            lines.append("These works demonstrate my ability to design, implement, and deliver")
            lines.append("quality software solutions.")
            lines.append("")
            
            # Technical Expertise
            skills_data = portfolio_data.get('skills', {})
            categorized = skills_data.get('categorized', {})
            languages = skills_data.get('languages', [])
            frameworks = skills_data.get('frameworks', [])
            
            lines.append("=" * 80)
            lines.append("TECHNICAL EXPERTISE")
            lines.append("=" * 80)
            lines.append("")
            lines.append("My technical expertise spans multiple domains, with proficiency in:")
            lines.append("")
            
            if categorized:
                for category, skill_list in categorized.items():
                    if skill_list:
                        lines.append(f"{category}:")
                        lines.append(f"  {', '.join(skill_list)}")
                        lines.append("")
            
            if languages:
                lines.append(f"Programming Languages: {', '.join(languages)}")
                lines.append("")
            
            if frameworks:
                lines.append(f"Frameworks & Tools: {', '.join(frameworks)}")
                lines.append("")
            
            # Featured Projects
            projects = portfolio_data.get('projects', [])
            lines.append("=" * 80)
            lines.append("FEATURED PROJECTS")
            lines.append("=" * 80)
            lines.append("")
            lines.append("Below are detailed descriptions of my key projects, showcasing")
            lines.append("technical skills, problem-solving abilities, and development practices.")
            lines.append("")
            
            for idx, project in enumerate(projects, 1):
                lines.append(f"{idx}. {project.get('name', 'Unknown')}")
                lines.append("-" * 80)
                
                # Show humanized summary first
                project_summary = project.get('summary', '')
                if project_summary:
                    lines.append("")
                    lines.append(f"   {project_summary}")
                    lines.append("")
                
                # Technical details in a more narrative way
                primary_lang = project.get('primary_language', 'Unknown')
                languages = project.get('languages', [])
                file_count = project.get('file_count', 0)
                lines_code = project.get('lines_of_code', 0)
                
                tech_details = []
                if primary_lang != 'Unknown':
                    tech_details.append(f"Built with {primary_lang}")
                    if len(languages) > 1:
                        other_langs = [l for l in languages if l != primary_lang]
                        if other_langs:
                            tech_details.append(f"and {', '.join(other_langs[:2])}")
                
                if tech_details:
                    lines.append(f"   {' '.join(tech_details)}.")
                
                if lines_code > 0:
                    lines.append(f"   Scale: {lines_code:,} lines of code across {file_count} files.")
                
                # Show key skills for this project
                project_skills = project.get('skills', [])
                if project_skills:
                    top_skills = project_skills[:5]
                    skill_line = ", ".join(top_skills)
                    if len(skill_line) > 70:
                        skill_line = skill_line[:67] + "..."
                    lines.append(f"   Key Technologies: {skill_line}")
                
                # Show project features in narrative form
                features = []
                if project.get('has_tests'):
                    features.append("comprehensive testing")
                if project.get('has_docs'):
                    features.append("documentation")
                quality_score = project.get('code_quality_score', 0)
                if quality_score > 75:
                    features.append("high code quality")
                
                if features:
                    lines.append(f"   Highlights: {', '.join(features)}.")
                
                # Show collaboration if available
                collab_analysis = project.get('collaboration_analysis', '')
                if collab_analysis:
                    lines.append(f"   {collab_analysis}")
                
                lines.append("")
            
            return "\n".join(lines)
            
        except Exception as e:
            print(f"[ERROR] Error formatting portfolio as text: {e}")
            return None
    
    @staticmethod
    def format_markdown(portfolio_data: Dict[str, Any]) -> Optional[str]:
        """
        Format portfolio as Markdown with humanized and analytical mix.
        
        Args:
            portfolio_data: Portfolio data dictionary
            
        Returns:
            Formatted Markdown string or None if error
        """
        try:
            if not portfolio_data or not isinstance(portfolio_data, dict):
                return "# ERROR\n\nInvalid portfolio data"
            if 'error' in portfolio_data:
                return f"# ERROR\n\n{portfolio_data.get('error', 'Unknown error')}"
            
            lines = []
            
            # Header
            summary = portfolio_data.get('summary', {})
            total_projects = summary.get('total_projects', 0)
            total_files = summary.get('total_files', 0)
            total_lines = summary.get('total_lines_of_code', 0)
            total_size = summary.get('total_size_mb', 0)
            
            lines.append("# Portfolio")
            lines.append("")
            lines.append(f"This portfolio represents **{total_projects} projects**, containing")
            lines.append(f"**{total_files:,} files** and **{total_lines:,} lines of code**")
            lines.append(f"({total_size:.1f} MB total).")
            lines.append("")
            lines.append("Each project below represents a unique challenge and learning opportunity.")
            lines.append("These works demonstrate my ability to design, implement, and deliver")
            lines.append("quality software solutions.")
            lines.append("")
            
            # Technical Expertise
            skills_data = portfolio_data.get('skills', {})
            categorized = skills_data.get('categorized', {})
            languages = skills_data.get('languages', [])
            frameworks = skills_data.get('frameworks', [])
            
            lines.append("## Technical Expertise")
            lines.append("")
            lines.append("My technical expertise spans multiple domains, with proficiency in:")
            lines.append("")
            
            if categorized:
                for category, skill_list in categorized.items():
                    if skill_list:
                        lines.append(f"### {category}")
                        lines.append(f"{', '.join(skill_list)}")
                        lines.append("")
            
            if languages:
                lines.append(f"**Programming Languages:** {', '.join(languages)}")
                lines.append("")
            
            if frameworks:
                lines.append(f"**Frameworks & Tools:** {', '.join(frameworks)}")
                lines.append("")
            
            # Featured Projects
            projects = portfolio_data.get('projects', [])
            lines.append("## Featured Projects")
            lines.append("")
            lines.append("Below are detailed descriptions of my key projects, showcasing")
            lines.append("technical skills, problem-solving abilities, and development practices.")
            lines.append("")
            
            for idx, project in enumerate(projects, 1):
                clean_name = project.get('name', 'Unknown').replace('.zip', '').replace('-master', '').replace('-main', '')
                lines.append(f"### {idx}. {clean_name}")
                lines.append("")
                
                # Show humanized summary first
                project_summary = project.get('summary', '')
                if project_summary:
                    lines.append(f"{project_summary}")
                    lines.append("")
                
                # Technical details
                primary_lang = project.get('primary_language', 'Unknown')
                languages = project.get('languages', [])
                file_count = project.get('file_count', 0)
                lines_code = project.get('lines_of_code', 0)
                
                if primary_lang != 'Unknown':
                    lang_text = f"**Built with:** {primary_lang}"
                    if len(languages) > 1:
                        other_langs = [l for l in languages if l != primary_lang]
                        if other_langs:
                            lang_text += f" and {', '.join(other_langs[:2])}"
                    lines.append(lang_text)
                
                if lines_code > 0:
                    lines.append(f"**Scale:** {lines_code:,} lines of code across {file_count} files")
                
                # Show key skills for this project
                project_skills = project.get('skills', [])
                if project_skills:
                    top_skills = project_skills[:8]
                    lines.append(f"**Key Technologies:** {', '.join(top_skills)}")
                
                # Show project features
                features = []
                if project.get('has_tests'):
                    features.append("comprehensive testing")
                if project.get('has_docs'):
                    features.append("documentation")
                quality_score = project.get('code_quality_score', 0)
                if quality_score > 75:
                    features.append("high code quality")
                
                if features:
                    lines.append(f"**Highlights:** {', '.join(features)}")
                
                # Show collaboration if available
                collab_analysis = project.get('collaboration_analysis', '')
                if collab_analysis:
                    lines.append(f"**Collaboration:** {collab_analysis}")
                
                lines.append("")
            
            return "\n".join(lines)
            
        except Exception as e:
            print(f"[ERROR] Error formatting portfolio as Markdown: {e}")
            return None
    
    @staticmethod
    def get_formatted_portfolio(portfolio_data: Dict[str, Any], format_type: str = 'text') -> Optional[str]:
        """
        Get portfolio in specified format.
        
        Args:
            portfolio_data: Portfolio data dictionary
            format_type: Format type ('text', 'markdown')
            
        Returns:
            Formatted portfolio string or None if error
        """
        format_type = format_type.lower().strip()
        
        if format_type == 'markdown':
            return PortfolioFormatter.format_markdown(portfolio_data)
        elif format_type == 'text':
            return PortfolioFormatter.format_text(portfolio_data)
        else:
            print(f"[ERROR] Unknown format type: {format_type}. Using text format.")
            return PortfolioFormatter.format_text(portfolio_data)
    @staticmethod
    def format_project_card(project_data: Dict[str, Any]) -> PortfolioCardResponse:
        """
        Transforms raw project analysis data into a rich Portfolio Showcase Card.
        Fulfills Milestone 2 Requirement: 'Display textual information about a project as a portfolio showcase'
        
        Args:
            project_data (dict): Single project dictionary from ProjectAnalyzer.
            
        Returns:
            PortfolioCardResponse: Pydantic model for API response.
        """
        # 1. Basic Info Extraction
        info = project_data.get('project_info', {})
        # Use filename as fallback title if needed
        raw_name = info.get('filename', 'Untitled Project')
        clean_title = PortfolioFormatter._clean_title_helper(raw_name)
        
        # 2. Descriptions (Elevator Pitch vs Full)
        # In a real scenario, these might come from an LLM summary. 
        # For now, we generate a structured summary based on stats.
        stats = project_data.get('file_statistics', {})
        total_loc = stats.get('total_lines_of_code', 0)
        file_count = stats.get('total_files', 0)
        
        short_desc = f"A robust software solution comprising {file_count} modules and {total_loc}+ lines of code."
        
        primary_lang = project_data.get('languages', {}).get('primary_language', 'Code')
        full_desc = (
            f"{clean_title} is a specialized application developed primarily in {primary_lang}. "
            f"It demonstrates best practices in software engineering, handling {file_count} files "
            f"and optimizing performance across the {total_loc} line codebase."
        )

        # 3. Tech Stack Mapping
        technologies = PortfolioFormatter._map_technologies(project_data)

        # 4. Success Metrics (Evidence of Success)
        metrics = PortfolioFormatter._generate_success_metrics(project_data)

        # 5. Collaborators (Placeholder until integrated with identifying_contributors.py)
        # Check if 'collaboration_analysis' exists in the input dictionary
        collaborators = project_data.get('collaboration_analysis', {}).get('contributors', [])

        return PortfolioCardResponse(
            project_id=f"proj_{info.get('id', 0)}", # Simple ID generation
            title=clean_title,
            short_description=short_desc,
            full_description=full_desc,
            image_url=None, # Placeholder: Evan's Image Module will inject this later
            my_role="Lead Developer", # Default: Eric's User Prefs will override this later
            collaborators=collaborators,
            success_metrics=metrics,
            technologies=technologies
        )

    @staticmethod
    def _clean_title_helper(filename: str) -> str:
        """Helper: Standardizes repository names into titles."""
        name = filename
        for suffix in ['.zip', '-main', '-master', '_main']:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
        return name.replace('_', ' ').replace('-', ' ').title()

    @staticmethod
    def _map_technologies(data: Dict[str, Any]) -> List[TechStack]:
        """Helper: Converts raw string lists into typed TechStack objects."""
        tech_list = []
        
        # Add Languages
        langs = data.get('languages', {}).get('detected_languages', [])
        for lang in langs:
            tech_list.append(TechStack(name=lang, category="Language"))
            
        # Add Frameworks
        frameworks = data.get('frameworks', [])
        # Handle if frameworks is dict (occurrence count) or list
        if isinstance(frameworks, dict):
            frameworks = list(frameworks.keys())
            
        for fw in frameworks:
            tech_list.append(TechStack(name=fw, category="Framework"))
            
        return tech_list[:8] # Cap at 8 tags for visual clarity

    @staticmethod
    def _generate_success_metrics(data: Dict[str, Any]) -> List[str]:
        """
        Helper: Derives 'Evidence of Success' from static analysis metrics.
        Fulfills Milestone 2 Requirement: 'Incorporate evidence of success'
        """
        metrics = []
        structure = data.get('project_structure', {})
        stats = data.get('file_statistics', {})
        
        # Metric 1: Scale
        if stats.get('total_lines_of_code', 0) > 1000:
            metrics.append("Large Scale Architecture")
            
        # Metric 2: Reliability
        if structure.get('has_tests'):
            metrics.append("Verified Reliability (Unit Tests)")
            
        # Metric 3: Documentation
        if structure.get('has_docs'):
            metrics.append("Well Documented")
            
        # Metric 4: Complexity (Mock logic)
        if len(data.get('languages', {}).get('detected_languages', [])) > 2:
            metrics.append("Multi-Language Integration")
            
        return metrics