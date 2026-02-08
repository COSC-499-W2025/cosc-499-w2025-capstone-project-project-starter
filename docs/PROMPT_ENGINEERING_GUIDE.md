# How to "Teach" the LLM Model - Prompt Engineering Guide

This guide explains how to customize and "teach" the LLM to analyze your artifacts exactly the way you want.

## Table of Contents
- [Understanding System vs User Prompts](#understanding-system-vs-user-prompts)
- [Customizing System Prompts](#customizing-system-prompts)
- [Crafting Effective Prompts](#crafting-effective-prompts)
- [Few-Shot Learning](#few-shot-learning)
- [Temperature & Creativity](#temperature--creativity)
- [Common Patterns](#common-patterns)
- [Examples](#examples)

---

## Understanding System vs User Prompts

### System Prompt
The **system prompt** defines the AI's role and behavior. It's like giving the AI a job description.

```python
# System prompt example (sets the AI's role)
"You are an experienced software engineer reviewing code. 
Focus on code quality, best practices, and security."
```

### User Prompt
The **user prompt** is the specific instruction and content for each request.

```python
# User prompt example (specific task)
"Review the following Python code and suggest improvements:
def calculate(x, y): return x / y"
```

---

## Customizing System Prompts

### Method 1: Modify Built-in System Prompts

```python
from llm_analyzer import LLMAnalyzer, AnalysisType

analyzer = LLMAnalyzer()

# Customize code review to focus on security
analyzer.set_custom_system_prompt(
    AnalysisType.CODE_REVIEW,
    """You are a cybersecurity expert reviewing code.
    
    Focus on:
    - Security vulnerabilities (SQL injection, XSS, etc.)
    - Authentication and authorization issues
    - Data validation and sanitization
    - Secure coding practices
    
    Be specific about security risks and provide remediation advice."""
)

# Now all code reviews will use this security-focused approach
result = analyzer.analyze_code_file(code, "app.py", "Python")
```

### Method 2: Create Custom Analysis Types

```python
# For highly specialized needs, you can subclass
class SecurityAnalyzer(LLMAnalyzer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add custom system prompts
        self.system_prompts[AnalysisType.CODE_REVIEW] = """
        You are a senior security auditor specializing in web applications.
        Your expertise includes OWASP Top 10, secure coding, and threat modeling.
        
        For each code review:
        1. Identify security vulnerabilities
        2. Rate severity (Critical/High/Medium/Low)
        3. Provide specific remediation steps
        4. Suggest security best practices
        """

# Use your custom analyzer
security_analyzer = SecurityAnalyzer()
```

---

## Crafting Effective Prompts

### ✅ Good Prompt Practices

#### 1. Be Specific
```python
# ❌ Vague
"Analyze this code"

# ✅ Specific
"""Analyze this Python code for:
1. Performance bottlenecks
2. Memory efficiency
3. Code readability
4. Potential bugs"""
```

#### 2. Provide Context
```python
# ❌ No context
analyzer.analyze(code, AnalysisType.CODE_REVIEW)

# ✅ With context
analyzer.analyze(
    code,
    AnalysisType.CODE_REVIEW,
    context={
        "project_type": "web_api",
        "framework": "FastAPI",
        "python_version": "3.11",
        "team_size": 6,
        "production": True
    }
)
```

#### 3. Set Expectations
```python
custom_prompt = """
Review this code and provide:
- 3-5 specific improvement suggestions
- Performance considerations
- A rating out of 10
- Whether it's production-ready

Format as:
## Improvements
1. ...
2. ...

## Performance
...

## Rating: X/10

## Production Ready: Yes/No
"""
```

#### 4. Use Examples (Few-Shot Learning)
```python
custom_prompt = """
Extract technical skills from the following project descriptions.

Examples:
Input: "Built REST API with FastAPI and PostgreSQL"
Output: {"languages": ["Python"], "frameworks": ["FastAPI"], "databases": ["PostgreSQL"]}

Input: "Created React frontend with TypeScript and Material-UI"
Output: {"languages": ["TypeScript", "JavaScript"], "frameworks": ["React"], "ui_libraries": ["Material-UI"]}

Now extract skills from:
{content}

Format as JSON.
"""
```

---

## Few-Shot Learning

Few-shot learning means providing examples to guide the AI's responses.

### Example 1: Structured Skill Extraction

```python
def extract_skills_structured(self, content: str):
    """Extract skills with consistent JSON format"""
    
    prompt = """
You are a technical recruiter analyzing work artifacts to identify skills.

FORMAT YOUR RESPONSE AS JSON:
{
  "programming_languages": ["Python", "JavaScript"],
  "frameworks": ["FastAPI", "React"],
  "databases": ["PostgreSQL", "Redis"],
  "tools": ["Docker", "Git"],
  "concepts": ["REST APIs", "Authentication"]
}

EXAMPLES:

Input: "Developed microservices with Spring Boot and MongoDB"
Output: {
  "programming_languages": ["Java"],
  "frameworks": ["Spring Boot"],
  "databases": ["MongoDB"],
  "tools": [],
  "concepts": ["Microservices"]
}

Input: "Built CI/CD pipeline with Jenkins and deployed to AWS"
Output: {
  "programming_languages": [],
  "frameworks": [],
  "databases": [],
  "tools": ["Jenkins", "AWS"],
  "concepts": ["CI/CD", "Cloud Deployment"]
}

Now analyze:
{content}
"""
    
    result = self.analyze(
        content=content,
        analysis_type=AnalysisType.SKILL_EXTRACTION,
        custom_prompt=prompt.format(content=content)
    )
    
    # Parse JSON from response
    import json
    try:
        skills = json.loads(result["analysis"])
        return skills
    except:
        return result
```

### Example 2: Consistent Code Reviews

```python
def code_review_with_rating(self, code: str):
    """Get code reviews with consistent format"""
    
    prompt = """
Review this code using the following format:

## Quality Score: X/10

## Strengths
- Point 1
- Point 2

## Issues
- Issue 1 (Severity: High/Medium/Low)
- Issue 2 (Severity: High/Medium/Low)

## Improvements
1. Specific change
2. Specific change

## Verdict: Production Ready / Needs Work / Major Issues

EXAMPLE:

Code: def divide(a, b): return a / b

Output:
## Quality Score: 4/10

## Strengths
- Simple and readable function

## Issues
- Division by zero not handled (Severity: High)
- No type hints (Severity: Low)
- No docstring (Severity: Low)

## Improvements
1. Add check: if b == 0: raise ValueError("Cannot divide by zero")
2. Add type hints: def divide(a: float, b: float) -> float
3. Add docstring explaining parameters and return value

## Verdict: Needs Work

Now review:
{code}
"""
    
    return self.analyze(
        code,
        AnalysisType.CODE_REVIEW,
        custom_prompt=prompt.format(code=code)
    )
```

---

## Temperature & Creativity

The `temperature` parameter controls randomness/creativity:

### Temperature Scale
- **0.0 - 0.3**: Very focused, deterministic
  - Good for: Factual analysis, code review, bug finding
- **0.4 - 0.7**: Balanced (default: 0.7)
  - Good for: General analysis, summaries
- **0.8 - 1.2**: Creative, varied
  - Good for: Portfolio writing, marketing copy
- **1.3 - 2.0**: Very creative, experimental
  - Good for: Brainstorming, creative content

### Examples

```python
# Strict, factual code analysis
factual_analyzer = LLMAnalyzer(temperature=0.2)
result = factual_analyzer.analyze_code_file(code, "app.py", "Python")

# Balanced analysis
balanced_analyzer = LLMAnalyzer(temperature=0.7)
result = balanced_analyzer.analyze_git_commits(commits, "my-repo")

# Creative portfolio generation
creative_analyzer = LLMAnalyzer(temperature=1.0)
result = creative_analyzer.generate_portfolio_entry(project_data)
```

---

## Common Patterns

### Pattern 1: Domain Expert

Make the AI an expert in your specific domain:

```python
analyzer.set_custom_system_prompt(
    AnalysisType.CODE_REVIEW,
    """You are a machine learning engineer specializing in PyTorch and TensorFlow.
    
    When reviewing code:
    - Check for efficient tensor operations
    - Identify GPU memory issues
    - Suggest vectorization opportunities
    - Validate model architecture choices
    - Review training loop best practices"""
)
```

### Pattern 2: Strict Format Enforcer

Get responses in a specific format:

```python
custom_prompt = """
Analyze this code and respond ONLY in this format:
SCORE: <number 1-10>
GOOD: <one positive thing>
BAD: <one negative thing>
FIX: <one specific improvement>

Do not deviate from this format.
"""
```

### Pattern 3: Comparative Analysis

Compare against standards or examples:

```python
custom_prompt = """
Compare this code against industry best practices for {framework}:

Best Practices Checklist:
✓ Error handling
✓ Type hints
✓ Documentation
✓ Testing
✓ Performance
✓ Security

For each item, rate: ✅ Good / ⚠️ Needs Improvement / ❌ Missing

Then provide specific recommendations.
"""
```

### Pattern 4: Progressive Depth

Get different levels of detail:

```python
def analyze_with_depth(code, depth="summary"):
    """
    depth: 'summary' | 'detailed' | 'exhaustive'
    """
    
    prompts = {
        "summary": "Provide a 2-3 sentence summary of this code.",
        "detailed": "Provide detailed analysis with 5-7 key points.",
        "exhaustive": "Provide exhaustive analysis covering all aspects: architecture, patterns, quality, security, performance, maintainability."
    }
    
    return analyzer.analyze(
        code,
        AnalysisType.CODE_REVIEW,
        custom_prompt=prompts[depth]
    )
```

---

## Complete Examples

### Example 1: Security-Focused Analyzer

```python
from llm_analyzer import LLMAnalyzer, AnalysisType

class SecurityCodeAnalyzer:
    def __init__(self):
        self.analyzer = LLMAnalyzer(
            model="gpt-4o",  # Use best model for security
            temperature=0.2   # Low temperature for focused analysis
        )
        
        # Set security-focused system prompt
        self.analyzer.set_custom_system_prompt(
            AnalysisType.CODE_REVIEW,
            """You are a senior application security engineer with CISSP certification.
            
            Your expertise:
            - OWASP Top 10
            - Secure coding standards (CERT, CWE)
            - Threat modeling
            - Security testing
            
            For each code review, identify:
            1. Security vulnerabilities with CWE references
            2. Severity: Critical/High/Medium/Low/Info
            3. Attack scenarios
            4. Specific remediation code
            5. Security testing recommendations"""
        )
    
    def analyze_code(self, code, filename, language):
        """Analyze code for security issues"""
        
        custom_prompt = f"""
Perform security analysis on this {language} code from {filename}.

Provide response in this format:

## Security Score: X/10

## Vulnerabilities Found
### 1. [Vulnerability Name] - [Severity]
- **CWE:** CWE-XXX
- **Description:** ...
- **Attack Scenario:** ...
- **Remediation:** 
```{language}
// Fixed code here
```

## Security Recommendations
1. ...
2. ...

## Security Testing Suggestions
- Test case 1
- Test case 2
"""
        
        result = self.analyzer.analyze(
            content=code,
            analysis_type=AnalysisType.CODE_REVIEW,
            custom_prompt=custom_prompt,
            context={
                "filename": filename,
                "language": language,
                "security_scan": True
            }
        )
        
        return result

# Usage
security_analyzer = SecurityCodeAnalyzer()

code = """
def login(username, password):
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    return db.execute(query)
"""

result = security_analyzer.analyze_code(code, "auth.py", "Python")
print(result["analysis"])
```

### Example 2: Portfolio Generation Specialist

```python
class PortfolioGenerator:
    def __init__(self):
        self.analyzer = LLMAnalyzer(
            model="gpt-4o",
            temperature=0.8  # Higher for creative writing
        )
        
        self.analyzer.set_custom_system_prompt(
            AnalysisType.PORTFOLIO_GENERATION,
            """You are a professional technical writer and career coach specializing in developer portfolios.
            
            Your writing style:
            - Clear and compelling
            - Achievement-focused (use metrics)
            - Technical but accessible
            - Professional yet personable
            
            Always include:
            - Strong opening hook
            - Technical depth
            - Quantified impact
            - Skills demonstrated
            - Call to action (if relevant)"""
        )
    
    def generate(self, project_data):
        """Generate portfolio entry"""
        
        prompt = """
Create a compelling portfolio entry for this project.

Structure:
1. **Project Title & Tagline** (one compelling sentence)
2. **Overview** (2-3 sentences - what, why, impact)
3. **Technical Implementation** (bullet points - what you built)
4. **Key Achievements** (quantified results)
5. **Technologies & Skills** (categorized list)
6. **Challenges & Solutions** (1-2 notable examples)

Example style:
"Developed a high-performance REST API serving 10K+ requests/day, reducing response times by 40% through strategic caching and database optimization. The system processes user artifacts in real-time, implementing privacy-first design with comprehensive PII redaction."

Make it impressive but honest. Use active voice and metrics.
"""
        
        return self.analyzer.generate_portfolio_entry(project_data)

# Usage
generator = PortfolioGenerator()
result = generator.generate({
    "name": "Digital Artifact Miner",
    "technologies": ["Python", "FastAPI", "SQLAlchemy", "OpenAI"],
    "commit_count": 200,
    "duration": "3 months"
})
```

### Example 3: Learning-Focused Analyzer

```python
class CodeMentorAnalyzer:
    """Analyzer that teaches while reviewing"""
    
    def __init__(self):
        self.analyzer = LLMAnalyzer(
            model="gpt-4o-mini",
            temperature=0.6
        )
        
        self.analyzer.set_custom_system_prompt(
            AnalysisType.CODE_REVIEW,
            """You are a patient and encouraging coding mentor.
            
            Your approach:
            - Start with positive feedback
            - Explain WHY something should change (educational)
            - Provide before/after examples
            - Link to learning resources
            - Encourage good practices
            - End with next steps
            
            Tone: Supportive, educational, practical"""
        )
    
    def review_for_learning(self, code, student_level="intermediate"):
        """Review code with educational focus"""
        
        level_guidance = {
            "beginner": "Explain concepts simply with basic examples",
            "intermediate": "Include design patterns and best practices",
            "advanced": "Discuss architecture, performance, and scalability"
        }
        
        prompt = f"""
Review this code for a {student_level} developer.
{level_guidance[student_level]}

Format:
## What You Did Well ✨
- Point 1 (and why it's good)
- Point 2

## Learning Opportunities 📚
### 1. [Concept Name]
**Current code:**
```python
# their code
```

**Why change:** [Educational explanation]

**Improved code:**
```python
# better version
```

**Learn more:** [Resource link or concept name]

## Next Steps 🚀
1. Practice ...
2. Learn about ...
"""
        
        return self.analyzer.analyze(
            code,
            AnalysisType.CODE_REVIEW,
            custom_prompt=prompt,
            context={"student_level": student_level}
        )

# Usage
mentor = CodeMentorAnalyzer()
result = mentor.review_for_learning("""
def get_users():
    users = []
    for id in range(1, 100):
        user = db.get(id)
        users.append(user)
    return users
""", student_level="intermediate")
```

---

## Advanced: Chain of Thought

For complex analysis, use chain-of-thought prompting:

```python
def analyze_with_reasoning(code):
    """Get detailed reasoning process"""
    
    prompt = """
Analyze this code using step-by-step reasoning:

Step 1: UNDERSTAND
- What does this code do?
- What is its purpose?

Step 2: ANALYZE STRUCTURE
- How is it organized?
- What patterns are used?

Step 3: IDENTIFY ISSUES
- What problems exist?
- Why are they problems?

Step 4: CONSIDER ALTERNATIVES
- What are better approaches?
- What are the tradeoffs?

Step 5: RECOMMEND
- What specific changes?
- Priority order?

Walk through each step explicitly.
"""
    
    return analyzer.analyze(code, AnalysisType.CODE_REVIEW, custom_prompt=prompt)
```

---

## Tips for Better Results

1. **Be Specific**: Vague prompts get vague responses
2. **Provide Examples**: Show the AI what you want
3. **Set Format**: Specify structure for consistent output
4. **Use Context**: Give relevant background information
5. **Iterate**: Refine prompts based on results
6. **Test Temperature**: Adjust for your use case
7. **Combine Techniques**: Use multiple patterns together
8. **Version Control**: Save successful prompts
9. **Monitor Cost**: Track token usage
10. **Validate Output**: Always verify AI responses

---

## Prompt Library

Save your best prompts for reuse:

```python
PROMPT_LIBRARY = {
    "security_audit": """...""",
    "performance_review": """...""",
    "beginner_friendly": """...""",
    "portfolio_polish": """...""",
    "commit_summary": """..."""
}

# Use from library
result = analyzer.analyze(
    code,
    AnalysisType.CODE_REVIEW,
    custom_prompt=PROMPT_LIBRARY["security_audit"]
)
```

---

## Summary

"Teaching" the LLM means:
1. **System prompts**: Define its role and expertise
2. **User prompts**: Provide clear, specific instructions
3. **Examples**: Show what you want (few-shot learning)
4. **Temperature**: Control creativity level
5. **Context**: Give relevant background
6. **Format**: Specify output structure
7. **Iteration**: Refine based on results

Start simple, test, and iterate to find what works best for your use case!

