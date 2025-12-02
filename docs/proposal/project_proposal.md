# Project Proposal for Data Mining Project  

**Team Number:** 15  
- Rylan Millar - 33334400  
- Alex Batke - 34354803  
- Cole Powrie - 77174209  
- Liam Storgaard - 64584279  
- Will Tilden - 61350294  
- Luis Wen Luo - 10665891  

---

# 1. Project Scope and Usage Scenario  

The system is designed for graduating students and early-career professionals who want to reflect on and showcase their digital work history.  

The primary user group consists of individuals who regularly produce digital artifacts such as code repositories, documents, designs, and notes on their personal computers. Using the web-based application, a user uploads or selects directories to scan, after which the system extracts and analyzes metadata, categorizes artifacts, and generates productivity metrics and timelines of project evolution.  

A web-based dashboard then visualizes the results, allowing users to filter, search, and preview artifacts, while also offering export options to create tailored summaries for résumés or digital portfolios.  

Secondary users may include career advisors or recruiters who could review these summaries, but the core focus remains empowering individuals to better understand and present their own work artifacts.  

---

# 2. Proposed Solution  

Our solution is a **local-first digital mining system** that enables users to drop in files for automatic extraction, analysis, and visualization of the work artifacts they’ve created over time. By combining high-performance preprocessing in **Rust** with a pretrained **PyTorch machine learning model**, the system can identify file types, detect skills and programming languages, highlight collaboration patterns, and generate productivity metrics along with project timelines. The results are then displayed in a modern, intuitive web-based dashboard, where users can filter, search, preview, and export personalized summaries for use in résumés or digital portfolios.  

What makes our solution unique is its **focus on speed, privacy, and usability**. In contrast to approaches that rely heavily on cloud infrastructure, all processing occurs **entirely on the user’s local machine**, preserving privacy and ensuring ethical handling of data. Rust’s efficiency and memory safety allow the system to process large collections of files quickly, while machine learning produces insights that go far beyond raw metadata. Compared to other solutions, our approach emphasizes scalability, responsiveness, and a polished user experience, ensuring that users gain not just information, but **clear, actionable insights** they can confidently present to demonstrate their skills and professional growth.  

---

# 3. Use Cases  

### Use Case 1: Upload and Analyze Archive  
**Actor:** Student/Professional  
**Description:** User submits a compressed archive of projects for categorization.  

- **Preconditions:** Valid archive, services online  
- **Postconditions:** Archive decompressed, filtered, analyzed → project summaries generated  

**Main Scenario:**
1. User drags archive into drop zone  
2. Sets search scope (languages, file types, ignore `.gitignore`, etc.)  
3. Backend unpacks and processes  
4. Rust preprocessor chunks content and caches files  
5. ML model classifies chunks (skills, domains, languages)  
6. Postprocessor compiles labels into summaries  
7. Results returned and displayed in dashboard  

**Extensions:** Unsupported file, decompression error, large archive, empty content, ML service unavailable  

---

### Use Case 2: Review and Refine Results  
**Actor:** Student/Professional  
**Description:** User reviews analysis results and adjusts categories/tags.  

- **Preconditions:** Completed analysis exists  
- **Postconditions:** Curated results stored in session  

**Main Scenario:**
1. User reviews results table  
2. Selects/filters tags and categories  
3. Adjusts thresholds  
4. Backend recomputes summaries incrementally  
5. Updated results shown in dashboard  

**Extensions:** Handle no confident tags, conflicting categories, recomputation safeguards  

---

### Use Case 3: Export Portfolio Summary  
**Actor:** Student/Professional  
**Description:** User exports a polished summary document (HTML/PDF/JSON).  

- **Preconditions:** Curated results exist  
- **Postconditions:** Exported summary available for download  

**Main Scenario:**
1. User selects export options  
2. Backend serializes summary  
3. Frontend prompts download  

**Extensions:** Missing sections, large artifacts, serialization errors  

---

# 4. Requirements, Testing, and Verification  

### Technology Stack  
- **Frontend:** React.js + TypeScript  
- **Backend:** Rust (preprocessing), Python (FastAPI + PyTorch ML)  
- **Communication:** gRPC / Unix sockets  
- **Database:** SQLite or JSON store (local caching)  
- **Visualization:** Chart.js / D3.js  
- **Packaging:** Electron / WebAssembly (optional local runtime)  

---

### Testing Framework  
- **Frontend:** Jest, React Testing Library, Cypress  
- **Backend:** Pytest (Python), Cargo test (Rust)  
- **Integration:** Postman / Pytest + docker-compose  
- **CI/CD:** GitHub Actions  

---

### Functional Requirements  

| Requirement | Description | Test Cases | Who | H/M/E |
|-------------|-------------|------------|-----|-------|
| File Upload & Validation | User uploads compressed archive; validate type/size; handle errors | Upload valid `.zip`, reject invalid type, error on empty archive | Liam | Medium |
| Archive Extraction | Decompress and filter files | Valid decompress, missing index handled, ignored files excluded | Liam | Hard |
| Preprocessing Engine | Rust scans directories, chunks files, extracts metadata | Process 1000 files, <200MB memory, invalid path handled | Liam | Hard |
| ML Classification | PyTorch classifies chunks | Known types → correct classification, unknown → unclassified, offline → queued | Luis/Rylan | Hard |
| Result Aggregation | Combine predictions, resolve categories, compute metrics | Correct category, handle no confident tags, resolve conflicts | Luis | Medium |
| Frontend Visualization | Display sortable/filterable table & charts | Table renders, filters work, missing data handled | Cole & Will | Medium |
| User Refinement Tools | Adjust tags, thresholds, recompute summaries | Adjust threshold → updated results, exclude tags → recompute | Cole & Will | Medium |
| Export Summary | Generate HTML/PDF/JSON exports | Valid export, warnings for missing sections, handle large files | Rylan | Easy |
| Error Handling | Clear error messages, no crashes | Invalid upload → error, ML timeout → retry | Alex | Medium |

---

### Non-Functional Requirements  

| Requirement | Description | Test Cases | Who | H/M/E |
|-------------|-------------|------------|-----|-------|
| Performance | Scan ≤10s for 500 files | Benchmark processing, log response times | Rylan | Hard |
| Usability | UI intuitive, drag-and-drop, toggles | User testing, WCAG compliance | Will | Medium |
| Reliability | No crashes on large input (10k files) | Stress test, monitor memory | Will | Hard |
| Security & Privacy | Runs locally only | Network monitoring, no external requests | Alex | Medium |
| Maintainability | Documented & tested code | Check docs, run test suites | Team | Easy |
| Privacy & Local Execution | No external data sent | Verify no network calls, check logs | Will | Medium |
| Usability (extended) | Minimal steps, clean UI, user feedback | Manual testing with 3 users, navigation clarity >4/5 | Alex & Will | Easy |

---
