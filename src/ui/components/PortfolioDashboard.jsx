import React, { useState, useEffect, useMemo } from "react";

export default function PortfolioDashboard({ scans, selectedScanId, fetchJson, downloadArtifact, loadProjectsForScan, setActiveTab, formatTimestamp }) {
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

  useEffect(() => {
    if (selectedScanId) {
      setPortfolioScanId(selectedScanId);
    }
  }, [selectedScanId]);

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

  const togglePortfolioProject = (projectId) => {
    setPortfolioError("");
    setPortfolioSelectedProjectIds((prev) => {
      if (prev.includes(projectId)) return prev.filter((id) => id !== projectId);
      if (prev.length >= 3) {
        setPortfolioError("Portfolio showcase is limited to top 3 projects.");
        return prev;
      }
      return [...prev, projectId];
    });
  };

  const updateProjectEdit = (projectId, key, value) => {
    setProjectEdits((prev) => ({ ...prev, [projectId]: { ...prev[projectId], [key]: value } }));
  };

  const handleGeneratePortfolio = async () => {
    setPortfolioError("");
    setPortfolioArtifact(null);
    if (!portfolioScanId) return setPortfolioError("Select a scan first.");
    if (portfolioSelectedProjectIds.length === 0) return setPortfolioError("Select 1 to 3 projects for the showcase.");

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
        if (projectEdits[projectId]) editsToApply[projectId] = projectEdits[projectId];
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
    if (portfolioViewMode === "private" || !portfolioSearch.trim()) return items;
    const needle = portfolioSearch.trim().toLowerCase();
    return items.filter((item) => {
      const bag = [item.project_name, item.text, item.project_description, item.role_description, item.role].filter(Boolean).join(" ").toLowerCase();
      return bag.includes(needle);
    });
  }, [portfolioArtifact, portfolioViewMode, portfolioSearch]);

  return (
    <section className="panel">
      <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "1rem" }}>
        <button
          type="button"
          className="btn btn-secondary"
          style={{ padding: "0.25rem 0.5rem" }}
          onClick={() => setActiveTab("scan-manager")}
        >
          &larr; Back
        </button>
        <h2 style={{ margin: 0 }}>Portfolio Dashboard</h2>
      </div>

      <div className="grid-form">
        <div className="field">
          <span>Dashboard mode</span>
          <div className="inline-options">
            <label><input type="radio" checked={portfolioViewMode === "private"} onChange={() => setPortfolioViewMode("private")} /> Private (customize)</label>
            <label><input type="radio" checked={portfolioViewMode === "public"} onChange={() => setPortfolioViewMode("public")} /> Public (search/filter)</label>
          </div>
        </div>
        <label className="field">
          <span>Source scan</span>
          <select value={portfolioScanId} onChange={(e) => setPortfolioScanId(e.target.value)}>
            <option value="">Select scan</option>
            {scans.map((scan) => (<option key={scan.summary_id} value={scan.summary_id}>Scan {scan.summary_id} - {formatTimestamp(scan.timestamp)} ({scan.analysis_mode})</option>))}
          </select>
        </label>
        <label className="field"><span>Portfolio title</span><input value={portfolioTitle} onChange={(e) => setPortfolioTitle(e.target.value)} /></label>
        <div className="field">
          <span>Top 3 showcase projects</span>
          {portfolioLoadingProjects ? (<p>Loading projects...</p>) : portfolioProjects.length === 0 ? (<p>No projects for this scan.</p>) : (
            <ul className="project-list">{portfolioProjects.map((project) => (<li key={project.project_id}><label><input type="checkbox" checked={portfolioSelectedProjectIds.includes(project.project_id)} onChange={() => togglePortfolioProject(project.project_id)} /><span>{project.project_name} <small>score: {project.score ?? "n/a"}</small></span></label></li>))}</ul>
          )}
        </div>

        {portfolioViewMode === "private" && portfolioSelectedProjectIds.map((projectId) => {
          const project = portfolioProjects.find((p) => p.project_id === projectId);
          const current = projectEdits[projectId] || {};
          return (
            <div className="result-card" key={projectId}>
              <h3>{project?.project_name || projectId}</h3>
              <label className="field"><span>Role</span><input value={current.role || ""} onChange={(e) => updateProjectEdit(projectId, "role", e.target.value)} placeholder="Lead Developer, Analyst, etc." /></label>
              <label className="field"><span>Evidence of success</span><input value={current.evidence_of_success || ""} onChange={(e) => updateProjectEdit(projectId, "evidence_of_success", e.target.value)} placeholder="Outcome or measurable impact" /></label>
              <label className="field"><span>Portfolio showcase text</span><textarea value={current.portfolio_showcase_text || ""} onChange={(e) => updateProjectEdit(projectId, "portfolio_showcase_text", e.target.value)} rows={3} placeholder="Narrative to show in the portfolio card" /></label>
            </div>
          );
        })}
        {portfolioViewMode === "public" && (<label className="field"><span>Search portfolio content</span><input value={portfolioSearch} onChange={(e) => setPortfolioSearch(e.target.value)} placeholder="Filter generated portfolio cards" /></label>)}
        <button type="button" className="btn btn-primary" onClick={handleGeneratePortfolio} disabled={portfolioGenerating}>{portfolioGenerating ? "Generating..." : "Generate Portfolio"}</button>
        {portfolioError && <p className="error-text">{portfolioError}</p>}
        {portfolioArtifact && (
          <div className="result-card">
            <h3>Portfolio Artifact #{portfolioArtifact.portfolio_id}</h3>
            <p>Showcase items: {visiblePortfolioItems.length}</p>
            <div className="portfolio-cards">{visiblePortfolioItems.map((item) => (<article className="portfolio-card" key={item.project_id}><h4>{item.project_name}</h4><p>{item.project_description || item.text}</p>{item.role_description && <p className="muted">Role: {item.role_description}</p>}{item.tech_stack?.length > 0 && (<p className="muted">Tech: {Array.isArray(item.tech_stack) ? item.tech_stack.join(", ") : item.tech_stack}</p>)}{item.contribution_display && <p className="muted">{item.contribution_display}</p>}</article>))}</div>
            <button type="button" className="btn btn-secondary" onClick={handleExportPortfolio} disabled={portfolioExporting}>{portfolioExporting ? "Exporting..." : "Export Markdown"}</button>
          </div>
        )}
      </div>
    </section>
  );
}