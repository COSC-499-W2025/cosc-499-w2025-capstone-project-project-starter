import React, { useState, useEffect, useCallback } from 'react';
import './Dashboard.css';

function normalizeProjectName(filename) {
  return filename.replace(/\.zip$/i, '');
}

function formatDate(value) {
  if (!value) return 'N/A';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return 'N/A';
  return parsed.toLocaleDateString();
}

function Dashboard({ token, currentUser, onLogout, projectApi }) {
  const [view, setView] = useState('projects');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [dashboardError, setDashboardError] = useState('');
  const [flashMessage, setFlashMessage] = useState('');

  const [portfolioId, setPortfolioId] = useState(null);
  const [projects, setProjects] = useState([]);
  const [topProjects, setTopProjects] = useState([]);
  const [chronologicalSkills, setChronologicalSkills] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [projectReport, setProjectReport] = useState(null);
  const [projectSkills, setProjectSkills] = useState(null);
  const [contributors, setContributors] = useState([]); // Now fully utilized!
  const [file, setFile] = useState(null);
  const [uploadProjectName, setUploadProjectName] = useState('');

  const fetchProjects = useCallback(async () => {
    setLoading(true);
    setDashboardError('');
    try {
      const data = await projectApi.listProjects(token);
      setProjects(data.projects || []);
      setPortfolioId(data.portfolio_id || null);
    } catch (error) {
      setDashboardError(error.message || 'Unable to load projects.');
    } finally {
      setLoading(false);
    }
  }, [token, projectApi]);

  const fetchTopProjects = useCallback(async () => {
    if (!portfolioId) return;
    setLoading(true);
    try {
      const data = await projectApi.getPortfolioTopProjects(token, portfolioId, 5);
      setTopProjects(data.top_projects || []);
    } catch (error) {
      setDashboardError('Unable to load top projects.');
    } finally {
      setLoading(false);
    }
  }, [token, portfolioId, projectApi]);

  const fetchChronologicalSkills = useCallback(async () => {
    if (!portfolioId) return;
    setLoading(true);
    try {
      const data = await projectApi.getPortfolioSkillTimeline(token, portfolioId, 50);
      setChronologicalSkills(data.skill_events || []);
    } catch (error) {
      setDashboardError('Unable to load skills timeline.');
    } finally {
      setLoading(false);
    }
  }, [token, portfolioId, projectApi]);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  useEffect(() => {
    if (view === 'top') fetchTopProjects();
    if (view === 'skills') fetchChronologicalSkills();
  }, [view, fetchTopProjects, fetchChronologicalSkills]);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setDashboardError('');
    try {
      await projectApi.uploadProject(token, {
        file,
        projectName: uploadProjectName.trim() || normalizeProjectName(file.name),
      });
      setFile(null);
      setUploadProjectName('');
      setFlashMessage('Project uploaded successfully.');
      await fetchProjects();
      setView('projects');
    } catch (error) {
      setDashboardError(error.message || 'Upload failed.');
    } finally {
      setUploading(false);
    }
  };

  const viewProjectDetails = async (project) => {
    setSelectedProject(project);
    setView('report');
    setLoading(true);
    try {
      const [report, conts] = await Promise.all([
        projectApi.getProjectReport(token, project.id),
        projectApi.getProjectContributors(token, project.id),
      ]);
      setProjectReport(report);
      setContributors(conts.contributors || []);

      if (project.latest_snapshot?.id) {
        const skills = await projectApi.getSnapshotSkills(token, project.latest_snapshot.id, 20);
        setProjectSkills(skills);
      }
    } catch (error) {
      setDashboardError('Unable to load project details.');
    } finally {
      setLoading(false);
    }
  };

  const generateResume = async (projectId) => {
    setLoading(true);
    try {
      const response = await projectApi.generateResume(token, projectId);
      setFlashMessage(`Resume generated! ID: ${response.resume_id}`);
      window.open(`http://localhost:5001/resume/${response.resume_id}/pdf`, '_blank');
    } catch (error) {
      setDashboardError('Resume generation failed.');
    } finally {
      setLoading(false);
    }
  };

  const navButtons = [
    { id: 'projects', label: 'Projects' },
    { id: 'upload', label: 'Upload' },
    { id: 'skills', label: 'Skills Timeline' },
    { id: 'top', label: 'Top Projects' },
  ];

  return (
    <div className="dashboard-shell">
      <header className="dashboard-header">
        <div>
          <p className="eyebrow">Signed in as</p>
          <h1>{currentUser?.display_name || currentUser?.email || 'User'}</h1>
        </div>
        <button className="ghost-btn" onClick={onLogout}>Log Out</button>
      </header>

      <nav className="dashboard-nav">
        {navButtons.map((btn) => (
          <button
            key={btn.id}
            className={view === btn.id ? 'nav-btn active' : 'nav-btn'}
            onClick={() => {
                setDashboardError('');
                setFlashMessage('');
                setView(btn.id);
            }}
          >
            {btn.label}
          </button>
        ))}
      </nav>

      {flashMessage && <p className="success-banner">{flashMessage}</p>}
      {dashboardError && <p className="error-banner">{dashboardError}</p>}

      <main className="dashboard-main">
        {view === 'projects' && (
          <section className="panel">
            <h2>Your Projects</h2>
            {loading ? <p>Loading projects...</p> : (
              <div className="project-grid">
                {projects.map((p) => (
                  <article key={p.id} className="project-card">
                    <h3>{p.name}</h3>
                    <div className="metrics-row">
                      <span>Commits: {p.metrics?.user_commits || 0}</span>
                      {p.metrics?.rank_score && <span className="rank-pill">Score: {p.metrics.rank_score.toFixed(1)}</span>}
                    </div>
                    <div className="card-actions">
                      <button className="primary-btn" onClick={() => viewProjectDetails(p)}>View Details</button>
                      <button className="secondary-btn" onClick={() => generateResume(p.id)}>Resume</button>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        )}

        {view === 'upload' && (
          <section className="panel">
            <h2>Upload Project ZIP</h2>
            <div className="upload-form">
                <label className="field">
                    Project name override
                    <input type="text" value={uploadProjectName} onChange={(e) => setUploadProjectName(e.target.value)} />
                </label>
                <label className="field">
                    ZIP file
                    <input type="file" accept=".zip" onChange={(e) => {
                        const selected = e.target.files?.[0] || null;
                        setFile(selected);
                        if (selected && !uploadProjectName) setUploadProjectName(normalizeProjectName(selected.name));
                    }} />
                </label>
                <button className="primary-btn" disabled={!file || uploading} onClick={handleUpload}>
                    {uploading ? 'Uploading...' : 'Upload Project'}
                </button>
            </div>
          </section>
        )}

        {view === 'report' && selectedProject && (
          <section className="panel detail-view">
            <button className="ghost-btn" onClick={() => setView('projects')}>← Back to Projects</button>
            <h2>{selectedProject.name}</h2>
            {loading ? <p>Loading details...</p> : (
              <>
                {projectReport && (
                  <div className="stack-block">
                    <h3>Summary</h3>
                    <div className="summary-grid">
                      <p>Total Files: {projectReport.summary?.total_files}</p>
                      <p>Total Lines: {projectReport.summary?.total_lines}</p>
                    </div>
                  </div>
                )}
                {projectSkills?.skills && (
                  <div className="stack-block">
                    <h3>Detected Skills</h3>
                    <div className="badge-row">
                      {projectSkills.skills.map((s, i) => <span key={i} className="skill-badge">{s.skill_name}</span>)}
                    </div>
                  </div>
                )}
                
                {/* RESTORED CONTRIBUTORS SECTION */}
                {contributors.length > 0 && (
                  <div className="stack-block">
                    <h3>Contributors</h3>
                    <div className="table-wrap">
                      <table className="data-table">
                        <thead>
                          <tr><th>Name</th><th>Commits</th><th>Is You</th></tr>
                        </thead>
                        <tbody>
                          {contributors.map((c, i) => (
                            <tr key={i}>
                              <td>{c.canonical_name}</td>
                              <td>{c.commits}</td>
                              <td>{c.is_user ? 'Yes' : 'No'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </>
            )}
          </section>
        )}

        {view === 'top' && (
          <section className="panel">
            <h2>Top Ranked Projects</h2>
            {loading ? <p>Calculating ranks...</p> : (
              <div className="top-list">
                {topProjects.map((project, index) => (
                  <article key={project.project_id} className="top-card">
                    <p className="top-rank">#{index + 1}</p>
                    <div>
                      <h3>{project.name}</h3>
                      <p>Rank Score: {project.rank_score?.toFixed(2) || 'N/A'}</p>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        )}

        {view === 'skills' && (
          <section className="panel">
            <h2>Skills Timeline</h2>
            <div className="timeline">
              {chronologicalSkills.map((event, i) => (
                <div key={i} className="timeline-item">
                  <span className="date">{formatDate(event.first_seen_ts)}</span>
                  <h4>{event.skill}</h4>
                  <p className="muted">Project: {event.project_name}</p>
                </div>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default Dashboard;