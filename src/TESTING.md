# Testing Guide

This document describes how to run tests for the Document Summarization & Repository Analysis system.

## 🧪 Available Tests

### 1. List Supported File Formats
**Purpose**: Verify all file format parsers are registered  
**Command**:
```bash
cd src
python3 list_supported_formats.py
```
**Expected Output**: List of 35 supported file formats across 5 categories

---

### 2. Document Summarization Test
**Purpose**: Test document parsing and AI summarization  
**Command**:
```bash
cd src
python3 test_summarization.py <file_path>
```

**Examples**:
```bash
# Test with Word document
python3 test_summarization.py file-sample_1MB.docx

# Test with PDF
python3 test_summarization.py document.pdf

# Test with code file
python3 test_summarization.py ../src/parsers/document_parser.py
```

**Requirements**: OpenAI API key in `.env` file

**Expected Output**:
- File metadata (name, type, word count, etc.)
- Extracted text information
- AI-generated summary

---

### 3. Git Repository Analysis Test
**Purpose**: Analyze Git repositories for contributor insights  
**Command**:
```bash
cd src
python3 test_repository_analysis.py --repo <path>
```

**Examples**:
```bash
# Analyze current project
python3 test_repository_analysis.py --repo .

# Analyze with AI insights
python3 test_repository_analysis.py --repo . --ai

# Save report to file
python3 test_repository_analysis.py --repo . --output ../reports/analysis.txt
```

**Requirements**: 
- Git repository with `.git` directory
- Optional: OpenAI API key for AI insights

**Expected Output**:
- Repository overview (commits, branches, contributors)
- Contributor analysis with skills and quality metrics
- Code quality analysis
- Optional: AI-generated insights

---

### 4. Zip File Analysis Test
**Purpose**: Extract and analyze zip archives  
**Command**:
```bash
cd src
python3 test_repository_analysis.py --zip <path.zip>
```

**Examples**:
```bash
# Analyze zip file
python3 test_repository_analysis.py --zip project.zip

# With AI insights
python3 test_repository_analysis.py --zip portfolio.zip --ai --output report.txt
```

**Expected Output**:
- Extracted directory location
- List of Git repositories found
- Analysis for each repository
- Document summaries

---

## 🔧 Setup for Testing

### 1. Install Dependencies
```bash
cd src
pip3 install -r requirements.txt
```

### 2. Configure API Key (Optional but recommended)
```bash
cp env.example .env
# Edit .env and add your OpenAI API key
```

### 3. Verify Installation
```bash
python3 list_supported_formats.py
```

---

## ✅ Test Results

See [TEST_RESULTS.md](../TEST_RESULTS.md) for detailed test execution results and verification.

### Quick Summary
- ✅ 35 file formats supported and working
- ✅ Document parsing functional (.docx tested with 1,231 words)
- ✅ AI summarization working (OpenAI integration verified)
- ✅ Git repository analysis operational (60 commits, 9 contributors analyzed)
- ✅ Contributor skill detection working
- ✅ Code quality analysis functional (17 files analyzed)
- ✅ Report generation working

---

## 📊 Performance Benchmarks

### Document Summarization
- **Small files** (<100 KB): < 2 seconds
- **Medium files** (100 KB - 1 MB): 2-5 seconds
- **Large files** (1 MB - 5 MB): 5-15 seconds

### Repository Analysis
- **Small repos** (<100 commits): < 5 seconds
- **Medium repos** (100-1000 commits): 5-30 seconds
- **Large repos** (>1000 commits): 30-120 seconds

*Note: Times include AI summarization when enabled*

---

## 🐛 Troubleshooting

### "Module not found" errors
```bash
pip3 install -r requirements.txt
```

### "OpenAI API key not provided"
```bash
# Create .env file
cp env.example .env
# Edit .env and add: OPENAI_API_KEY=sk-...
```

### "Not a Git repository"
- Ensure the directory has a `.git` folder
- Or use `git init` to initialize

### "Insufficient quota" (OpenAI)
- Add credits to your OpenAI account
- Visit: https://platform.openai.com/account/billing

---

## 🧩 Component Testing

### Test Individual Components

#### Git Analyzer
```python
from analyzers.git_analyzer import GitAnalyzer

analyzer = GitAnalyzer("/path/to/repo")
data = analyzer.analyze_repository()
print(f"Total commits: {data['total_commits']}")
```

#### Document Parser
```python
from parsers.document_parser import DocumentParser

parser = DocumentParser()
result = parser.parse_file("document.pdf")
print(f"Word count: {result['word_count']}")
```

#### Contributor Analyzer
```python
from analyzers.contributor_analyzer import ContributorAnalyzer

contributor_data = {"files_touched": ["app.py", "test.js", "api.go"]}
skills = ContributorAnalyzer.analyze_contributor_skills(contributor_data)
print(skills['primary_languages'])
```

---

## 📝 Test Coverage

### Tested Features
- ✅ File format detection (35 formats)
- ✅ Document parsing (text extraction)
- ✅ AI summarization (OpenAI)
- ✅ Git repository analysis
- ✅ Contributor detection
- ✅ Skill analysis (language, frameworks)
- ✅ Code quality metrics
- ✅ Report generation

### Pending Tests
- ⚠️ Unit tests with pytest
- ⚠️ Error handling edge cases
- ⚠️ Zip file extraction
- ⚠️ Very large repositories (>10,000 commits)
- ⚠️ Multiple formats in one zip
- ⚠️ Corrupted file handling

---

## 🎯 Running Full Test Suite

```bash
# 1. Test file format detection
python3 list_supported_formats.py

# 2. Test document summarization
python3 test_summarization.py file-sample_1MB.docx

# 3. Test repository analysis
python3 test_repository_analysis.py --repo . --ai --output test_report.txt

# 4. Check report was generated
cat test_report.txt
```

All tests should complete without errors and produce expected outputs.

---

**Last Updated**: November 10, 2025  
**Test Status**: ✅ All Core Features Passing



