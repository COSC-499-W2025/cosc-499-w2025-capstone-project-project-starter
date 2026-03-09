import React, { useCallback, useEffect, useMemo, useState } from "react";
import "./App.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:5000";

function App() {
  const [activeTab, setActiveTab] = useState("scan");
  const [apiStatus, setApiStatus] = useState("checking");
  const [apiMessage, setApiMessage] = useState("");

  const [scans, setScans] = useState([]);
  const [scansLoading, setScansLoading] = useState(false);
  const [selectedScanId, setSelectedScanId] = useState("");

  const [scanZipFile, setScanZipFile] = useState(null);
  const [scanMode, setScanMode] = useState("basic");
  const [scanConsent, setScanConsent] = useState(true);
  const [scanPersist, setScanPersist] = useState(true);
  const [scanAllowDuplicate, setScanAllowDuplicate] = useState(false);
  const [scanIncremental, setScanIncremental] = useState(false);
  const [scanIncrementalTarget, setScanIncrementalTarget] = useState("");
  const [advancedOptions, setAdvancedOptions] = useState({
    programming_scan: true,
    framework_scan: true,
    skills_gen: true,
    resume_gen: true,
  });
  const [scanRunning, setScanRunning] = useState(false);
  const [scanResult, setScanResult] = useState(null);
  const [scanError, setScanError] = useState("");

  const [resumeTitle, setResumeTitle] = useState("Generated Resume");
  const [resumeScanId, setResumeScanId] = useState("");
  const [resumeProjects, setResumeProjects] = useState([]);
  const [resumeSelectedProjectIds, setResumeSelectedProjectIds] = useState([]);
  const [resumeLoadingProjects, setResumeLoadingProjects] = useState(false);
  const [resumeGenerating, setResumeGenerating] = useState(false);
  const [resumeArtifact, setResumeArtifact] = useState(null);
  const [resumeError, setResumeError] = useState("");
  const [resumeExporting, setResumeExporting] = useState(false);

  const [portfolioTitle, setPortfolioTitle] = useState("Generated Portfolio");
  const [portfolioScanId, setPortfolioScanId] = useState("");
  const [portfolioProjects, setPortfolioProjects] = useState([]);
  const [portfolioSelectedProjectIds, setPortfolioSelectedProjectIds] = useState([]);
  const [portfolioLoadingProjects, setPortfolioLoadingProjects] = useState(false);
  const [portfolioGenerating, setPortfolioGenerating] = useState(false);
  const [portfolioArtifact, setPortfolioArtifact] = useState(null);
  const [portfolioError, setPortfolioError] = useState("");
  const [portfolioExporting, setPortfolioExporting] = useState(false);
  const [portfolioViewMode, setPortfolioViewMode] = useState("private");
  const [portfolioSearch, setPortfolioSearch] = useState("");
  const [projectEdits, setProjectEdits] = useState({});

  const fetchJson = useCallback(async (path, options = {}) => {
    const response = await fetch(`${API_BASE}${path}`, options);
    const contentType = response.headers.get("content-type") || "";

    let payload = null;
    if (contentType.includes("application/json")) {
      payload = await response.json();
    } else {
      payload = await response.text();
    }

    if (!response.ok) {
      const errorMessage =
        (payload && payload.error) ||
        (typeof payload === "string" && payload) ||
        `Request failed (${response.status})`;
      throw new Error(errorMessage);
    }
    return payload;
  }, []);

  const downloadArtifact = useCallback(async (path, fallbackFileName) => {
    const response = await fetch(`${API_BASE}${path}`);
    if (!response.ok) {
      let message = `Download failed (${response.status})`;
      const contentType = response.headers.get("content-type") || "";
      if (contentType.includes("application/json")) {
        const body = await response.json();
        message = body.error || message;
      }
      throw new Error(message);
    }

    const blob = await response.blob();
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    const disposition = response.headers.get("content-disposition") || "";
    const match = disposition.match(/filename="?([^"]+)"?/i);
    const fileName = match?.[1] || fallbackFileName;
    link.href = url;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }, []);

  const loadScans = useCallback(async () => {
    setScansLoading(true);
    try {
      const data = await fetchJson("/scans");
      const nextScans = data.scans || [];
      setScans(nextScans);
      if (nextScans.length > 0) {
        const firstId = String(nextScans[0].summary_id);
        setSelectedScanId((prev) => prev || firstId);
        setResumeScanId((prev) => prev || firstId);
        setPortfolioScanId((prev) => prev || firstId);
      }
    } catch (error) {
      setApiStatus("offline");
      setApiMessage(error.message);
    } finally {
      setScansLoading(false);
    }
  }, [fetchJson]);

  const loadProjectsForScan = useCallback(
    async (scanId, config) => {
      if (!scanId) {
        config.setError("");
        config.setProjects([]);
        config.setSelected([]);
        return;
      }
      config.setLoading(true);
      try {
        config.setError("");
        const data = await fetchJson(`/projects?scan_id=${encodeURIComponent(scanId)}`);
        const projects = data.projects || [];
        config.setProjects(projects);
        config.setSelected(config.limit ? projects.slice(0, config.limit).map((p) => p.project_id) : projects.map((p) => p.project_id));
      } catch (error) {
        config.setError(error.message);
      } finally {
        config.setLoading(false);
      }
    },
    [fetchJson]
  );

  useEffect(() => {
    let cancelled = false;
    const checkApi = async () => {
      try {
        const data = await fetchJson("/health");
        if (!cancelled) {
          setApiStatus(data.status === "ok" ? "online" : "offline");
          setApiMessage(data.status === "ok" ? "API ready" : "API health check failed");
        }
      } catch (error) {
        if (!cancelled) {
          setApiStatus("offline");
          setApiMessage(error.message);
        }
      }
    };

    checkApi();
    loadScans();
    return () => {
      cancelled = true;
    };
  }, [fetchJson, loadScans]);

  useEffect(() => {
    loadProjectsForScan(resumeScanId, {
      setProjects: setResumeProjects,
      setSelected: setResumeSelectedProjectIds,
      setLoading: setResumeLoadingProjects,
      setError: setResumeError,
      limit: 0,
    });
  }, [resumeScanId, loadProjectsForScan]);

  useEffect(() => {
    loadProjectsForScan(portfolioScanId, {
      setProjects: setPortfolioProjects,
      setSelected: setPortfolioSelectedProjectIds,
      setLoading: setPortfolioLoadingProjects,
      setError: setPortfolioError,
      limit: 3,
    });
    setProjectEdits({});
  }, [portfolioScanId, loadProjectsForScan]);

  const handleAdvancedOptionToggle = (key) => {
    setAdvancedOptions((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleRunScan = async (event) => {
    event.preventDefault();
    setScanError("");
    setScanResult(null);

    if (!scanZipFile) {
      setScanError("Select a .zip file before scanning.");
      return;
    }

    setScanRunning(true);
    try {
      const formData = new FormData();
      formData.append("zip", scanZipFile);
      formData.append("analysis_mode", scanMode);
      formData.append("consent", String(scanConsent));
      formData.append("persist", String(scanPersist));
      formData.append("allow_duplicate", String(scanAllowDuplicate));
      formData.append("incremental", String(scanIncremental));

      if (scanMode === "advanced") {
        formData.append("advanced_options", JSON.stringify(advancedOptions));
      }
      if (scanIncremental && scanIncrementalTarget) {
        formData.append("existing_scan_id", scanIncrementalTarget);
      }

      const result = await fetchJson("/projects/upload", {
        method: "POST",
        body: formData,
      });
      setScanResult(result);
      await loadScans();

      if (result.summary_id) {
        const sid = String(result.summary_id);
        setSelectedScanId(sid);
        setResumeScanId(sid);
        setPortfolioScanId(sid);
      }
    } catch (error) {
      setScanError(error.message);
    } finally {
      setScanRunning(false);
    }
  };

  const toggleResumeProject = (projectId) => {
    setResumeSelectedProjectIds((prev) =>
      prev.includes(projectId) ? prev.filter((id) => id !== projectId) : [...prev, projectId]
    );
  };

  const handleGenerateResume = async () => {
    setResumeError("");
    setResumeArtifact(null);

    if (!resumeScanId) {
      setResumeError("Select a scan first.");
      return;
    }
    if (resumeSelectedProjectIds.length === 0) {
      setResumeError("Select at least one project.");
      return;
    }

    setResumeGenerating(true);
    try {
      const payload = {
        scan_id: Number(resumeScanId),
        title: resumeTitle.trim() || "Generated Resume",
        selected_project_ids: resumeSelectedProjectIds,
        project_order: resumeSelectedProjectIds,
      };
      const data = await fetchJson("/resume/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setResumeArtifact(data.resume);
    } catch (error) {
      setResumeError(error.message);
    } finally {
      setResumeGenerating(false);
    }
  };

  const handleExportResume = async () => {
    if (!resumeArtifact?.resume_id) return;
    setResumeExporting(true);
    setResumeError("");
    try {
      await downloadArtifact(`/resume/${resumeArtifact.resume_id}/export`, "resume.docx");
    } catch (error) {
      setResumeError(error.message);
    } finally {
      setResumeExporting(false);
    }
  };

  const togglePortfolioProject = (projectId) => {
    setPortfolioError("");
    setPortfolioSelectedProjectIds((prev) => {
      if (prev.includes(projectId)) {
        return prev.filter((id) => id !== projectId);
      }
      if (prev.length >= 3) {
        setPortfolioError("Portfolio showcase is limited to top 3 projects.");
        return prev;
      }
      return [...prev, projectId];
    });
  };

  const updateProjectEdit = (projectId, key, value) => {
    setProjectEdits((prev) => ({
      ...prev,
      [projectId]: {
        ...prev[projectId],
        [key]: value,
      },
    }));
  };

  const handleGeneratePortfolio = async () => {
    setPortfolioError("");
    setPortfolioArtifact(null);

    if (!portfolioScanId) {
      setPortfolioError("Select a scan first.");
      return;
    }
    if (portfolioSelectedProjectIds.length === 0) {
      setPortfolioError("Select 1 to 3 projects for the showcase.");
      return;
    }

    setPortfolioGenerating(true);
    try {
      const generatePayload = {
        scan_id: Number(portfolioScanId),
        title: portfolioTitle.trim() || "Generated Portfolio",
        selected_project_ids: portfolioSelectedProjectIds,
        project_order: portfolioSelectedProjectIds,
      };
      const data = await fetchJson("/portfolio/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(generatePayload),
      });

      let artifact = data.portfolio;
      const editsToApply = {};
      for (const projectId of portfolioSelectedProjectIds) {
        if (projectEdits[projectId]) {
          editsToApply[projectId] = projectEdits[projectId];
        }
      }

      if (Object.keys(editsToApply).length > 0 && portfolioViewMode === "private") {
        const edited = await fetchJson(`/portfolio/${artifact.portfolio_id}/edit`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ project_edits: editsToApply }),
        });
        artifact = edited.portfolio;
      }
      setPortfolioArtifact(artifact);
    } catch (error) {
      setPortfolioError(error.message);
    } finally {
      setPortfolioGenerating(false);
    }
  };

  const handleExportPortfolio = async () => {
    if (!portfolioArtifact?.portfolio_id) return;
    setPortfolioExporting(true);
    setPortfolioError("");
    try {
      await downloadArtifact(`/portfolio/${portfolioArtifact.portfolio_id}/export`, "portfolio.md");
    } catch (error) {
      setPortfolioError(error.message);
    } finally {
      setPortfolioExporting(false);
    }
  };

  const visiblePortfolioItems = useMemo(() => {
    const items = portfolioArtifact?.data?.items || [];
    if (portfolioViewMode === "private" || !portfolioSearch.trim()) {
      return items;
    }
    const needle = portfolioSearch.trim().toLowerCase();
    return items.filter((item) => {
      const bag = [
        item.project_name,
        item.text,
        item.project_description,
        item.role_description,
        item.role,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return bag.includes(needle);
    });
  }, [portfolioArtifact, portfolioViewMode, portfolioSearch]);

  return (
    <div className="app-shell">
      <header className="masthead">
        <div className="masthead-title-wrap">
          <p className="eyebrow">Milestone 3 Workbench</p>
          <h1>Skill Scope Frontend</h1>
          <p className="subtitle">Build scans, resumes, and portfolio exports from one dashboard.</p>
        </div>
        <div className="status-card">
          <p className="status-label">API Status</p>
          <p className={`status-pill ${apiStatus}`}>{apiStatus}</p>
          <p className="status-message">{apiMessage || "Checking backend availability..."}</p>
          <button type="button" className="btn btn-ghost" onClick={loadScans} disabled={scansLoading}>
            {scansLoading ? "Refreshing..." : "Refresh Scans"}
          </button>
        </div>
      </header>

      <nav className="tab-row">
        <button
          type="button"
          className={`tab ${activeTab === "scan" ? "active" : ""}`}
          onClick={() => setActiveTab("scan")}
        >
          Scan Studio
        </button>
        <button
          type="button"
          className={`tab ${activeTab === "resume" ? "active" : ""}`}
          onClick={() => setActiveTab("resume")}
        >
          Resume Builder
        </button>
        <button
          type="button"
          className={`tab ${activeTab === "portfolio" ? "active" : ""}`}
          onClick={() => setActiveTab("portfolio")}
        >
          Portfolio Dashboard
        </button>
      </nav>

      <main className="content-grid">
        {activeTab === "scan" && (
          <section className="panel">
            <h2>Run New Scan</h2>
            <form className="grid-form" onSubmit={handleRunScan}>
              <label className="field">
                <span>Zip file</span>
                <input
                  type="file"
                  accept=".zip"
                  onChange={(event) => setScanZipFile(event.target.files?.[0] || null)}
                />
              </label>

              <div className="field">
                <span>Analysis mode</span>
                <div className="inline-options">
                  <label>
                    <input
                      type="radio"
                      value="basic"
                      checked={scanMode === "basic"}
                      onChange={() => setScanMode("basic")}
                    />
                    Basic
                  </label>
                  <label>
                    <input
                      type="radio"
                      value="advanced"
                      checked={scanMode === "advanced"}
                      onChange={() => setScanMode("advanced")}
                    />
                    Advanced
                  </label>
                </div>
              </div>

              {scanMode === "advanced" && (
                <div className="field">
                  <span>Advanced options</span>
                  <div className="inline-options wrap">
                    {Object.keys(advancedOptions).map((key) => (
                      <label key={key}>
                        <input
                          type="checkbox"
                          checked={advancedOptions[key]}
                          onChange={() => handleAdvancedOptionToggle(key)}
                        />
                        {key}
                      </label>
                    ))}
                  </div>
                </div>
              )}

              <div className="field">
                <span>Scan options</span>
                <div className="inline-options wrap">
                  <label>
                    <input
                      type="checkbox"
                      checked={scanConsent}
                      onChange={(event) => setScanConsent(event.target.checked)}
                    />
                    User consent
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={scanPersist}
                      onChange={(event) => setScanPersist(event.target.checked)}
                    />
                    Persist result
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={scanAllowDuplicate}
                      onChange={(event) => setScanAllowDuplicate(event.target.checked)}
                    />
                    Allow duplicate
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={scanIncremental}
                      onChange={(event) => setScanIncremental(event.target.checked)}
                    />
                    Incremental merge
                  </label>
                </div>
              </div>

              {scanIncremental && (
                <label className="field">
                  <span>Incremental target scan</span>
                  <select
                    value={scanIncrementalTarget}
                    onChange={(event) => setScanIncrementalTarget(event.target.value)}
                  >
                    <option value="">Select scan</option>
                    {scans.map((scan) => (
                      <option key={scan.summary_id} value={scan.summary_id}>
                        #{scan.summary_id} ({scan.analysis_mode}) {scan.timestamp}
                      </option>
                    ))}
                  </select>
                </label>
              )}

              <button type="submit" className="btn btn-primary" disabled={scanRunning}>
                {scanRunning ? "Scanning..." : "Run Scan"}
              </button>
            </form>

            {scanError && <p className="error-text">{scanError}</p>}

            {scanResult && (
              <div className="result-card">
                <h3>Scan Result</h3>
                <p>
                  Summary ID: <strong>{scanResult.summary_id ?? "not persisted"}</strong>
                </p>
                <p>
                  Flags: persisted={String(scanResult.persisted)}, duplicate={String(scanResult.duplicate)},
                  merged={String(scanResult.merged)}
                </p>
                <p>Projects detected: {(scanResult.projects || []).length}</p>
                <div className="tag-wrap">
                  {(scanResult.projects || []).map((project) => (
                    <span className="tag" key={project.project_id}>
                      {project.project_name}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className="result-card">
              <h3>Saved Scans</h3>
              {scans.length === 0 ? (
                <p>No saved scans yet.</p>
              ) : (
                <ul className="simple-list">
                  {scans.map((scan) => (
                    <li key={scan.summary_id}>
                      <button
                        type="button"
                        className={`inline-link ${selectedScanId === String(scan.summary_id) ? "active" : ""}`}
                        onClick={() => {
                          const sid = String(scan.summary_id);
                          setSelectedScanId(sid);
                          setResumeScanId(sid);
                          setPortfolioScanId(sid);
                        }}
                      >
                        #{scan.summary_id} | {scan.analysis_mode} | {scan.timestamp}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>
        )}

        {activeTab === "resume" && (
          <section className="panel">
            <h2>Resume Builder</h2>
            <div className="grid-form">
              <label className="field">
                <span>Source scan</span>
                <select value={resumeScanId} onChange={(event) => setResumeScanId(event.target.value)}>
                  <option value="">Select scan</option>
                  {scans.map((scan) => (
                    <option key={scan.summary_id} value={scan.summary_id}>
                      #{scan.summary_id} ({scan.analysis_mode}) {scan.timestamp}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field">
                <span>Resume title</span>
                <input value={resumeTitle} onChange={(event) => setResumeTitle(event.target.value)} />
              </label>

              <div className="field">
                <span>Projects for this resume</span>
                {resumeLoadingProjects ? (
                  <p>Loading projects...</p>
                ) : resumeProjects.length === 0 ? (
                  <p>No projects for this scan.</p>
                ) : (
                  <ul className="project-list">
                    {resumeProjects.map((project) => (
                      <li key={project.project_id}>
                        <label>
                          <input
                            type="checkbox"
                            checked={resumeSelectedProjectIds.includes(project.project_id)}
                            onChange={() => toggleResumeProject(project.project_id)}
                          />
                          <span>
                            {project.project_name}
                            <small>
                              score: {project.score ?? "n/a"} | type: {project.project_type ?? "n/a"}
                            </small>
                          </span>
                        </label>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <button type="button" className="btn btn-primary" onClick={handleGenerateResume} disabled={resumeGenerating}>
                {resumeGenerating ? "Generating..." : "Generate Resume"}
              </button>

              {resumeError && <p className="error-text">{resumeError}</p>}

              {resumeArtifact && (
                <div className="result-card">
                  <h3>Resume Artifact #{resumeArtifact.resume_id}</h3>
                  <p>Selected projects: {(resumeArtifact.data?.selected_project_ids || []).length}</p>
                  <ul className="simple-list">
                    {(resumeArtifact.data?.items || []).map((item) => (
                      <li key={item.project_id}>
                        <strong>{item.project_name}</strong>
                        <p>{item.text}</p>
                      </li>
                    ))}
                  </ul>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={handleExportResume}
                    disabled={resumeExporting}
                  >
                    {resumeExporting ? "Exporting..." : "Export DOCX"}
                  </button>
                </div>
              )}
            </div>
          </section>
        )}

        {activeTab === "portfolio" && (
          <section className="panel">
            <h2>Portfolio Dashboard</h2>
            <div className="grid-form">
              <div className="field">
                <span>Dashboard mode</span>
                <div className="inline-options">
                  <label>
                    <input
                      type="radio"
                      checked={portfolioViewMode === "private"}
                      onChange={() => setPortfolioViewMode("private")}
                    />
                    Private (customize)
                  </label>
                  <label>
                    <input
                      type="radio"
                      checked={portfolioViewMode === "public"}
                      onChange={() => setPortfolioViewMode("public")}
                    />
                    Public (search/filter)
                  </label>
                </div>
              </div>

              <label className="field">
                <span>Source scan</span>
                <select value={portfolioScanId} onChange={(event) => setPortfolioScanId(event.target.value)}>
                  <option value="">Select scan</option>
                  {scans.map((scan) => (
                    <option key={scan.summary_id} value={scan.summary_id}>
                      #{scan.summary_id} ({scan.analysis_mode}) {scan.timestamp}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field">
                <span>Portfolio title</span>
                <input value={portfolioTitle} onChange={(event) => setPortfolioTitle(event.target.value)} />
              </label>

              <div className="field">
                <span>Top 3 showcase projects</span>
                {portfolioLoadingProjects ? (
                  <p>Loading projects...</p>
                ) : portfolioProjects.length === 0 ? (
                  <p>No projects for this scan.</p>
                ) : (
                  <ul className="project-list">
                    {portfolioProjects.map((project) => (
                      <li key={project.project_id}>
                        <label>
                          <input
                            type="checkbox"
                            checked={portfolioSelectedProjectIds.includes(project.project_id)}
                            onChange={() => togglePortfolioProject(project.project_id)}
                          />
                          <span>
                            {project.project_name}
                            <small>score: {project.score ?? "n/a"}</small>
                          </span>
                        </label>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {portfolioViewMode === "private" &&
                portfolioSelectedProjectIds.map((projectId) => {
                  const project = portfolioProjects.find((p) => p.project_id === projectId);
                  const current = projectEdits[projectId] || {};
                  return (
                    <div className="result-card" key={projectId}>
                      <h3>{project?.project_name || projectId}</h3>
                      <label className="field">
                        <span>Role</span>
                        <input
                          value={current.role || ""}
                          onChange={(event) => updateProjectEdit(projectId, "role", event.target.value)}
                          placeholder="Lead Developer, Analyst, etc."
                        />
                      </label>
                      <label className="field">
                        <span>Evidence of success</span>
                        <input
                          value={current.evidence_of_success || ""}
                          onChange={(event) =>
                            updateProjectEdit(projectId, "evidence_of_success", event.target.value)
                          }
                          placeholder="Outcome or measurable impact"
                        />
                      </label>
                      <label className="field">
                        <span>Portfolio showcase text</span>
                        <textarea
                          value={current.portfolio_showcase_text || ""}
                          onChange={(event) =>
                            updateProjectEdit(projectId, "portfolio_showcase_text", event.target.value)
                          }
                          rows={3}
                          placeholder="Narrative to show in the portfolio card"
                        />
                      </label>
                    </div>
                  );
                })}

              {portfolioViewMode === "public" && (
                <label className="field">
                  <span>Search portfolio content</span>
                  <input
                    value={portfolioSearch}
                    onChange={(event) => setPortfolioSearch(event.target.value)}
                    placeholder="Filter generated portfolio cards"
                  />
                </label>
              )}

              <button
                type="button"
                className="btn btn-primary"
                onClick={handleGeneratePortfolio}
                disabled={portfolioGenerating}
              >
                {portfolioGenerating ? "Generating..." : "Generate Portfolio"}
              </button>

              {portfolioError && <p className="error-text">{portfolioError}</p>}

              {portfolioArtifact && (
                <div className="result-card">
                  <h3>Portfolio Artifact #{portfolioArtifact.portfolio_id}</h3>
                  <p>Showcase items: {visiblePortfolioItems.length}</p>
                  <div className="portfolio-cards">
                    {visiblePortfolioItems.map((item) => (
                      <article className="portfolio-card" key={item.project_id}>
                        <h4>{item.project_name}</h4>
                        <p>{item.project_description || item.text}</p>
                        {item.role_description && <p className="muted">Role: {item.role_description}</p>}
                        {item.tech_stack?.length > 0 && (
                          <p className="muted">Tech: {item.tech_stack.join(", ")}</p>
                        )}
                        {item.contribution_display && <p className="muted">{item.contribution_display}</p>}
                      </article>
                    ))}
                  </div>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={handleExportPortfolio}
                    disabled={portfolioExporting}
                  >
                    {portfolioExporting ? "Exporting..." : "Export Markdown"}
                  </button>
                </div>
              )}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
