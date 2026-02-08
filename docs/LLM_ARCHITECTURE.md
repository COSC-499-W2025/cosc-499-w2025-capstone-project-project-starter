# LLM Integration Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Digital Artifact Miner                       │
│                     (Your Capstone Project)                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Scanning Layer                           │
├─────────────────────────────────────────────────────────────────┤
│  R1: Directory Selection  (Tahsin)                              │
│  R2: Type Detection       (Misha)                               │
│  R3: Git Adapter          (Abijeet)                             │
│  R4: Office/PDF Adapter   (Abhinav)                             │
│  R5: Media/Design Adapter (Kaiden)                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  ⭐ LLM Analysis Layer ⭐                        │
├─────────────────────────────────────────────────────────────────┤
│                      llm_analyzer.py                            │
│                                                                 │
│  📊 Analysis Types:                                             │
│   • CODE_REVIEW        → Review code quality                    │
│   • COMMIT_SUMMARY     → Summarize git history                  │
│   • PROJECT_OVERVIEW   → Create project summaries               │
│   • SKILL_EXTRACTION   → Extract technical skills               │
│   • DOCUMENTATION      → Summarize docs                         │
│   • PORTFOLIO_GEN      → Generate portfolio entries             │
│                                                                 │
│  🔌 Integration:                                                │
│   • OpenAI API (gpt-4o-mini/gpt-4o)                            │
│   • Customizable prompts                                        │
│   • Batch processing                                            │
│   • Error handling & caching                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Storage Layer (R6)                         │
├─────────────────────────────────────────────────────────────────┤
│  • Original artifact data                                       │
│  • LLM-generated insights                                       │
│  • Analysis metadata                                            │
│  • Token usage tracking                                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Analytics Layer (R7)                          │
├─────────────────────────────────────────────────────────────────┤
│  • Compute metrics from artifacts                               │
│  • Enhance with LLM insights                                    │
│  • Generate timelines & visualizations                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   REST API Layer (R8)                           │
├─────────────────────────────────────────────────────────────────┤
│  FastAPI Endpoints:                                             │
│   • GET  /artifacts           → List artifacts                  │
│   • GET  /artifacts/{id}      → Get artifact details            │
│   • POST /analyze             → Trigger LLM analysis            │
│   • GET  /insights            → Get LLM insights                │
│   • GET  /portfolio           → Generate portfolio              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Export Layer (R10)                           │
├─────────────────────────────────────────────────────────────────┤
│  • Export to JSON/CSV/PDF                                       │
│  • Include LLM-generated summaries                              │
│  • Professional portfolio format                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Example

### Scenario: User scans a Git repository

```
1. User initiates scan
   └─> Scanner finds Git repo (R2: Type Detection)
        └─> Git Adapter extracts commits (R3)
             └─> Commits data: 
                 - Hash, message, author, date
                 - Files changed, additions, deletions

2. LLM Analysis triggered
   └─> llm_analyzer.analyze_git_commits()
        └─> Sends to OpenAI API:
             SYSTEM: "You are a git history analyst..."
             USER: "Summarize these 50 commits..."
        └─> Receives AI-generated insights:
             "This repository shows consistent development
              with focus on API implementation and testing.
              Key contributions include..."

3. Storage Layer (R6)
   └─> Saves both:
        • Raw commit data
        • LLM insights
        • Tokens used: 450
        • Timestamp

4. API Layer (R8)
   └─> Exposes via endpoints:
        GET /insights/repo/{id}
        → Returns combined data + AI analysis

5. Export (R10)
   └─> Generates portfolio.pdf with:
        • Project timeline
        • Commit summary (AI-enhanced)
        • Skills demonstrated
        • Professional formatting
```

---

## LLM Analyzer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        LLMAnalyzer Class                        │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐      ┌──────────────┐
│   OpenAI     │    │   Analysis   │      │    Prompt    │
│   Client     │    │    Types     │      │   Builder    │
├──────────────┤    ├──────────────┤      ├──────────────┤
│ • API Key    │    │ • CODE_REVIEW│      │ • System     │
│ • Model      │    │ • COMMIT_SUM │      │ • User       │
│ • Settings   │    │ • SKILLS     │      │ • Context    │
└──────────────┘    │ • PORTFOLIO  │      └──────────────┘
                    └──────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐      ┌──────────────┐
│    Batch     │    │    Cache     │      │    Error     │
│  Processing  │    │   Manager    │      │   Handler    │
├──────────────┤    ├──────────────┤      ├──────────────┤
│ • Multiple   │    │ • Content    │      │ • Retries    │
│   items      │    │   hashing    │      │ • Fallbacks  │
│ • Parallel   │    │ • Avoid      │      │ • Validation │
└──────────────┘    │   re-analysis│      └──────────────┘
                    └──────────────┘
```

---

## Analysis Flow

### Step-by-Step Process

```
User Code Input
     │
     ▼
┌─────────────────────┐
│  1. Preprocessing   │
│  • Detect language  │
│  • Extract metadata │
│  • Format content   │
└─────────────────────┘
     │
     ▼
┌─────────────────────┐
│  2. Prompt Build    │
│  • Select system    │
│    prompt           │
│  • Build user       │
│    prompt           │
│  • Add context      │
└─────────────────────┘
     │
     ▼
┌─────────────────────┐
│  3. LLM Call        │
│  • Send to OpenAI   │
│  • Wait for response│
│  • Track tokens     │
└─────────────────────┘
     │
     ▼
┌─────────────────────┐
│  4. Post-process    │
│  • Extract analysis │
│  • Format result    │
│  • Cache result     │
└─────────────────────┘
     │
     ▼
Return Result
```

---

## Integration Points

### How Each Team Member Can Use LLM

#### Misha (R2: Type Detection)
```python
# After detecting file type
from llm_analyzer import LLMAnalyzer

def categorize_file(file_path, content):
    # Your type detection
    file_type = detect_type(file_path)
    
    # Optional: LLM can suggest better categorization
    if file_type == "unknown":
        analyzer = LLMAnalyzer()
        result = analyzer.analyze(
            content[:500],  # First 500 chars
            AnalysisType.PROJECT_OVERVIEW,
            custom_prompt="What type of file is this?"
        )
        # Use result to improve categorization
```

#### Abijeet (R3: Git Adapter)
```python
# After extracting commits
from llm_analyzer import LLMAnalyzer

def process_repository(repo_path):
    # Your git extraction
    commits = extract_commits(repo_path)
    
    # Add LLM insights
    analyzer = LLMAnalyzer()
    insights = analyzer.analyze_git_commits(commits, repo_name)
    
    return {
        "commits": commits,
        "ai_summary": insights["analysis"],
        "tokens_used": insights["tokens_used"]
    }
```

#### Abhinav (R4, R8: Documents & API)
```python
# R4: Document parsing + LLM summary
def process_document(doc_path):
    # Your doc parsing
    text = extract_text_from_pdf(doc_path)
    
    # Add LLM summary
    analyzer = LLMAnalyzer()
    summary = analyzer.analyze(
        text,
        AnalysisType.DOCUMENTATION_SUMMARY
    )
    return summary

# R8: Add API endpoint
@app.post("/analyze/code")
async def analyze_code(code: str):
    analyzer = LLMAnalyzer()
    result = analyzer.analyze_code_file(code, "input.py", "Python")
    return result
```

#### Abdur (R6: Storage)
```python
# Store LLM results with artifacts
def store_artifact(artifact_data, llm_insights):
    db.insert({
        "artifact_id": artifact_data["id"],
        "type": artifact_data["type"],
        "content": artifact_data["content"],
        "llm_analysis": llm_insights["analysis"],
        "tokens_used": llm_insights["tokens_used"],
        "analyzed_at": datetime.now()
    })
```

#### Tahsin (R7: Analytics)
```python
# Enhance analytics with LLM
def compute_insights(artifacts):
    # Your metrics
    metrics = calculate_metrics(artifacts)
    
    # LLM generates narrative
    analyzer = LLMAnalyzer()
    narrative = analyzer.analyze(
        str(metrics),
        AnalysisType.PROJECT_OVERVIEW,
        custom_prompt="Create an engaging summary of these metrics"
    )
    
    return {
        "metrics": metrics,
        "narrative": narrative["analysis"]
    }
```

#### Kaiden (R10: Export)
```python
# Export with LLM-generated content
def export_portfolio(artifacts):
    analyzer = LLMAnalyzer()
    
    # Generate portfolio entry for each project
    portfolio_entries = []
    for artifact in artifacts:
        entry = analyzer.generate_portfolio_entry({
            "name": artifact["name"],
            "technologies": artifact["techs"],
            "commits": artifact["commit_count"]
        })
        portfolio_entries.append(entry["analysis"])
    
    # Export to PDF with professional content
    create_pdf(portfolio_entries)
```

---

## API Endpoints (Suggestion for R8)

```python
# api/endpoints.py

from fastapi import FastAPI, HTTPException
from llm_analyzer import LLMAnalyzer, AnalysisType

app = FastAPI()
analyzer = LLMAnalyzer()

@app.post("/api/analyze/code")
async def analyze_code(code: str, language: str):
    """Analyze code with LLM"""
    result = analyzer.analyze_code_file(code, "input", language)
    if not result["success"]:
        raise HTTPException(500, result["error"])
    return result

@app.get("/api/artifacts/{id}/insights")
async def get_insights(id: str):
    """Get LLM insights for an artifact"""
    # Get from database
    artifact = db.get_artifact(id)
    if not artifact:
        raise HTTPException(404, "Artifact not found")
    return {
        "artifact": artifact,
        "insights": artifact.llm_analysis
    }

@app.post("/api/portfolio/generate")
async def generate_portfolio(project_data: dict):
    """Generate portfolio entry"""
    result = analyzer.generate_portfolio_entry(project_data)
    return result

@app.post("/api/analyze/batch")
async def batch_analyze(items: list):
    """Batch analyze multiple items"""
    results = analyzer.batch_analyze(items, AnalysisType.CODE_REVIEW)
    return {"results": results}
```

---

## Cost & Performance

### Token Usage Estimates

| Operation | Input Tokens | Output Tokens | Total | Cost (gpt-4o-mini) |
|-----------|-------------|---------------|-------|-------------------|
| Code review (50 lines) | ~300 | ~200 | ~500 | $0.0008 |
| Commit summary (20) | ~500 | ~300 | ~800 | $0.0012 |
| Portfolio entry | ~400 | ~500 | ~900 | $0.0014 |
| Skill extraction | ~200 | ~150 | ~350 | $0.0005 |

### Performance
- **Latency**: 1-3 seconds per analysis
- **Batch processing**: 10 items in ~15 seconds
- **Cache hit**: < 0.1 seconds
- **Rate limit**: 3,500 requests/minute (gpt-4o-mini)

---

## Security & Privacy

### Data Flow
```
User's Machine
     │
     ├─> Artifact data extracted locally
     │
     ├─> (Optional) PII redaction applied
     │
     ├─> Sent to OpenAI API (over HTTPS)
     │   • OpenAI doesn't train on API data
     │   • Data not stored by OpenAI
     │   • 30-day retention for abuse monitoring
     │
     └─> Response returned
         └─> Stored locally in your database
```

### Best Practices
1. **Redact PII** before sending to LLM (R12)
2. **Don't send sensitive** credentials, keys, passwords
3. **Use allowlists** to control what gets analyzed
4. **Store locally** - LLM results stay on user's machine
5. **User consent** - Clear about what's sent to OpenAI

---

## Future Enhancements

### Phase 1 (Current) ✅
- Basic LLM integration
- 6 analysis types
- Batch processing
- Error handling

### Phase 2 (Next)
- Result caching in database
- Asynchronous processing
- Background job queue
- Dashboard visualization

### Phase 3 (Later)
- Fine-tuned models for specific tasks
- Multi-model support (Anthropic, etc.)
- Advanced prompt templates
- A/B testing of prompts

---

## Quick Reference

### Import
```python
from llm_analyzer import LLMAnalyzer, AnalysisType
```

### Initialize
```python
analyzer = LLMAnalyzer(model="gpt-4o-mini")
```

### Analyze
```python
result = analyzer.analyze(content, AnalysisType.CODE_REVIEW)
print(result["analysis"])
```

### Custom
```python
result = analyzer.analyze(
    content=code,
    analysis_type=AnalysisType.CODE_REVIEW,
    custom_prompt="Focus on security",
    context={"language": "Python"}
)
```

---

## Documentation Map

- **Quick Start**: `src/QUICKSTART.md`
- **Full Setup**: `docs/LLM_SETUP_GUIDE.md`
- **Prompts**: `docs/PROMPT_ENGINEERING_GUIDE.md`
- **Architecture**: `docs/LLM_ARCHITECTURE.md` (this file)
- **Summary**: `LLM_INTEGRATION_SUMMARY.md`

---

## Questions?

Check the documentation or run the examples:
```bash
python src/example_usage.py
python src/integration_example.py
```

