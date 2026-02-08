# Digital Work Artifact Miner

Team 14 — COSC 499 Capstone Project

Privacy-first pipeline that scans approved folders (code, docs, media), normalizes artifacts locally, and produces portfolio-ready insights with optional OpenAI-powered summarization.

## Quick links

- **[📚 Documentation Index](./docs/DOCUMENTATION_INDEX.md)** - Complete documentation overview
- **[⚡ Quick Commands](./docs/QUICK_COMMANDS.md)** - Ultra-short commands for common operations
- **[📅 Chronological Skills Guide](./docs/CHRONOLOGICAL_SKILLS_GUIDE.md)** - Complete guide for skills timeline
- [system demo walkthrough](./docs/system_demo_walkthrough.md)
- [test results](./docs/TEST_RESULTS.md)
- [team contract](./docs/plan/team14_team_contract.pdf)

## Getting started

### Prerequisites

- Docker
- OpenAI API key from https://platform.openai.com/api-keys (required for LLM-backed analysis)
- Optional: Python 3.11+ if you want to run scripts outside Docker

### Setup and first run (Docker)

1. Copy env template and add your key:

```bash
cp env.template .env
# edit .env and set OPENAI_API_KEY=<your key>
```

2. Build and start the backend (SQLite stored in `data/app.db`):

```bash
docker compose build backend
docker compose up -d backend
```

3. Run the pipeline on the sample ZIP (prompts for consent; runs local analysis if LLM declined):

```bash
docker compose run --rm backend python -m src.pipeline.orchestrator tests/categorize/demo_projects.zip
```

4. **Short commands**: Use the helper scripts for easier operations:

```bash
# Make scripts executable (one-time)
chmod +x scripts/*.sh

# Run pipeline (short version)
./scripts/run-pipeline.sh tests/categorize/demo_projects.zip

# View chronological skills
./scripts/chronological-skills.sh

# List all projects
./scripts/list-projects.sh

# Start API server
./scripts/start-api.sh
```

5. More commands (retrieving runs, deleting data, etc.) are in the [system demo walkthrough](./docs/system_demo_walkthrough.md) or [Quick Commands](./docs/QUICK_COMMANDS.md).

## Usage

- End-to-end demo script, retrieval commands, and clean-up steps live in `docs/system_demo_walkthrough.md`.
- FastAPI, adapters, and LLM behavior are described in `docs/LLM_ARCHITECTURE.md` and `docs/LLM_SETUP_GUIDE.md`.

## Project goals (what this app delivers)

- Local-first ingestion of approved folders with configurable allow/deny rules and size caps
- Normalized records for Git repos, Office/PDF docs, and media/design files
- Optional OpenAI-driven summaries (portfolio bullets, resume items, timelines, rankings)
- Exports (JSON/CSV/PDF) and retrieval via local SQLite database

## Testing

```bash
docker compose run --rm backend pytest -q
```

For integration runs that hit OpenAI, ensure `OPENAI_API_KEY` is set in `.env`.

## System Architecture Diagram

![System architecture diagram](docs/plan/revised-uml-diagram.png)

## Level 1 Data Flow Diagram

![Data flow diagram](docs/plan/level1dfd.png)

## Work Breakdown Structure (WBS)

### Mining Digital Work Artifacts System

### Team 14: Privacy-First Portfolio Mining Pipeline

---

## 1.0 Project Management

### 1.1 Project Planning

- Define project charter and scope statement
- Create detailed project schedule with milestones
- Develop risk management plan
- Establish communication protocols
- Define success metrics and KPIs

### 1.2 Team Coordination

- Conduct weekly team meetings
- Maintain project documentation repository
- Track task assignments and progress
- Manage inter-component dependencies
- Coordinate integration points between modules

### 1.3 Stakeholder Management

- Identify and document stakeholder requirements
- Conduct regular progress reviews
- Manage feedback and change requests
- Prepare and deliver status reports

---

## 2.0 Requirements Analysis & Design

### 2.1 Requirements Gathering

- Document functional requirements (FR-1 through FR-10)
- Document non-functional requirements (NFRs)
- Create requirements traceability matrix
- Validate requirements with stakeholders
- Baseline requirements documentation

### 2.2 System Architecture Design

- Design overall system architecture
- Create component interaction diagrams
- Design data flow diagrams (Level 0, Level 1)
- Define API contracts and interfaces
- Document technology stack decisions

### 2.3 Database Design

- Design normalized database schema
- Create entity-relationship diagrams
- Define indexes and optimization strategies
- Design audit log structure
- Plan data retention and purge strategies

### 2.4 Security & Privacy Design

- 2.4.1 Design redaction rule engine
- 2.4.2 Define PII detection patterns
- 2.4.3 Create privacy-preserving data flow
- 2.4.4 Design consent management system
- 2.4.5 Document security best practices

---

## 3.0 Scanner & Configuration Module

### 3.1 Configuration Management

- Implement configuration file parser
- Build configuration validation logic
- Create allowlist/denylist processor
- Implement file size and type limits
- Build configuration persistence layer

### 3.2 File System Scanner

- Implement directory traversal algorithm
- Build file enumeration service
- Create progress tracking mechanism
- Implement exclusion pattern matcher
- Add symbolic link and mount point handling

### 3.3 ZIP Upload Validator

- Implement ZIP file validation
- Build extraction service
- Create temporary storage manager
- Implement malware scanning hooks
- 3Add compression bomb detection

### 3.4 File Type Detection

- Implement MIME type detection
- Build file signature analyzer
- Create extension mapping service
- Implement content-based detection fallback
- Build adapter routing logic

---

## 4.0 Adapter Framework

### 4.1 Adapter Interface Design

- Define base adapter abstract class
- Create adapter registration system
- Implement adapter factory pattern
- Build adapter configuration management
- Create adapter testing framework

### 4.2 Git Repository Adapter

- Integrate GitPython/pydriller libraries
- Implement commit history extraction
- Build contributor analysis logic
- Extract branch and tag information
- Calculate code churn metrics
- Implement language detection
- Build timeline generation

### 4.3 Document Adapters

- 4.3.1 **Word Document Adapter (docx)**
  - Integrate python-docx library
  - Extract document metadata
  - Implement word/page counting
  - Extract revision history
  - Build content summarization
- 4.3.2 **PowerPoint Adapter (pptx)**
  - Integrate python-pptx library
  - Extract slide count and structure
  - Implement content extraction
  - Build presentation metadata parser
- 4.3.3 **PDF Adapter**
  - Integrate pdfminer library
  - Extract text and metadata
  - Implement page analysis
  - Build form field detection

### 4.4 Media/Design File Adapters

- Implement image metadata extraction (EXIF)
- Build video/audio duration extraction (ffprobe)
- Extract resolution and codec information
- Implement design file basic metadata parsing
- Build thumbnail generation service

### 4.5 Fallback Adapter

- Implement generic file metadata extraction
- Build basic file statistics collector
- Create unsupported file type handler

---

## 5.0 Data Processing Pipeline

### 5.1 Normalizer Component

- Design unified data schema
- Implement schema mapping logic
- Build data transformation pipelines
- Create field standardization rules
- Implement data validation layer

### 5.2 Deduplication System

- Implement file hashing (SHA-256)
- Build hash comparison engine
- Create duplicate detection algorithm
- Implement merge strategy for duplicates
- Build duplicate reporting mechanism

### 5.3 Redaction Engine

- Implement regex-based redaction rules
- Build PII detection patterns
  - Email address detection
  - Phone number detection
- Create field-level redaction logic
- Implement configurable redaction policies
- Build redaction preview system
- Create redaction audit trail

### 5.4 Data Storage Layer

- Implement SQLAlchemy ORM models
- Build database connection pool
- Create transaction management
- Implement batch insert optimization
- Build database migration system

---

## 6.0 Analytics & Insights Engine

### 6.1 Local Analysis Engine

- Implement contribution timeline calculator
  -Build project activity heatmap generator
- Create skill extraction algorithm
- Implement streak detection logic
- Build technology stack analyzer

### 6.2 LLM Integration (Optional)

- Design LLM consent checking system
- Implement LLM API integration layer
- Build prompt engineering templates
- Create response parsing logic
- Implement fallback to local analysis

### 6.3 Metrics Aggregation

- Build project summary statistics
- Implement contribution scoring algorithm
- Create ranking and prioritization logic
- Build cross-project analytics
- Implement time-series analysis

### 6.4 Portfolio Generation

- Design portfolio data structure
- Implement project highlight extraction
- Build résumé-ready content formatter
- Create skill categorization system
- Implement achievement detection

---

## 7.0 API Development

### 7.1 FastAPI Service Setup

- Initialize FastAPI application
- Configure middleware and CORS
- Implement dependency injection
- Set up request/response validation
- Configure API documentation (Swagger/OpenAPI)

### 7.2 REST Endpoints Implementation

- 7.2.1 **Configuration Endpoints**
  - POST /config/scan - Create scan configuration
  - GET /config/scan - Retrieve configurations
  - PUT /config/scan - Update configuration
  - DELETE /config/scan - Delete configuration
- 7.2.2 **Scanning Endpoints**
  - POST /scan/start - Initiate scan
  - GET /scan/status - Check scan progress
  - POST /scan/cancel - Cancel running scan
- 7.2.3 **Artifact Endpoints**
  - GET /artifacts - List all artifacts
  - GET /artifacts/{id} - Get artifact details
  - DELETE /artifacts/{id} - Remove artifact
- 7.2.4 **Insights Endpoints**
  - GET /insights/summary - Get overall summary
  - GET /insights/timeline - Get contribution timeline
  - GET /insights/skills - Get extracted skills
  - GET /insights/projects - Get project analytics
- 7.2.5 **Export Endpoints**
  - POST /export/json - Export as JSON
  - POST /export/csv - Export as CSV
  - POST /export/pdf - Export as PDF
- 7.2.6 **Privacy Endpoints**
  - GET /privacy/settings - Get privacy settings
  - PUT /privacy/settings - Update settings
  - POST /privacy/purge - Purge data

### 7.3 Authentication & Authorization

- Implement API key management
- Build rate limiting middleware
- Create access control logic
- Implement audit logging for API calls

---

## 8.0 Export & Reporting Module

### 8.1 Export Format Handlers

- 8.1.1 **JSON Exporter**
  - Design JSON schema
  - Implement serialization logic
  - Build schema validation
- 8.1.2 **CSV Exporter**
  - Design CSV structure
  - Implement flattening logic
  - Build CSV writer with encoding support
- 8.1.3 **PDF Exporter**
  - Design PDF template
  - Implement PDF generation (ReportLab)
  - Build chart and graph rendering
  - Create styling and formatting

### 8.2 Report Templates

- Create résumé summary template
- Build portfolio overview template
- Design project detail template
- Implement contribution report template
- Create skills matrix template

### 8.3 Data Filtering & Scoping

- Implement time window filtering
- Build project selection logic
- Create skill category filtering
- Implement contribution threshold filtering

---

## 9.0 Testing & Quality Assurance

### 9.1 Unit Testing

- Write adapter unit tests
- reate redaction engine tests
- Build configuration parser tests
- Implement normalizer tests
- Write API endpoint unit tests

### 9.2 Integration Testing

- Create end-to-end scan tests
- Build deduplication integration tests
- Implement full pipeline tests
- Create export workflow tests
- Build error handling scenario tests

### 9.3 Performance Testing

- Create large file handling tests
- Build concurrent scan tests
- Implement memory usage tests
- Create database performance tests

### 9.4 Security Testing

- Implement PII redaction verification
- Create injection attack tests
- Build access control tests
- Implement data leakage tests

### 9.5 User Acceptance Testing

- Create test scenarios document
- Build sample test datasets
- Conduct privacy settings testing
- Perform export validation testing
- Execute cross-platform testing

---

## 10.0 Infrastructure & DevOps

### 10.1 Development Environment

- Set up Python 3.11 environment
- Configure virtual environments
- Install and configure dependencies
- Set up IDE configurations
- Create development database instances

### 10.2 CI/CD Pipeline

- Configure GitHub Actions/GitLab CI
- Implement automated testing pipeline
- Set up code coverage reporting
- Configure linting and type checking
- Build automated deployment scripts

### 10.3 Containerization

- Create Docker images
- Write docker-compose configuration
- Implement container orchestration
- Build volume management for data persistence

### 10.4 Monitoring & Logging

- Implement application logging
- Set up error tracking
- Create performance monitoring
- Build audit log system
- Implement health check endpoints

---

## 11.0 Documentation

### 11.1 Technical Documentation

- Write API documentation
- Create adapter development guide
- Document database schema
- Write architecture decision records
- Create troubleshooting guide

### 11.2 User Documentation

- Write installation guide
- Create user manual
- Develop quick start guide
- Write privacy configuration guide
- Create FAQ document

### 11.3 Developer Documentation

- Write code contribution guidelines
- Create coding standards document
- Document testing procedures
- Write plugin development guide
- Create API integration examples

---

## 12.0 Deployment & Release

### 12.1 Release Preparation

- Conduct final integration testing
- Perform security audit
- Complete documentation review
- Create release notes
- Package distribution artifacts

### 12.2 Deployment Execution

- Deploy to production environment
- Run smoke tests
- Verify all endpoints
- Validate data persistence
- Confirm export functionality

### 12.3 Post-Deployment

- Monitor system performance
- Collect user feedback
- Address immediate issues
- Plan maintenance schedule
- Document lessons learned

---

## 13.0 Project Closure

### 13.1 Final Deliverables

- Compile final project report
- Create technical handover document
- Prepare demonstration materials
- Archive project artifacts
- Submit final codebase

### 13.2 Knowledge Transfer

- Conduct handover sessions
- Create maintenance guide
- Document known issues and roadmap
- Transfer ownership of repositories
- Provide support contact information
