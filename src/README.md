# Document Summarization & Repository Analysis with OpenAI

A comprehensive system for analyzing code repositories and documents with **AI-powered insights**. Supports **25+ file formats**, Git repository analysis, contributor skill detection, code quality metrics, and zip file processing.

## 🌟 Key Features

### 📚 Document Analysis
- **Multi-Format Support**: Extract text from 25+ file types
  - 📄 **Documents**: `.docx`, `.pdf`, `.rtf`, `.txt`, `.md`
  - 📊 **Spreadsheets**: `.csv`, `.xlsx`, `.xls`
  - 🎯 **Presentations**: `.pptx`
  - 💻 **Code Files**: `.py`, `.js`, `.java`, `.cpp`, `.ts`, `.go`, `.rs`, `.rb`, `.php`, and more
  - 🌐 **Markup**: `.html`, `.xml`, `.json`, `.yaml`
- **AI Summarization**: Generate concise summaries using OpenAI GPT models

### 🔬 Git Repository Analysis
- **Comprehensive Git Metrics**: Commits, contributors, branches, timelines
- **Contributor Analysis**: Automatic skill detection from code contributions
  - Primary programming languages with percentages
  - Framework and technology expertise
  - Work area categorization (Frontend, Backend, DevOps, etc.)
- **Contribution Statistics**: Lines added/deleted, files touched, activity periods
- **Quality Metrics**: 
  - Code quality scoring
  - Commit patterns analysis
  - Code churn detection
  - Quality indicators per contributor

### 📦 Zip File Processing
- **Automatic Extraction**: Extract and analyze zip archives
- **Repository Detection**: Find and analyze Git repositories in zip files
- **Batch Processing**: Analyze all documents and code in one go
- **Comprehensive Reports**: Generate detailed reports for entire archives

### 🤖 AI-Powered Insights
- **Repository Summaries**: High-level overview of project and contributors
- **Contributor Insights**: Personalized analysis of each developer's contributions
- **Document Summaries**: AI-generated summaries for all supported file types

### 🏗️ Architecture
- **Clean Architecture**: Modular, testable, and easy to extend
- **Privacy-First**: All processing happens locally, only text is sent to OpenAI

## 🚀 Quick Start

### 1. Get Your OpenAI API Key

You need an OpenAI API key to use this service:

1. Go to [https://platform.openai.com/](https://platform.openai.com/)
2. Sign up or log in to your account
3. Navigate to **API Keys** section: [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
4. Click **"Create new secret key"**
5. Copy the key (it will look like: `sk-proj-...` or `sk-...`)
6. **Important**: Save it somewhere safe - you won't be able to see it again!

**Note**: You may need to add credit to your account. OpenAI offers free trial credits for new users.

### 2. Set Up Your Environment

```bash
# Navigate to the src directory
cd src

# Install required dependencies
pip install -r requirements.txt
```

### 3. Configure Your API Key

Create a `.env` file in the `src` directory:

```bash
# Copy the example file
cp env.example .env

# Edit the .env file and add your API key
# Change this line:
OPENAI_API_KEY=your-openai-api-key-here
# To something like:
OPENAI_API_KEY=sk-proj-ABC123...XYZ789
```

**Using a text editor:**
```bash
# macOS/Linux
nano .env

# Or use any text editor
code .env  # VS Code
open -a TextEdit .env  # macOS TextEdit
```

### 4. Test It!

#### Document Summarization
```bash
# Summarize any supported document
python test_summarization.py path/to/your/file.docx
python test_summarization.py path/to/your/file.pdf
python test_summarization.py path/to/your/code.py
python test_summarization.py path/to/your/data.csv
```

#### Git Repository Analysis
```bash
# Analyze a Git repository (shows contributors, skills, quality metrics)
python test_repository_analysis.py --repo /path/to/repository

# With AI-powered insights
python test_repository_analysis.py --repo /path/to/repository --ai

# Save report to file
python test_repository_analysis.py --repo /path/to/repository --output report.txt

# Analyze current directory
python test_repository_analysis.py --repo .
```

#### Zip File Analysis
```bash
# Extract and analyze a zip file
python test_repository_analysis.py --zip project.zip --ai

# Works with repositories, documents, or both!
python test_repository_analysis.py --zip portfolio.zip --output analysis.txt
```

## 📖 Usage Examples

### Document Summarization

```python
from services.summarization_service import SummarizationService

# Initialize the service (reads API key from .env)
service = SummarizationService()

# Summarize a document
result = service.summarize_document("path/to/document.docx")

# Access the results
print(f"File: {result['file_name']}")
print(f"Word Count: {result['word_count']}")
print(f"Summary: {result['summary']}")
```

### Git Repository Analysis

```python
from services.repository_analysis_service import RepositoryAnalysisService
from services.report_generator import ReportGenerator

# Initialize service
service = RepositoryAnalysisService(api_key="your-openai-key")

# Analyze repository
results = service.analyze_repository(
    "/path/to/repo",
    analyze_code_quality=True,
    generate_ai_summary=True
)

# Access contributor data
for contributor in results['repository_analysis']['contributors']:
    print(f"\n{contributor['name']}:")
    print(f"  Commits: {contributor['commits']}")
    print(f"  Contribution: {contributor['percentage']:.1f}%")
    
    # Skills detected
    for lang in contributor['skills']['primary_languages']:
        print(f"  - {lang['language']}: {lang['percentage']:.1f}%")
    
    # Quality metrics
    metrics = contributor['quality_metrics']
    print(f"  Activity: {metrics['activity_level']}")
    print(f"  Quality indicators: {metrics['quality_indicators']}")

# Generate formatted report
report = ReportGenerator.generate_text_report(results)
print(report)

# Save to file
ReportGenerator.save_report(report, "analysis_report.txt")
```

### Zip File Analysis

```python
from services.repository_analysis_service import RepositoryAnalysisService

# Initialize service
service = RepositoryAnalysisService(api_key="your-openai-key")

# Analyze zip file (automatically detects repos and documents)
results = service.analyze_zip_file(
    "project_portfolio.zip",
    analyze_code_quality=True,
    generate_ai_summary=True
)

# Check what was found
print(f"Git Repositories: {results['summary']['total_git_repos']}")
print(f"Documents: {results['summary']['total_documents']}")
print(f"Total Contributors: {results['summary']['total_contributors']}")

# Access individual repository analyses
for repo_analysis in results['git_repositories']:
    repo_data = repo_analysis['repository_analysis']
    print(f"\nRepository: {repo_data['repository_path']}")
    print(f"Contributors: {repo_data['contributor_count']}")

# Cleanup temp files
service.cleanup()
```

### Custom Configuration

```python
# Use a specific API key
service = SummarizationService(api_key="sk-...")

# Customize summary length and model
result = service.summarize_document(
    "document.docx",
    max_summary_tokens=300,  # Shorter summary
    model="gpt-4o"  # Use more powerful model
)
```

### Parsing Only (No Summarization)

```python
from parsers.document_parser import DocumentParser

parser = DocumentParser()

# Universal parser - works with any supported format
data = parser.parse_file("any_supported_file.pdf")
print(f"File: {data['file_name']}")
print(f"Type: {data['file_type']}")
print(f"Text: {data['text']}")

# Specific parsers also available
docx_data = parser.parse_docx("document.docx")
pdf_data = parser.parse_pdf("document.pdf")
code_data = parser.parse_code("script.py")
csv_data = parser.parse_csv("data.csv")
html_data = parser.parse_html("page.html")

# Check if a file is supported
if parser.is_supported("unknown_file.xyz"):
    data = parser.parse_file("unknown_file.xyz")

# Get list of all supported formats
print(parser.get_supported_formats())
```

## 🏗️ Project Structure

```
src/
├── analyzers/                              # Analysis modules
│   ├── git_analyzer.py                    # Git repository analysis
│   ├── contributor_analyzer.py            # Contributor skill detection
│   └── code_quality_analyzer.py           # Code quality metrics
├── llm/
│   └── openai_client.py                   # OpenAI API wrapper
├── parsers/
│   └── document_parser.py                 # Document text extraction (25+ formats)
├── services/
│   ├── summarization_service.py           # Document summarization
│   ├── repository_analysis_service.py     # Repository analysis orchestration
│   └── report_generator.py                # Report formatting & export
├── utils/
│   └── zip_handler.py                     # Zip extraction & processing
├── test_summarization.py                  # Document summarization tests
├── test_repository_analysis.py            # Repository analysis tests
├── list_supported_formats.py              # List all supported file types
├── requirements.txt                       # Python dependencies
├── env.example                            # Environment variables template
└── README.md                              # This file
```

## 🧪 Testing

**✅ All Core Tests Passing** - See [TEST_RESULTS.md](../TEST_RESULTS.md) and [TESTING.md](TESTING.md) for details.

### Document Summarization Tests

```bash
python test_summarization.py your_document.docx
```

**Verified**: Tested with 1.2MB Word document (1,231 words) - Successfully parsed and summarized ✅

### Repository Analysis Tests

```bash
# Basic analysis (no AI)
python test_repository_analysis.py --repo /path/to/repo

# Full analysis with AI insights
python test_repository_analysis.py --repo /path/to/repo --ai --output report.txt

# Analyze a zip file
python test_repository_analysis.py --zip project.zip --ai
```

**Verified**: Tested on this project repository - Successfully analyzed 60 commits, 9 contributors ✅

### Example Output (Repository Analysis)

```
================================================================================
REPOSITORY ANALYSIS REPORT
================================================================================
Generated: 2025-01-10 15:30:45

📊 REPOSITORY OVERVIEW
--------------------------------------------------------------------------------
Repository Path: /path/to/project
Total Commits: 245
Branches: 8
Contributors: 4

📁 FILE TYPES
--------------------------------------------------------------------------------
  .py                   156 files
  .js                    89 files
  .md                    23 files

👥 CONTRIBUTORS
================================================================================

1. John Doe <john@example.com>
--------------------------------------------------------------------------------
   Commits: 128 (52.2%)
   Lines Added: +5,234
   Lines Deleted: -1,876
   Files Touched: 87

   💡 PRIMARY SKILLS:
      • Python              65.5% (57 files)
      • JavaScript          25.3% (22 files)
      • TypeScript           9.2% (8 files)

   🛠️  FRAMEWORKS & TOOLS:
      • FastAPI                   (15 mentions)
      • React                     (12 mentions)
      • Docker                    (8 mentions)

   📋 WORK AREAS:
      • Backend                45 files
      • Frontend               22 files
      • Testing                12 files

   📊 QUALITY METRICS:
      Activity Level: Very High
      Avg Lines/Commit: 55.5
      Files/Commit: 0.7
      Code Churn: 35.8%

   ✨ QUALITY INDICATORS:
      • Small, focused commits
      • Low code churn (stable code)
      • Focused changes

🤖 AI-POWERED INSIGHTS
================================================================================
This repository shows a well-structured project with consistent contribution
patterns. The main contributors demonstrate expertise in modern web development
technologies, particularly Python backend (FastAPI) and React frontend...
```

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | Your OpenAI API key |

### Model Options

The default model is `gpt-4o-mini` (fast and cost-effective). You can change it to:

- `gpt-4o-mini`: Fastest and cheapest (recommended)
- `gpt-4o`: More capable, higher cost
- `gpt-4-turbo`: Previous generation, balanced
- `gpt-3.5-turbo`: Older, cheaper but less accurate

### Cost Estimates (approximate)

Using `gpt-4o-mini`:
- Small document (< 1000 words): ~$0.001 - $0.005
- Medium document (1000-5000 words): ~$0.005 - $0.02
- Large document (5000+ words): ~$0.02 - $0.10

## 🔒 Security & Privacy

- **API Key**: Never commit your `.env` file! It's already in `.gitignore`
- **Local Processing**: Document parsing happens locally
- **Data Sent**: Only extracted text is sent to OpenAI for summarization
- **No Storage**: OpenAI doesn't store your data (per their API terms)

## 🛠️ Troubleshooting

### "OpenAI API key not provided"
- Make sure you've created the `.env` file
- Check that your API key is correctly formatted
- Ensure the `.env` file is in the same directory as your script

### "File not found"
- Check the file path is correct
- Use absolute paths if relative paths don't work

### "Failed to parse DOCX/PPTX file"
- Ensure the file isn't corrupted
- Check that the file extension matches the actual format
- Try opening the file in Word/PowerPoint to verify it works

### "Rate limit exceeded"
- You've hit OpenAI's rate limits
- Wait a few seconds and try again
- Consider upgrading your OpenAI plan

### "Insufficient quota"
- Your OpenAI account has run out of credits
- Add payment method and credits at [https://platform.openai.com/account/billing](https://platform.openai.com/account/billing)

## 📚 Dependencies

### Core Dependencies
- **openai**: Official OpenAI Python library
- **python-dotenv**: Load environment variables

### Document Parsing
- **python-docx**: Word documents (`.docx`)
- **python-pptx**: PowerPoint presentations (`.pptx`)
- **pypdf**: PDF documents (`.pdf`)
- **openpyxl**: Excel files (`.xlsx`, `.xls`)
- **beautifulsoup4** + **lxml**: HTML/XML parsing
- **striprtf**: RTF documents (`.rtf`)
- **PyYAML**: YAML files (`.yaml`, `.yml`)

Built-in libraries handle: `.txt`, `.md`, `.csv`, `.json`, and code files

## 📋 Supported File Types

| Category | Formats | Extensions |
|----------|---------|------------|
| **Documents** | Word, PDF, RTF, Text, Markdown | `.docx`, `.pdf`, `.rtf`, `.txt`, `.md`, `.rst` |
| **Presentations** | PowerPoint | `.pptx` |
| **Spreadsheets** | CSV, Excel | `.csv`, `.xlsx`, `.xls` |
| **Code** | Python, JavaScript, TypeScript, Java, C/C++, Go, Rust, Ruby, PHP, Swift, Kotlin | `.py`, `.js`, `.ts`, `.jsx`, `.tsx`, `.java`, `.cpp`, `.c`, `.h`, `.go`, `.rs`, `.rb`, `.php`, `.swift`, `.kt`, `.cs`, `.r`, `.m` |
| **Markup** | HTML, XML, JSON, YAML | `.html`, `.htm`, `.xml`, `.json`, `.yaml`, `.yml` |

**Total**: 25+ file formats supported!

## 🔄 Next Steps

Potential enhancements:

1. **Batch Processing**: Summarize multiple files at once
2. **Custom Prompts**: Different summarization styles (bullet points, executive summary, etc.)
3. **Caching**: Store summaries to avoid re-processing
4. **API Integration**: Wrap this in a FastAPI service
5. **Error Recovery**: Retry logic for transient failures
6. **OCR Support**: Extract text from images
7. **Audio Transcription**: Summarize audio/video with Whisper API

## 📄 License

Part of the capstone-project-team-14 repository.

## 🤝 Contributing

This is a team project. For questions or improvements, contact the team members listed in the project README.

---

## 🎯 Use Cases

### For Students & Graduates
- **Portfolio Analysis**: Analyze your capstone/thesis repositories
- **Skill Documentation**: Automatically detect and document your technical skills
- **Project Summaries**: Generate professional summaries of your work

### For Instructors & Reviewers
- **Project Assessment**: Quickly understand contribution patterns
- **Skill Verification**: See what technologies students actually used
- **Quality Review**: Assess code quality and commitment patterns

### For Hiring Managers
- **Candidate Evaluation**: Analyze GitHub repositories from candidates
- **Skill Verification**: See real contributions vs. resume claims
- **Team Composition**: Understand skill distribution in existing teams

### For Teams
- **Onboarding**: Help new members understand codebase and contributors
- **Retrospectives**: Analyze contribution patterns over time
- **Documentation**: Auto-generate contributor skill matrices

---

## 🚀 Quick Reference

### Setup (One Time)
```bash
cd src
pip install -r requirements.txt
cp env.example .env
# Edit .env and add your OpenAI API key
```

### Commands
```bash
# Document summarization
python test_summarization.py document.pdf

# Repository analysis
python test_repository_analysis.py --repo . --ai

# Zip file analysis
python test_repository_analysis.py --zip project.zip --ai --output report.txt

# List supported formats
python list_supported_formats.py
```

**Get API Key:** [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)

## 📊 What Gets Analyzed

### Repository Metrics
- ✅ Total commits, branches, contributors
- ✅ Commit timeline and activity patterns
- ✅ File types and extensions distribution
- ✅ Contributor contribution percentages

### Contributor Analysis
- ✅ Programming languages used (with percentages)
- ✅ Frameworks and technologies detected
- ✅ Work areas (Frontend, Backend, DevOps, Testing, etc.)
- ✅ Lines of code added/deleted
- ✅ Files touched and modified
- ✅ Activity period (first to last commit)
- ✅ Activity level classification

### Code Quality Metrics
- ✅ Code vs. comment ratio
- ✅ Code complexity indicators
- ✅ Code smell detection
- ✅ Commit patterns and quality
- ✅ Overall quality scoring (0-100)

### AI-Generated Insights
- ✅ Repository overview and summary
- ✅ Personalized contributor insights
- ✅ Technology stack analysis
- ✅ Contribution pattern analysis

