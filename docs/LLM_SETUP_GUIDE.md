# LLM Analysis Setup Guide

This guide will help you set up and use the OpenAI LLM integration for analyzing digital work artifacts.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [OpenAI API Setup](#openai-api-setup)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Customization](#customization)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

- Python 3.11 or higher
- OpenAI API account (sign up at https://platform.openai.com/)
- Basic understanding of Python and REST APIs

---

## Installation

### Step 1: Clone the Repository (if not already done)
```bash
cd /Users/mishagavura/Documents/UBC/cosc499/capstone-project-team-14
```

### Step 2: Create Virtual Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate it (macOS/Linux)
source venv/bin/activate

# Activate it (Windows)
# venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

---

## OpenAI API Setup

### Step 1: Create OpenAI Account
1. Go to https://platform.openai.com/signup
2. Sign up for an account
3. Verify your email

### Step 2: Get API Key
1. Log into https://platform.openai.com/
2. Navigate to **API Keys** section (left sidebar)
3. Click **"Create new secret key"**
4. Give it a name (e.g., "Capstone Project")
5. **Copy the key immediately** (you won't see it again!)

### Step 3: Add Billing (Required)
1. Go to **Settings** → **Billing**
2. Add a payment method
3. Set up usage limits (recommended: $10-20/month for development)

**Note:** OpenAI charges per token. For reference:
- gpt-4o-mini: ~$0.15 per 1M input tokens, ~$0.60 per 1M output tokens
- gpt-4o: ~$2.50 per 1M input tokens, ~$10 per 1M output tokens
- Most analysis requests will cost < $0.01

---

## Configuration

### Step 1: Create Environment File
Create a `.env` file in the project root:

```bash
# In project root directory
touch .env
```

### Step 2: Add Your API Key
Edit `.env` and add:

```env
# Required: Your OpenAI API Key
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Optional: Model Settings (defaults shown)
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=1500

# Optional: Application Settings
# DATABASE_URL is optional (default is sqlite:///data/app.db -> data/app.db)
LOG_LEVEL=INFO
```

**Important:** 
- Replace `sk-proj-xxxxx...` with your actual API key
- Never commit `.env` to git (it's in `.gitignore`)
- Use `gpt-4o-mini` for development (cheaper and fast)
- Use `gpt-4o` for production (better quality)

### Step 3: Verify Installation
```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('API Key:', 'Found' if os.getenv('OPENAI_API_KEY') else 'Missing')"
```

Should print: `API Key: Found`

---

## Usage Examples

### Example 1: Basic Code Analysis

```python
from src.llm_analyzer import LLMAnalyzer, AnalysisType

# Initialize analyzer
analyzer = LLMAnalyzer(model="gpt-4o-mini")

# Analyze code
code = """
def calculate_metrics(data):
    total = sum(data.values())
    average = total / len(data)
    return {'total': total, 'average': average}
"""

result = analyzer.analyze_code_file(
    code=code,
    filename="metrics.py",
    language="Python"
)

if result["success"]:
    print(result["analysis"])
    print(f"Cost estimate: ~${result['tokens_used'] * 0.0000015:.4f}")
```

### Example 2: Commit History Analysis

```python
commits = [
    {"hash": "abc123", "message": "Add user auth", "author": "You", "date": "2024-10-20"},
    {"hash": "def456", "message": "Fix bug in login", "author": "You", "date": "2024-10-21"}
]

result = analyzer.analyze_git_commits(
    commits=commits,
    repo_name="my-project"
)

print(result["analysis"])
```

### Example 3: Skill Extraction

```python
artifacts = [
    "Built REST API with FastAPI and async endpoints",
    "Implemented React frontend with TypeScript",
    "Set up CI/CD with GitHub Actions"
]

result = analyzer.extract_skills(artifacts)
print(result["analysis"])
```

### Example 4: Portfolio Generation

```python
project_data = {
    "name": "My Awesome Project",
    "description": "A full-stack application",
    "technologies": ["Python", "FastAPI", "React", "PostgreSQL"],
    "commit_count": 150,
    "file_count": 45,
    "duration": "3 months"
}

result = analyzer.generate_portfolio_entry(project_data)
print(result["analysis"])
```

### Example 5: Run All Examples

```bash
cd src
python example_usage.py
```

---

## Customization

### Custom System Prompts

You can customize how the AI behaves:

```python
analyzer = LLMAnalyzer()

# Make it focus on security
analyzer.set_custom_system_prompt(
    AnalysisType.CODE_REVIEW,
    "You are a security-focused code reviewer. "
    "Identify potential vulnerabilities and security best practices."
)

# Now all code reviews will use this prompt
result = analyzer.analyze_code_file(code, "app.py", "Python")
```

### Custom Analysis Prompts

```python
result = analyzer.analyze(
    content="Your content here",
    analysis_type=AnalysisType.PROJECT_OVERVIEW,
    custom_prompt="Focus on scalability and performance aspects"
)
```

### Adjusting Parameters

```python
# More creative responses
analyzer = LLMAnalyzer(temperature=1.2)

# More focused/deterministic responses
analyzer = LLMAnalyzer(temperature=0.3)

# Longer responses
analyzer = LLMAnalyzer(max_tokens=3000)

# Better quality (more expensive)
analyzer = LLMAnalyzer(model="gpt-4o")
```

---

## Advanced Usage

### Batch Processing

```python
items = [
    {"id": "file1", "content": code1, "context": {"filename": "app.py"}},
    {"id": "file2", "content": code2, "context": {"filename": "utils.py"}}
]

results = analyzer.batch_analyze(items, AnalysisType.CODE_REVIEW)

for result in results:
    print(f"{result['item_id']}: {result['analysis']}")
```

### With Error Handling

```python
try:
    result = analyzer.analyze(content, AnalysisType.CODE_REVIEW)
    
    if result["success"]:
        print(f"Analysis: {result['analysis']}")
        print(f"Tokens used: {result['tokens_used']}")
    else:
        print(f"Error: {result['error']}")
        
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Tracking Costs

```python
# Approximate cost calculation
def estimate_cost(tokens, model="gpt-4o-mini"):
    costs = {
        "gpt-4o-mini": 0.0000015,  # $0.15/1M input + $0.60/1M output ≈ $0.0015/1K
        "gpt-4o": 0.00625           # $2.50/1M input + $10/1M output ≈ $6.25/1K
    }
    return tokens * costs.get(model, 0.001)

result = analyzer.analyze(content, AnalysisType.CODE_REVIEW)
cost = estimate_cost(result["tokens_used"], analyzer.model)
print(f"Cost: ${cost:.4f}")
```

---

## Model Selection Guide

### gpt-4o-mini (Recommended for Development)
- **Speed:** Very fast
- **Cost:** ~$0.15/1M input tokens
- **Quality:** Good for most tasks
- **Best for:** Code review, commit summaries, skill extraction

### gpt-4o (Recommended for Production)
- **Speed:** Slower
- **Cost:** ~$2.50/1M input tokens  
- **Quality:** Excellent, most capable
- **Best for:** Portfolio generation, complex analysis

### gpt-3.5-turbo (Budget Option)
- **Speed:** Very fast
- **Cost:** ~$0.50/1M input tokens
- **Quality:** Decent for simple tasks
- **Best for:** Quick summaries, simple extraction

---

## Testing

### Run Unit Tests
```bash
# Install test dependencies (already in requirements.txt)
pip install pytest pytest-cov

# Run tests
pytest tests/test_llm_analyzer.py -v

# Run with coverage
pytest tests/test_llm_analyzer.py --cov=src --cov-report=html
```

### Integration Test (Requires API Key)
```bash
# Set API key first
export OPENAI_API_KEY=your_key_here

# Run integration tests
pytest tests/test_llm_analyzer.py::TestIntegration -v
```

---

## Troubleshooting

### Issue: "OpenAI API key not found"
**Solution:**
1. Check `.env` file exists in project root
2. Verify `OPENAI_API_KEY` is set correctly
3. Make sure you've loaded the environment: `python-dotenv` should auto-load

```python
# Debug: Check if key is loaded
import os
from dotenv import load_dotenv
load_dotenv()
print(os.getenv("OPENAI_API_KEY"))
```

### Issue: "AuthenticationError: Incorrect API key"
**Solution:**
1. Verify your API key is correct (starts with `sk-`)
2. Check if key has been revoked in OpenAI dashboard
3. Generate a new key if needed

### Issue: "RateLimitError"
**Solution:**
1. You've exceeded your rate limit
2. Wait a few minutes or upgrade your plan
3. Implement exponential backoff:

```python
import time
from openai import RateLimitError

def analyze_with_retry(analyzer, content, max_retries=3):
    for i in range(max_retries):
        try:
            return analyzer.analyze(content, AnalysisType.CODE_REVIEW)
        except RateLimitError:
            if i < max_retries - 1:
                wait_time = (2 ** i) * 2  # Exponential backoff
                print(f"Rate limited. Waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise
```

### Issue: "Timeout errors"
**Solution:**
1. Reduce content size
2. Reduce `max_tokens`
3. Use faster model (gpt-4o-mini)

### Issue: "High costs"
**Solution:**
1. Use `gpt-4o-mini` instead of `gpt-4o`
2. Reduce `max_tokens` parameter
3. Cache results to avoid re-analyzing
4. Set usage limits in OpenAI dashboard

---

## Best Practices

1. **Start with gpt-4o-mini** - It's fast, cheap, and good enough for most tasks
2. **Cache results** - Don't re-analyze the same content
3. **Use batch processing** - More efficient for multiple items
4. **Monitor costs** - Set up billing alerts in OpenAI dashboard
5. **Handle errors gracefully** - Network issues, rate limits, etc.
6. **Test prompts** - Experiment with different prompts for better results
7. **Keep content focused** - Don't send massive files (truncate if needed)
8. **Version control prompts** - Store good prompts for reuse

---

## Cost Management

### Set Up Billing Alerts
1. Go to OpenAI Dashboard → Billing
2. Set up usage alerts (e.g., notify at $5, $10)
3. Set hard limits if needed

### Optimize Token Usage
```python
# Truncate large content
def truncate_code(code, max_lines=100):
    lines = code.split('\n')
    if len(lines) > max_lines:
        return '\n'.join(lines[:max_lines]) + f"\n... ({len(lines) - max_lines} more lines)"
    return code

# Use lower max_tokens for summaries
analyzer = LLMAnalyzer(max_tokens=500)  # Shorter responses
```

---

## Next Steps

1. **Integrate with your pipeline:**
   - Call LLM analysis after scanning artifacts
   - Store results in database
   - Use in REST API endpoints

2. **Build features:**
   - Auto-generate portfolio entries
   - Create commit summaries for projects
   - Extract skills for resume building

3. **Improve prompts:**
   - Test different system prompts
   - Add examples to prompts (few-shot learning)
   - Tune temperature and max_tokens

4. **Add caching:**
   - Cache analysis results by content hash
   - Avoid re-analyzing unchanged files

---

## Support & Resources

- **OpenAI Documentation:** https://platform.openai.com/docs
- **OpenAI Cookbook:** https://github.com/openai/openai-cookbook
- **Pricing:** https://openai.com/pricing
- **Rate Limits:** https://platform.openai.com/docs/guides/rate-limits
- **Python SDK:** https://github.com/openai/openai-python

---

## Example .env File

Create a `.env` file in your project root with:

```env
# OpenAI Configuration
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx

# Model Settings (optional)
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=1500

# Database (optional; default is sqlite:///data/app.db -> data/app.db)
LOG_LEVEL=INFO
```

**Remember:** Never commit `.env` to version control!

---

Good luck with your LLM integration! 🚀
