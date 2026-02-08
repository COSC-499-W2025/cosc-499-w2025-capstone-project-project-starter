# Pipeline Orchestrator

The pipeline orchestrator connects all analysis components to provide a unified interface for analyzing project artifacts from ZIP files.

## Overview

The orchestrator follows a **project-centric architecture** where each top-level directory in the ZIP file is treated as an individual project. The pipeline performs these steps for each project:

1. **Parse ZIP**: Extracts and validates the ZIP file, computing metadata and hashes
2. **Identify Projects**: Discovers top-level directories as individual projects
3. **Git Analysis** (if applicable): Analyzes Git repositories to extract contributor metrics
4. **Categorize Files**: Classifies files by type (code, documentation, images, videos)
5. **Analyze Files**: Runs specialized analyzers for each file type
   - **Code Analyzer**: Extracts languages, frameworks, and skills from code files
   - **Text Analyzer**: Analyzes documentation (PDF, DOCX, TXT, MD) for metrics
   - **Image Processor**: Analyzes images for content, resolution, and features
   - **Video Analyzer**: Extracts video metadata and optionally transcribes audio

## Architecture

```
orchestrator.py
    ├── ZIP Parser (parse & extract)
    ├── Project Detection (identify top-level directories)
    └── For each project:
        ├── Git Analyzer (if .git exists)
        ├── File Categorizer (classify by type)
        └── Analysis Layer:
            ├── Code Analyzer
            ├── Text Analyzer
            ├── Image Processor
            └── Video Analyzer
```

## Usage

### From Command Line

```bash
# Using the module directly (from root dir)
python3 -m src.pipeline.orchestrator tests/categorize/demo_projects.zip
```

The CLI now prompts once for consent before using the optional LLM summarization
service. Your choice is stored in the local user configuration database (keyed
by `--user-id` or `$PIPELINE_USER_ID`, defaulting to the current OS user). If you
opt out, only the local analyzers run; opting in adds the LLM summaries at the
end of the pipeline run.

## Output Format

The `start()` method returns a **project-centric** dictionary with two main sections:

```json
{
  "zip_metadata": {
    "root_name": "projects.zip",
    "file_count": 127,
    "total_uncompressed_bytes": 5242880,
    "total_compressed_bytes": 2621440
  },
  "projects": {
    "project-webapp": {
      "project_name": "project-webapp",
      "project_path": "/tmp/unzipped_xyz/project-webapp",
      "is_git_repo": true,
      "git_analysis": {
        "total_commits": 243,
        "total_contributors": 5,
        "contributors": [
          {
            "author": {"name": "John Doe", "email": "john@example.com"},
            "commits": 120,
            "insertions": 5420,
            "deletions": 2130,
            "files_touched": 45,
            "active_weeks": 12,
            "first_commit_at": "2024-01-15",
            "last_commit_at": "2024-03-20",
            "activity_mix": {
              "feature": 60,
              "bugfix": 30,
              "refactor": 20,
              "docs": 5,
              "test": 5,
              "other": 0
            },
            "share_of_commits_pct": 49.38,
            "top_files": [
              {"path": "src/main.py", "touches": 25}
            ]
          }
        ]
      },
      "categorized_contents": {
        "code": [...],
        "code_by_language": {"python": [...], "javascript": [...]},
        "documentation": [...],
        "images": [...],
        "other": [...]
      },
      "analysis_results": {
        "code": {
          "files": [...],
          "metrics": {
            "total_files": 30,
            "total_lines": 5420,
            "languages": ["python", "javascript"],
            "frameworks": ["django", "react"],
            "skills": [...],
            "code_files": 28,
            "test_files": 2
          }
        },
        "documentation": {
          "files": [...],
          "totals": {
            "total_files": 5,
            "total_words": 2500,
            "total_reading_time_minutes": 12.5
          }
        },
        "images": [...],
        "videos": {...}
      }
    },
    "project-mobile": {
      "is_git_repo": false,
      "categorized_contents": {...},
      "analysis_results": {...}
    }
  }
}
```

## Project Structure

Each project in the `projects` dictionary contains:

- **`project_name`**: Name of the project (directory name)
- **`project_path`**: Absolute path to the project directory
- **`is_git_repo`**: Boolean indicating if this is a Git repository
- **`git_analysis`**: Git metrics (only if `is_git_repo` is true)
  - **`total_commits`**: Total number of commits
  - **`total_contributors`**: Number of unique contributors
  - **`contributors`**: Array of contributor metrics
- **`categorized_contents`**: File categorization by type
  - **`code`**: List of code file paths
  - **`code_by_language`**: Dictionary mapping languages to file paths
  - **`documentation`**: List of documentation files
  - **`images`**: List of image files
  - **`other`**: List of other files (includes videos)
- **`analysis_results`**: Results from specialized analyzers
  - **`code`**: Code analysis (languages, frameworks, LOC)
  - **`documentation`**: Text analysis (word count, reading time)
  - **`images`**: Image analysis (resolution, content type)
  - **`videos`**: Video analysis (duration, format)

## Example Output

```
======================================================================
🚀 Starting Artifact Pipeline
======================================================================
📦 ZIP File: demo_projects.zip

[1/6] Parsing ZIP file metadata...
✓ Parsed 45 files

[2/6] Extracting ZIP contents...
✓ Extracted to: /tmp/unzipped_abc123

[3/6] Identifying projects (top-level directories)...
✓ Found 2 project(s): project-webapp, project-mobile

[4/6] Processing each project...

  📁 Processing project: project-webapp
     🔍 Git repository detected
     📊 Running Git analysis...
     ✓ Git analysis complete
     📁 Categorizing files...
     ✓ Categorized: 25 code, 3 docs, 2 images
     🔬 Running file analyzers...
  📄 Analyzing 3 documentation file(s)...
     ✓ Documentation analysis complete
  🖼️  Analyzing 2 image file(s)...
     ✓ Image analysis complete
  💻 Analyzing 25 code file(s)...
     ✓ Code analysis complete (25 files)
  🎥 No video files to analyze
     ✓ Analysis complete

  📁 Processing project: project-mobile
     ℹ️  Not a Git repository
     📁 Categorizing files...
     ✓ Categorized: 15 code, 2 docs, 3 images
     🔬 Running file analyzers...
     ✓ Analysis complete

[5/6] Compiling results...

[6/6] Generating summary...

======================================================================
✅ Pipeline Complete!
======================================================================

📊 ZIP Summary:
   • Total files: 45
   • Uncompressed size: 2.50 MB
   • Compressed size: 1.25 MB

📦 Projects Found: 2

──────────────────────────────────────────────────────────────────────
📁 Project: project-webapp
──────────────────────────────────────────────────────────────────────
   🔍 Git Repository: YES
      • Total commits: 243
      • Contributors: 3
      • Top contributors:
         1. John Doe (120 commits)
         2. Jane Smith (80 commits)
         3. Bob Wilson (43 commits)

   📁 File Categorization:
      • Code files: 25
        Languages detected:
          - python: 15 files
          - javascript: 10 files
      • Documentation files: 3
      • Image files: 2
      • Video files: 0

   🔬 Analysis Results:
      • Documentation: 3 files, 2,500 words
      • Images: 2 files, 1.25 MB
      • Code: 25 files, 5,420 lines
        Languages: javascript, python
```

## Features

✅ **Multi-project support**: Each top-level directory is analyzed independently  
✅ **Git integration**: Automatic detection and analysis of Git repositories  
✅ **Comprehensive analysis**: Code, documentation, images, and videos  
✅ **Project-centric output**: Results organized by project and file type  
✅ **Automatic cleanup**: Temporary files are cleaned up after analysis

## Testing

```bash
# Test with a sample ZIP file (from root dir)
python3 -m src.pipeline.orchestrator tests/categorize/demo_projects.zip

# Output will be saved to orchestrator_output.json
```
