# LLM Analyzer - Quick Start Guide

Get up and running with LLM analysis in 5 minutes!

## 🚀 Quick Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Get OpenAI API Key
1. Go to https://platform.openai.com/api-keys
2. Create account if needed
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)

### 3. Set Up Environment
```bash
# Create .env file
echo "OPENAI_API_KEY=sk-your-key-here" > ../.env
```

### 4. Test It!
```bash
python -c "from llm_analyzer import quick_analyze; print(quick_analyze('def add(a,b): return a+b'))"
```

## 📖 Basic Usage

```python
from llm_analyzer import LLMAnalyzer, AnalysisType

# Create analyzer
analyzer = LLMAnalyzer(model="gpt-4o-mini")

# Analyze code
result = analyzer.analyze(
    content="your code here",
    analysis_type=AnalysisType.CODE_REVIEW
)

print(result["analysis"])
```

## 🎯 Common Tasks

### Analyze Code
```python
code = "def factorial(n): return 1 if n <= 1 else n * factorial(n-1)"
result = analyzer.analyze_code_file(code, "math.py", "Python")
```

### Summarize Commits
```python
commits = [
    {"hash": "abc123", "message": "Add feature X", "author": "You", "date": "2024-10-20"}
]
result = analyzer.analyze_git_commits(commits, "my-repo")
```

### Extract Skills
```python
artifacts = ["Built API with FastAPI", "Created React frontend"]
result = analyzer.extract_skills(artifacts)
```

### Generate Portfolio
```python
project = {
    "name": "Cool Project",
    "technologies": ["Python", "FastAPI"],
    "commit_count": 100
}
result = analyzer.generate_portfolio_entry(project)
```

## 🎨 Analysis Types

- `CODE_REVIEW` - Review code quality and patterns
- `COMMIT_SUMMARY` - Summarize git history
- `PROJECT_OVERVIEW` - Create project summaries
- `SKILL_EXTRACTION` - Extract technical skills
- `DOCUMENTATION_SUMMARY` - Summarize docs
- `PORTFOLIO_GENERATION` - Generate portfolio entries

## 💰 Cost Info

**gpt-4o-mini** (recommended):
- ~$0.15 per 1M tokens
- Most requests < $0.01
- Fast and good quality

**gpt-4o** (production):
- ~$2.50 per 1M tokens
- Highest quality
- Slower but better

## 📚 Examples

Run the full example suite:
```bash
python example_usage.py
```

## 🐛 Troubleshooting

**API Key Error?**
```bash
# Check if key is loaded
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('OPENAI_API_KEY'))"
```

**Still stuck?** Check `docs/LLM_SETUP_GUIDE.md` for detailed help!

## 📝 Next Steps

1. Read full guide: `docs/LLM_SETUP_GUIDE.md`
2. Check examples: `example_usage.py`
3. Run tests: `pytest tests/test_llm_analyzer.py`
4. Customize prompts for your needs!

---

**Need help?** Check the full setup guide in `docs/LLM_SETUP_GUIDE.md`

