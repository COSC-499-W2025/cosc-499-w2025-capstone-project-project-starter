"""
Skill Mapper Module

Converts technical analysis findings into resume-friendly skill descriptions.
Maps deep code analysis patterns to professional skill statements.
"""

from typing import Dict, List, Set


class SkillMapper:
    """Maps technical code analysis to resume-friendly skill descriptions."""
    
    # Mapping from technical patterns to resume skills
    SKILL_MAPPINGS = {
        # OOP Principles
        'abstraction': 'Object-Oriented Design',
        'encapsulation': 'Data Encapsulation & Information Hiding',
        'polymorphism': 'Polymorphic Programming',
        'inheritance': 'Class Inheritance & Code Reusability',
        
        # Data Structures
        'hash_map': 'Hash Tables & Key-Value Data Structures',
        'list': 'List & Array Manipulation',
        'set': 'Set Operations & Unique Collections',
        'tree': 'Tree Data Structures & Hierarchical Data',
        'array': 'Array Processing & Indexing',
        
        # Design Patterns
        'singleton': 'Singleton Design Pattern',
        'caching': 'Caching & Memoization Strategies',
        'lazy_loading': 'Lazy Loading & Resource Optimization',
        
        # Complexity & Algorithms
        'nested_loops': 'Complex Algorithm Implementation',
        'recursive_functions': 'Recursive Problem Solving',
        'sorting': 'Sorting Algorithms & Data Organization',
        'binary_search': 'Binary Search & Efficient Search Algorithms',
        
        # Code Quality
        'error_handling': 'Exception Handling & Error Management',
        'documentation': 'Code Documentation & Technical Writing',
        'type_hints': 'Type Safety & Static Typing',
        'testing': 'Unit Testing & Test-Driven Development',
        'modularity': 'Modular Architecture & Code Organization',
        
        # Optimizations
        'string_optimization': 'Performance Optimization',
        'early_returns': 'Code Efficiency & Control Flow',
        'async': 'Asynchronous Programming',
        
        # Frameworks & Technologies (these are already resume-friendly)
        'React': 'React.js',
        'Vue': 'Vue.js',
        'Angular': 'Angular',
        'Django': 'Django Web Framework',
        'Flask': 'Flask Web Framework',
        'Express': 'Express.js',
        'Spring': 'Spring Framework',
        'Node.js': 'Node.js',
        'Docker': 'Docker & Containerization',
        'PostgreSQL': 'PostgreSQL Database',
        'MongoDB': 'MongoDB Database',
        'FastAPI': 'FastAPI',
        
        # Languages (already resume-friendly, but can add descriptions)
        'Python': 'Python Programming',
        'Java': 'Java Programming',
        'JavaScript': 'JavaScript Programming',
        'TypeScript': 'TypeScript Programming',
        'C++': 'C++ Programming',
        'C': 'C Programming',
        'C#': 'C# Programming',
        'Go': 'Go Programming',
        'Rust': 'Rust Programming',
        'Ruby': 'Ruby Programming',
        'PHP': 'PHP Programming',
        'Swift': 'Swift Programming',
        'Kotlin': 'Kotlin Programming',
    }
    
    # Skill categories for better organization
    SKILL_CATEGORIES = {
        'Programming Languages': ['Python', 'Java', 'JavaScript', 'TypeScript', 'C++', 'C', 'C#', 'Go', 'Rust', 'Ruby', 'PHP', 'Swift', 'Kotlin'],
        'Web Frameworks': ['React', 'Vue', 'Angular', 'Django', 'Flask', 'Express', 'FastAPI'],
        'Backend Frameworks': ['Spring', 'Django', 'Flask', 'Express', 'FastAPI'],
        'Databases': ['PostgreSQL', 'MongoDB'],
        'DevOps': ['Docker', 'CI/CD', 'Git'],
        'Software Engineering': ['abstraction', 'encapsulation', 'polymorphism', 'inheritance', 'modularity', 'error_handling', 'documentation', 'testing'],
        'Data Structures & Algorithms': ['hash_map', 'list', 'set', 'tree', 'array', 'nested_loops', 'recursive_functions', 'sorting', 'binary_search'],
        'Performance & Optimization': ['caching', 'lazy_loading', 'string_optimization', 'early_returns', 'async'],
    }
    
    @staticmethod
    def map_technical_skill(technical_term: str) -> str:
        """
        Map a technical term to a resume-friendly skill description.
        
        Args:
            technical_term: Technical term from code analysis
            
        Returns:
            Resume-friendly skill description
        """
        # Normalize the term
        normalized = technical_term.lower().replace(' ', '_').replace('-', '_')
        
        # Direct mapping
        if normalized in SkillMapper.SKILL_MAPPINGS:
            return SkillMapper.SKILL_MAPPINGS[normalized]
        
        # Check if it's a language (capitalize properly)
        if technical_term in SkillMapper.SKILL_MAPPINGS:
            return SkillMapper.SKILL_MAPPINGS[technical_term]
        
        # If no mapping found, return a formatted version
        return technical_term.replace('_', ' ').title()
    
    @staticmethod
    def extract_skills_from_deep_analysis(deep_analysis: Dict) -> Set[str]:
        """
        Extract skills from deep code analysis results.
        
        Args:
            deep_analysis: Deep code analysis dictionary
            
        Returns:
            Set of resume-friendly skill descriptions
        """
        skills = set()
        
        if not deep_analysis:
            return skills
        
        # Extract OOP principles
        oop_summary = deep_analysis.get('oop_principles_summary', {})
        for principle in ['abstraction', 'encapsulation', 'polymorphism', 'inheritance']:
            principle_data = oop_summary.get(principle, {})
            if principle_data.get('count', 0) > 0:
                skills.add(SkillMapper.map_technical_skill(principle))
        
        # Extract data structures
        ds_summary = deep_analysis.get('data_structure_summary', {})
        for struct_name in ds_summary.keys():
            if ds_summary[struct_name] > 0:
                skills.add(SkillMapper.map_technical_skill(struct_name))
        
        # Extract complexity indicators
        complexity = deep_analysis.get('complexity_summary', {})
        if complexity.get('nested_loops', 0) > 0:
            skills.add(SkillMapper.map_technical_skill('nested_loops'))
        if complexity.get('recursive_functions', 0) > 0:
            skills.add(SkillMapper.map_technical_skill('recursive_functions'))
        if complexity.get('complexity_awareness', False):
            skills.add('Algorithm Complexity Analysis')
        
        # Extract optimizations
        optimizations = deep_analysis.get('optimization_summary', [])
        for opt in optimizations:
            opt_type = opt.get('type', '').lower().replace(' ', '_')
            if opt_type:
                skills.add(SkillMapper.map_technical_skill(opt_type))
        
        # Extract code quality indicators
        quality = deep_analysis.get('code_quality_summary', {})
        if quality.get('error_handling', 0) > 0:
            skills.add(SkillMapper.map_technical_skill('error_handling'))
        if quality.get('documentation', 0) > 0:
            skills.add(SkillMapper.map_technical_skill('documentation'))
        if quality.get('type_hints', 0) > 0:
            skills.add(SkillMapper.map_technical_skill('type_hints'))
        if quality.get('testing', 0) > 0:
            skills.add(SkillMapper.map_technical_skill('testing'))
        if quality.get('modularity', 0) > 0:
            skills.add(SkillMapper.map_technical_skill('modularity'))
        
        return skills
    
    @staticmethod
    def extract_skills_from_project_summary(project_summary: Dict) -> Set[str]:
        """
        Extract skills from project summary (languages, frameworks, etc.).
        
        Args:
            project_summary: Project summary dictionary
            
        Returns:
            Set of resume-friendly skill descriptions
        """
        skills = set()
        
        # Extract languages
        languages = project_summary.get('languages', {})
        for lang in languages.get('languages', []):
            mapped = SkillMapper.map_technical_skill(lang)
            skills.add(mapped)
        
        # Extract frameworks (if available in project summary)
        # This would come from project_analyzer or similar
        frameworks = project_summary.get('frameworks', [])
        for framework in frameworks:
            mapped = SkillMapper.map_technical_skill(framework)
            skills.add(mapped)
        
        return skills
    
    @staticmethod
    def categorize_skills(skills: Set[str]) -> Dict[str, List[str]]:
        """
        Categorize skills into groups for better organization.
        
        Args:
            skills: Set of skill descriptions
            
        Returns:
            Dictionary mapping categories to lists of skills
        """
        categorized = {}
        
        for category, category_terms in SkillMapper.SKILL_CATEGORIES.items():
            category_skills = []
            for skill in skills:
                # Check if skill matches any term in this category
                skill_lower = skill.lower()
                for term in category_terms:
                    term_lower = term.lower()
                    if term_lower in skill_lower or skill_lower in term_lower:
                        category_skills.append(skill)
                        break
            
            if category_skills:
                categorized[category] = sorted(category_skills)
        
        # Add uncategorized skills
        all_categorized = set()
        for cat_skills in categorized.values():
            all_categorized.update(cat_skills)
        
        uncategorized = sorted(list(skills - all_categorized))
        if uncategorized:
            categorized['Other Skills'] = uncategorized
        
        return categorized

