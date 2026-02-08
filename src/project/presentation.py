"""
Portfolio and Resume Item Generation

This module generates structured, human-facing summaries for projects analyzed
by the artifact pipeline. It is pure (no I/O, no LLM, no DB) and template-based.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.insights.storage import ProjectInsightsStore


@dataclass
class PortfolioItem:
    """
    Structured portfolio item suitable for a personal portfolio site
    """
    project_name: str
    tagline: str
    description: str
    languages: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    is_collaborative: bool = False
    total_commits: int = 0
    total_lines: int = 0
    # Additional fields
    project_type: str = "Software Project"
    complexity: str = "Medium"
    key_features: List[str] = field(default_factory=list)
    has_documentation: bool = False
    has_tests: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to plain dictionary"""
        return asdict(self)


@dataclass
class ResumeItem:
    """
    Structured resume item containing bullet points for a CV
    """
    project_name: str
    bullets: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to plain dictionary"""
        return asdict(self)


@dataclass
class ProjectMetrics:
    """
    Extracted metrics from a project analysis dict
    """
    languages: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    total_files: int = 0
    total_lines: int = 0
    total_commits: int = 0
    total_contributors: int = 0
    is_collaborative: bool = False
    # Additional metrics
    doc_files: int = 0
    doc_words: int = 0
    image_files: int = 0
    video_files: int = 0
    test_files: int = 0
    has_documentation: bool = False
    has_images: bool = False
    has_videos: bool = False
    has_tests: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to a plain dictionary for storage/serialization."""
        return asdict(self)


def extract_project_metrics(project_dict: Dict[str, Any]) -> ProjectMetrics:
    """
    Extract comprehensive metrics from a project result dict produced by _process_project()
    
    Args:
        project_dict: Project result dictionary from ArtifactPipeline._process_project()
        
    Returns:
        ProjectMetrics with safely extracted values (defaults to empty/zero on missing data)
    """
    metrics = ProjectMetrics()
    
    # Extract from analysis_results -> code -> metrics
    try:
        analysis_results = project_dict.get('analysis_results', {})
        if isinstance(analysis_results, dict):
            code_analysis = analysis_results.get('code')
            if isinstance(code_analysis, dict) and 'error' not in code_analysis:
                code_metrics = code_analysis.get('metrics', {})
                if isinstance(code_metrics, dict):
                    metrics.languages = code_metrics.get('languages', [])
                    metrics.frameworks = code_metrics.get('frameworks', [])
                    metrics.skills = code_metrics.get('skills', [])
                    metrics.total_files = code_metrics.get('total_files', 0)
                    metrics.total_lines = code_metrics.get('total_lines', 0)
                    metrics.test_files = code_metrics.get('test_files', 0)
                    metrics.has_tests = metrics.test_files > 0
    except (AttributeError, TypeError, KeyError):
        # If any access fails, keep defaults
        pass
    
    # Extract documentation metrics
    try:
        analysis_results = project_dict.get('analysis_results', {})
        if isinstance(analysis_results, dict):
            doc_analysis = analysis_results.get('documentation')
            if isinstance(doc_analysis, dict) and 'error' not in doc_analysis:
                doc_totals = doc_analysis.get('totals', {})
                if isinstance(doc_totals, dict):
                    metrics.doc_files = doc_totals.get('total_files', 0)
                    metrics.doc_words = doc_totals.get('total_words', 0)
                    metrics.has_documentation = metrics.doc_files > 0
    except (AttributeError, TypeError, KeyError):
        pass
    
    # Extract image/video metrics from categorized_contents
    try:
        categorized = project_dict.get('categorized_contents', {})
        if isinstance(categorized, dict):
            metrics.image_files = len(categorized.get('images', []))
            metrics.has_images = metrics.image_files > 0
            
            # Count videos in 'other' category
            other_files = categorized.get('other', [])
            if isinstance(other_files, list):
                video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.wmv'}
                metrics.video_files = sum(
                    1 for f in other_files 
                    if isinstance(f, str) and any(f.lower().endswith(ext) for ext in video_extensions)
                )
                metrics.has_videos = metrics.video_files > 0
    except (AttributeError, TypeError, KeyError):
        pass
    
    # Extract from git_analysis
    try:
        git_analysis = project_dict.get('git_analysis')
        if isinstance(git_analysis, dict) and 'error' not in git_analysis:
            metrics.total_commits = git_analysis.get('total_commits', 0)
            metrics.total_contributors = git_analysis.get('total_contributors', 0)
            # is_collaborative if more than 1 contributor
            metrics.is_collaborative = metrics.total_contributors > 1
    except (AttributeError, TypeError, KeyError):
        # If any access fails, keep defaults
        pass
    
    return metrics


def generate_portfolio_item(
    project_dict: Dict[str, Any],
    metrics: Optional[ProjectMetrics] = None,
) -> Dict[str, Any]:
    """
    Generate a portfolio item from a project analysis dict
    
    Args:
        project_dict: Project result dictionary from ArtifactPipeline._process_project()
        metrics: Optional pre-extracted metrics to avoid recomputation
        
    Returns:
        Dictionary representation of a PortfolioItem
    """
    # Extract project name safely
    project_name = project_dict.get('project_name', 'Unnamed Project')
    
    # Extract metrics
    metrics = metrics or extract_project_metrics(project_dict)
    
    # Build tagline
    tagline = _build_tagline(metrics)
    
    # Build description
    description = _build_description(metrics)
    
    # Determine project type
    project_type = _determine_project_type(metrics)
    
    # Determine complexity
    complexity = _determine_complexity(metrics)
    
    # Extract key features
    key_features = _extract_key_features(metrics)
    
    # Create portfolio item
    portfolio = PortfolioItem(
        project_name=project_name,
        tagline=tagline,
        description=description,
        languages=metrics.languages[:10],  # Limit to top 10
        frameworks=metrics.frameworks[:10],  # Limit to top 10
        skills=metrics.skills[:15],  # Limit to top 15
        is_collaborative=metrics.is_collaborative,
        total_commits=metrics.total_commits,
        total_lines=metrics.total_lines,
        project_type=project_type,
        complexity=complexity,
        key_features=key_features,
        has_documentation=metrics.has_documentation,
        has_tests=metrics.has_tests
    )
    
    return portfolio.to_dict()


def apply_resume_item_customization(
    resume_item: Dict[str, Any],
    customization: Dict[str, Any],
    *,
    max_bullets: int = 6,
) -> Dict[str, Any]:
    """
    Apply non-persistent customization to a resume item (pure function, no mutation)
    
    This function allows runtime override/editing of resume bullet wording and project name
    without any database persistence. Useful for UI-driven customization workflows.
    
    Args:
        resume_item: Resume item dict with "project_name" (str) and "bullets" (List[str])
        customization: Customization dict with optional keys:
            - "project_name": Optional[str] - Override project name if present and non-empty
            - "bullets": Optional[List[str]] - Replace entire bullets list (highest precedence)
            - "edits": Optional[List[Dict]] - Apply index-based edits to existing bullets
                Each edit: {"index": int, "text": str}
        max_bullets: Maximum number of bullets allowed (default 6)
    
    Returns:
        New resume item dict with customizations applied (original not mutated)
    
    Raises:
        TypeError: If resume_item or customization are not dicts
        ValueError: If resume_item is invalid or customization contains invalid data
    
    Examples:
        >>> item = {"project_name": "Cool Project", "bullets": ["Built X", "Improved Y"]}
        >>> custom = {"edits": [{"index": 1, "text": "Improved Y by 25%"}]}
        >>> apply_resume_item_customization(item, custom)
        {"project_name": "Cool Project", "bullets": ["Built X", "Improved Y by 25%"]}
    """
    # Validate inputs
    if not isinstance(resume_item, dict):
        raise TypeError(f"resume_item must be a dict, got {type(resume_item).__name__}")
    if not isinstance(customization, dict):
        raise TypeError(f"customization must be a dict, got {type(customization).__name__}")
    
    # Validate resume_item structure
    if "project_name" not in resume_item:
        raise ValueError("resume_item must contain 'project_name' key")
    if not isinstance(resume_item.get("project_name"), str):
        raise ValueError("resume_item['project_name'] must be a string")
    
    if "bullets" not in resume_item:
        raise ValueError("resume_item must contain 'bullets' key")
    if not isinstance(resume_item.get("bullets"), list):
        raise ValueError("resume_item['bullets'] must be a list")
    if len(resume_item["bullets"]) == 0:
        raise ValueError("resume_item['bullets'] cannot be empty")
    if not all(isinstance(b, str) for b in resume_item["bullets"]):
        raise ValueError("All items in resume_item['bullets'] must be strings")
    
    # Start with a copy of the original
    result = {
        "project_name": resume_item["project_name"],
        "bullets": list(resume_item["bullets"])  # Shallow copy
    }
    
    # Apply project_name override if present
    custom_name = customization.get("project_name")
    if custom_name is not None:
        if not isinstance(custom_name, str):
            raise ValueError("customization['project_name'] must be a string")
        custom_name_stripped = custom_name.strip()
        if custom_name_stripped:
            result["project_name"] = custom_name_stripped
    
    # Apply bullets customization (highest precedence)
    custom_bullets = customization.get("bullets")
    if custom_bullets is not None:
        if not isinstance(custom_bullets, list):
            raise ValueError("customization['bullets'] must be a list")
        
        # Strip and filter empty bullets
        cleaned_bullets = []
        for bullet in custom_bullets:
            if not isinstance(bullet, str):
                raise ValueError("All items in customization['bullets'] must be strings")
            stripped = bullet.strip()
            if stripped:
                cleaned_bullets.append(stripped)
        
        if len(cleaned_bullets) == 0:
            raise ValueError("customization['bullets'] must contain at least one non-empty bullet after stripping")
        if len(cleaned_bullets) > max_bullets:
            raise ValueError(f"customization['bullets'] cannot exceed {max_bullets} bullets, got {len(cleaned_bullets)}")
        
        result["bullets"] = cleaned_bullets
    else:
        # Apply edits if bullets override not present
        custom_edits = customization.get("edits")
        if custom_edits is not None:
            if not isinstance(custom_edits, list):
                raise ValueError("customization['edits'] must be a list")
            
            for edit in custom_edits:
                if not isinstance(edit, dict):
                    raise ValueError("Each edit in customization['edits'] must be a dict")
                if "index" not in edit:
                    raise ValueError("Each edit must contain 'index' key")
                if "text" not in edit:
                    raise ValueError("Each edit must contain 'text' key")
                
                index = edit["index"]
                text = edit["text"]
                
                if not isinstance(index, int):
                    raise ValueError(f"Edit index must be an integer, got {type(index).__name__}")
                if not isinstance(text, str):
                    raise ValueError(f"Edit text must be a string, got {type(text).__name__}")
                
                if index < 0 or index >= len(result["bullets"]):
                    raise ValueError(f"Edit index {index} out of range [0, {len(result['bullets'])-1}]")
                
                text_stripped = text.strip()
                if not text_stripped:
                    raise ValueError(f"Edit text at index {index} cannot be empty after stripping")
                
                result["bullets"][index] = text_stripped
    
    return result


def generate_resume_item(
    project_dict: Dict[str, Any],
    metrics: Optional[ProjectMetrics] = None,
    customization: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate a resume item with 2-3 bullet points from a project analysis dict
    
    Args:
        project_dict: Project result dictionary from ArtifactPipeline._process_project()
        metrics: Optional pre-extracted metrics to avoid recomputation
        customization: Optional customization dict to override/edit resume item wording
            (non-persistent, runtime-only). See apply_resume_item_customization for schema.
        
    Returns:
        Dictionary representation of a ResumeItem
    """
    # Extract project name safely
    project_name = project_dict.get('project_name', 'Unnamed Project')
    
    # Extract metrics
    metrics = metrics or extract_project_metrics(project_dict)
    
    # Build bullets
    bullets = _build_resume_bullets(metrics)
    
    # Create resume item
    resume = ResumeItem(
        project_name=project_name,
        bullets=bullets
    )
    
    resume_dict = resume.to_dict()
    
    # Apply customization if provided
    if customization:
        resume_dict = apply_resume_item_customization(resume_dict, customization)
    
    return resume_dict


def _build_tagline(metrics: ProjectMetrics) -> str:
    """
    Build a one-line tagline for a project with more variety and context
    
    Args:
        metrics: Extracted project metrics
        
    Returns:
        Short tagline string
    """
    # Determine collaboration type with more variety
    if metrics.is_collaborative:
        collab_phrases = ["Collaborative", "Team-based", "Multi-contributor"]
        collab_type = collab_phrases[metrics.total_contributors % len(collab_phrases)]
    else:
        collab_type = "Individual"
    
    # Get primary language(s) - up to 2
    lang_phrase = ""
    if metrics.languages:
        if len(metrics.languages) == 1:
            lang_phrase = metrics.languages[0]
        elif len(metrics.languages) == 2:
            lang_phrase = f"{metrics.languages[0]} and {metrics.languages[1]}"
        else:
            lang_phrase = f"multi-language ({metrics.languages[0]}, {metrics.languages[1]})"
    else:
        lang_phrase = "software"
    
    # Get framework mention - up to 2
    framework_phrase = ""
    if metrics.frameworks:
        if len(metrics.frameworks) == 1:
            framework_phrase = f" using {metrics.frameworks[0]}"
        elif len(metrics.frameworks) >= 2:
            framework_phrase = f" using {metrics.frameworks[0]} and {metrics.frameworks[1]}"
    
    # Add project type indicator if available
    type_indicator = ""
    if metrics.has_tests:
        type_indicator = " (tested)"
    elif metrics.has_documentation and metrics.doc_words > 500:
        type_indicator = " (well-documented)"
    
    return f"{collab_type} {lang_phrase} project{framework_phrase}{type_indicator}"


def _build_description(metrics: ProjectMetrics) -> str:
    """
    Build an engaging 1-2 sentence description for a project
    
    Args:
        metrics: Extracted project metrics
        
    Returns:
        Description string
    """
    sentences = []
    
    # First sentence: Scale and scope
    if metrics.total_files > 0 or metrics.total_lines > 0:
        scale_parts = []
        if metrics.total_files > 0:
            scale_parts.append(f"{metrics.total_files} source file{'s' if metrics.total_files != 1 else ''}")
        if metrics.total_lines > 0:
            scale_parts.append(f"{metrics.total_lines:,} lines of code")
        
        if scale_parts:
            scale_str = " and ".join(scale_parts)
            sentences.append(f"A comprehensive project comprising {scale_str}.")
    
    # Second sentence: Quality indicators and collaboration
    quality_parts = []
    if metrics.has_tests:
        quality_parts.append("includes comprehensive test coverage")
    if metrics.has_documentation and metrics.doc_words > 500:
        quality_parts.append("features extensive documentation")
    if metrics.is_collaborative:
        quality_parts.append(f"developed collaboratively by {metrics.total_contributors} contributor{'s' if metrics.total_contributors != 1 else ''}")
    if metrics.total_commits > 50:
        quality_parts.append(f"maintained through {metrics.total_commits} Git commits")
    
    if quality_parts:
        quality_str = ", ".join(quality_parts)
        sentences.append(f"The project {quality_str}.")
    
    # Fallback if no metrics available
    if not sentences:
        return "A software project analyzed through automated artifact pipeline processing."
    
    return " ".join(sentences)


def _determine_project_type(metrics: ProjectMetrics) -> str:
    """
    Determine the project type based on technologies and structure
    
    Args:
        metrics: Extracted project metrics
        
    Returns:
        Project type string
    """
    # Web projects
    web_frameworks = {'react', 'vue', 'angular', 'django', 'flask', 'express', 'spring', 'rails', 'laravel'}
    if any(fw.lower() in web_frameworks for fw in metrics.frameworks):
        return "Web Application"
    
    # Mobile projects
    mobile_frameworks = {'react native', 'flutter', 'swift', 'kotlin', 'xamarin', 'ionic'}
    if any(fw.lower() in mobile_frameworks for fw in metrics.frameworks):
        return "Mobile Application"
    
    # Data/ML projects
    data_languages = {'python', 'r', 'julia'}
    data_frameworks = {'tensorflow', 'pytorch', 'pandas', 'numpy', 'scikit-learn', 'keras'}
    if any(lang.lower() in data_languages for lang in metrics.languages) or \
       any(fw.lower() in data_frameworks for fw in metrics.frameworks):
        return "Data Science / ML Project"
    
    # API/Backend projects
    backend_frameworks = {'express', 'fastapi', 'django', 'flask', 'spring', 'rails', 'laravel', 'asp.net'}
    if any(fw.lower() in backend_frameworks for fw in metrics.frameworks):
        return "Backend / API Service"
    
    # Game development
    game_frameworks = {'unity', 'unreal', 'godot', 'phaser'}
    if any(fw.lower() in game_frameworks for fw in metrics.frameworks):
        return "Game Development"
    
    # Default
    return "Software Project"


def _determine_complexity(metrics: ProjectMetrics) -> str:
    """
    Determine project complexity based on metrics
    
    Args:
        metrics: Extracted project metrics
        
    Returns:
        Complexity level string
    """
    # Simple heuristic: lines of code + files + contributors
    complexity_score = 0
    
    if metrics.total_lines > 10000:
        complexity_score += 3
    elif metrics.total_lines > 5000:
        complexity_score += 2
    elif metrics.total_lines > 1000:
        complexity_score += 1
    
    if metrics.total_files > 50:
        complexity_score += 2
    elif metrics.total_files > 20:
        complexity_score += 1
    
    if metrics.total_contributors > 5:
        complexity_score += 2
    elif metrics.total_contributors > 2:
        complexity_score += 1
    
    if len(metrics.languages) > 3:
        complexity_score += 1
    
    if complexity_score >= 5:
        return "High"
    elif complexity_score >= 3:
        return "Medium-High"
    elif complexity_score >= 1:
        return "Medium"
    else:
        return "Low"


def _extract_key_features(metrics: ProjectMetrics) -> List[str]:
    """
    Extract key features/characteristics of the project
    
    Args:
        metrics: Extracted project metrics
        
    Returns:
        List of feature strings
    """
    features = []
    
    if metrics.has_tests:
        features.append("Comprehensive Testing")
    
    if metrics.has_documentation and metrics.doc_words > 500:
        features.append("Well-Documented")
    
    if metrics.is_collaborative:
        features.append("Team Collaboration")
    
    if metrics.total_commits > 100:
        features.append("Active Development")
    
    if len(metrics.languages) > 2:
        features.append("Multi-Language")
    
    if len(metrics.frameworks) > 2:
        features.append("Modern Stack")
    
    if metrics.total_lines > 5000:
        features.append("Large-Scale")
    
    return features[:5]  # Limit to top 5


def _build_resume_bullets(metrics: ProjectMetrics) -> List[str]:
    """
    Build 2-3 impactful resume bullet points from project metrics
    
    Args:
        metrics: Extracted project metrics
        
    Returns:
        List of 2-3 bullet strings
    """
    bullets = []
    
    # Bullet 1: Project scope and impact (more action-oriented)
    action_verbs = ["Developed", "Engineered", "Built", "Created", "Designed"]
    verb = action_verbs[metrics.total_lines % len(action_verbs)] if metrics.total_lines > 0 else "Developed"
    
    if metrics.is_collaborative:
        verb = "Contributed to" if metrics.total_contributors > 3 else "Co-developed"
    
    bullet1_parts = [verb]
    
    # Mention languages with more context
    if metrics.languages:
        if len(metrics.languages) == 1:
            bullet1_parts.append(f"a {metrics.languages[0]}-based")
        elif len(metrics.languages) == 2:
            bullet1_parts.append(f"a {metrics.languages[0]}/{metrics.languages[1]}")
        else:
            bullet1_parts.append(f"a multi-language")
        bullet1_parts.append("application")
    else:
        bullet1_parts.append("a software application")
    
    # Add frameworks if available
    if metrics.frameworks:
        if len(metrics.frameworks) == 1:
            bullet1_parts.append(f"leveraging {metrics.frameworks[0]}")
        elif len(metrics.frameworks) >= 2:
            bullet1_parts.append(f"using {metrics.frameworks[0]} and {metrics.frameworks[1]}")
    
    # Add scale with impact
    if metrics.total_lines > 10000:
        bullet1_parts.append(f"comprising {metrics.total_lines:,}+ lines of code")
    elif metrics.total_lines > 5000:
        bullet1_parts.append(f"with {metrics.total_lines:,}+ lines of code")
    elif metrics.total_files > 20:
        bullet1_parts.append(f"spanning {metrics.total_files}+ files")
    
    # Add quality indicators
    if metrics.has_tests:
        bullet1_parts.append("with comprehensive test coverage")
    elif metrics.has_documentation and metrics.doc_words > 500:
        bullet1_parts.append("with extensive documentation")
    
    bullets.append(" ".join(bullet1_parts) + ".")
    
    # Bullet 2: Collaboration and process (more specific)
    if metrics.is_collaborative and metrics.total_commits > 0:
        bullets.append(
            f"Collaborated with {metrics.total_contributors} team member{'s' if metrics.total_contributors != 1 else ''} "
            f"across {metrics.total_commits}+ commits, implementing agile practices "
            f"and maintaining code quality through code reviews and continuous integration."
        )
    elif metrics.total_commits > 100:
        bullets.append(
            f"Maintained robust version control practices with {metrics.total_commits}+ commits, "
            f"demonstrating commitment to iterative development and systematic code management."
        )
    elif metrics.total_commits > 0:
        bullets.append(
            f"Implemented disciplined version control with {metrics.total_commits} commits, "
            f"ensuring project maintainability and tracking development progress."
        )
    elif metrics.has_tests:
        bullets.append(
            "Established comprehensive testing practices, ensuring code reliability "
            "and maintainability through automated test suites."
        )
    else:
        # Generic but still professional
        if metrics.is_collaborative:
            bullets.append(
                "Participated in collaborative development workflows, contributing to "
                "team-based software engineering practices and knowledge sharing."
            )
        else:
            bullets.append(
                "Demonstrated strong project ownership and systematic approach to "
                "software development, following industry best practices."
            )
    
    # Bullet 3: Technical skills and achievements (more specific)
    if metrics.skills and len(metrics.skills) > 0:
        skill_list = metrics.skills[:4]  # Limit to 4 for readability
        if len(skill_list) <= 2:
            skill_str = " and ".join(skill_list)
        else:
            skill_str = ", ".join(skill_list[:-1]) + f", and {skill_list[-1]}"
        
        achievement_parts = []
        if metrics.total_lines > 5000:
            achievement_parts.append("large-scale")
        if len(metrics.languages) > 2:
            achievement_parts.append("multi-technology")
        if metrics.has_documentation:
            achievement_parts.append("well-documented")
        
        achievement = " " + " ".join(achievement_parts) if achievement_parts else ""
        
        bullets.append(
            f"Applied expertise in {skill_str} to deliver a{achievement} solution, "
            f"showcasing proficiency in modern software engineering practices."
        )
    else:
        # Fallback with available metrics
        tech_parts = []
        if metrics.languages:
            tech_parts.append(f"{len(metrics.languages)} programming language{'s' if len(metrics.languages) != 1 else ''}")
        if metrics.frameworks:
            tech_parts.append(f"{len(metrics.frameworks)} framework{'s' if len(metrics.frameworks) != 1 else ''}")
        
        if tech_parts:
            tech_str = " and ".join(tech_parts)
            bullets.append(
                f"Leveraged {tech_str} to build a robust application, "
                f"demonstrating versatility and technical depth."
            )
        else:
            bullets.append(
                "Demonstrated proficiency in software engineering principles, "
                "including clean code practices, documentation, and systematic problem-solving."
            )
    
    return bullets


def generate_items_from_project_id(
    project_id: int,
    db_path: Optional[str] = None,
    store: Optional["ProjectInsightsStore"] = None,
    regenerate: bool = True,
    resume_customization: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate portfolio and resume items from a stored project run by its database ID.
    
    This function fetches a project's stored insights from the SQLite database
    and regenerates portfolio/resume items using the current template logic.
    This allows updating presentation items for old projects when templates change.
    
    Args:
        project_id: The project_info.id primary key from the SQLite insights database.
        db_path: Optional database path. If None, uses default from environment.
            Ignored if `store` is provided.
        store: Optional ProjectInsightsStore instance. If None, creates a new one.
        regenerate: If True (default), always regenerate portfolio/resume items
            from the stored payload. If False, return existing items if present.
        resume_customization: Optional customization dict to override/edit resume item
            wording (non-persistent, runtime-only). See apply_resume_item_customization
            for schema. Only applied if regenerate=True.
    
    Returns:
        Dictionary containing:
            - "project_id": The provided project_id
            - "project_payload": The full decrypted project payload from storage
            - "portfolio_item": Generated portfolio item dict
            - "resume_item": Generated resume item dict
    
    Raises:
        ValueError: If project_id is not found in the database.
        RuntimeError: If database access fails or payload is invalid.
    """
    # Import here to avoid circular dependency
    from src.insights.storage import ProjectInsightsStore
    
    # Initialize store if not provided
    if store is None:
        store = ProjectInsightsStore(db_path=db_path)
    
    # Load project insight by ID
    project_payload = store.load_project_insight_by_id(project_id)
    if project_payload is None:
        raise ValueError(f"Project with ID {project_id} not found in database")
    
    # If regenerate is False and items already exist, return them
    if not regenerate:
        portfolio_item = project_payload.get("portfolio_item")
        resume_item = project_payload.get("resume_item")
        if portfolio_item and resume_item and "error" not in portfolio_item and "error" not in resume_item:
            return {
                "project_id": project_id,
                "project_payload": project_payload,
                "portfolio_item": portfolio_item,
                "resume_item": resume_item,
            }
    
    # Regenerate portfolio and resume items from the stored payload
    # Remove existing items if present to ensure fresh generation
    project_dict = dict(project_payload)
    project_dict.pop("portfolio_item", None)
    project_dict.pop("resume_item", None)
    
    try:
        portfolio_item = generate_portfolio_item(project_dict)
        resume_item = generate_resume_item(project_dict, customization=resume_customization)
    except Exception as e:
        raise RuntimeError(f"Failed to generate presentation items: {e}") from e
    
    return {
        "project_id": project_id,
        "project_payload": project_payload,
        "portfolio_item": portfolio_item,
        "resume_item": resume_item,
    }
