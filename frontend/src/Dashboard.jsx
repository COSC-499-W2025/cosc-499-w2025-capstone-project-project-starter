import React, { useState, useEffect, useCallback } from 'react';
import './Dashboard.css';

const dashHelpers = {
  normalizeName: (filename) => filename.replace(/\.zip$/i, ''),
  formatDate: (value) => {
    if (!value) return 'N/A';
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? 'N/A' : parsed.toLocaleDateString();
  }
};
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
  const [contributors, setContributors] = useState([]);
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
        projectName: uploadProjectName.trim() || dashHelpers.normalizeName(file.name),
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
      setView('report');
    } catch (error) {
      setDashboardError('Unable to load project details.');
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
          <p className="eyebrow" style={{ fontSize: '0.8rem', color: '#64748b', margin: 0, textTransform: 'uppercase' }}>Signed in as</p>
          <h1 style={{ margin: 0 }}>{currentUser?.display_name || currentUser?.email || 'User'}</h1>
        </div>
        <button className="nav-btn" style={{ borderColor: '#fee2e2', color: '#ef4444' }} onClick={onLogout}>Log Out</button>
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

      <main className="dashboard-main">
        {flashMessage && <div className="panel" style={{ color: '#166534', backgroundColor: '#dcfce7', marginBottom: '1rem' }}>{flashMessage}</div>}
        {dashboardError && <div className="panel" style={{ color: '#991b1b', backgroundColor: '#fee2e2', marginBottom: '1rem' }}>{dashboardError}</div>}

        {view === 'projects' && (
          <section className="panel">
            <h2 style={{ marginTop: 0 }}>Your Projects</h2>
            {loading ? <p>Loading projects...</p> : (
              <div className="project-grid">
                {projects.map((p) => (
                  <article key={p.id} className="project-card">
                    <div className="thumbnail-box">No thumbnail</div>
                    <h3>{p.name}</h3>
                    <p>Type: code</p>
                    <p>Added: {dashHelpers.formatDate(p.created_at)}</p>
                    <div className="analysis-pill">Analysis in progress</div>
                    <p style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '0.5rem' }}>
                      {p.metrics?.complete_count || 0}/3 complete <br />
                      Running: Git Metrics
                    </p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      <button className="btn-primary" onClick={() => viewProjectDetails(p)}>View Details</button>
                      <button className="btn-secondary" onClick={() => projectApi.generateResume(token, p.id)}>Generate Resume</button>
                      <button className="btn-secondary" style={{ border: 'none', color: '#94a3b8', fontSize: '0.8rem' }}>Delete Project</button>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        )}

        {view === 'upload' && (
          <section className="panel">
            <h2 style={{ marginTop: 0 }}>Upload Project ZIP</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', maxWidth: '400px' }}>
              <label style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontWeight: 'bold' }}>
                Project name override
                <input style={{ padding: '10px', borderRadius: '8px', border: '1px solid #ddd' }} type="text" value={uploadProjectName} onChange={(e) => setUploadProjectName(e.target.value)} />
              </label>
              <label style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontWeight: 'bold' }}>
                ZIP file
                <input type="file" accept=".zip" onChange={(e) => {
                  const selected = e.target.files?.[0] || null;
                  setFile(selected);
                  if (selected && !uploadProjectName) setUploadProjectName(dashHelpers.normalizeName(selected.name));
                }} />
              </label>
              <button className="btn-primary" disabled={!file || uploading} onClick={handleUpload}>
                {uploading ? 'Uploading...' : 'Upload Project'}
              </button>
            </div>
          </section>
        )}

        {view === 'report' && selectedProject && (
          <section className="panel">
            <button className="nav-btn" onClick={() => setView('projects')} style={{ marginBottom: '1rem' }}>← Back</button>
            <h2 style={{ marginTop: 0 }}>{selectedProject.name}</h2>
            {loading ? <p>Loading details...</p> : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                <div>
                  <h3 style={{ borderBottom: '1px solid #eee', paddingBottom: '0.5rem' }}>Summary</h3>
                  <p>Total Files: {projectReport?.summary?.total_files || 0}</p>
                  <p>Total Lines: {projectReport?.summary?.total_lines || 0}</p>
                </div>
                {projectSkills?.skills && (
                  <div>
                    <h3 style={{ borderBottom: '1px solid #eee', paddingBottom: '0.5rem' }}>Detected Skills</h3>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '1rem' }}>
                      {projectSkills.skills.map((s, i) => (
                        <span key={i} style={{ backgroundColor: '#eff6ff', color: '#1e40af', padding: '4px 12px', borderRadius: '999px', fontSize: '0.85rem', fontWeight: '600' }}>
                          {s.skill_name}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {contributors.length > 0 && (
                  <div>
                    <h3 style={{ borderBottom: '1px solid #eee', paddingBottom: '0.5rem' }}>Contributors</h3>
                    <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse', marginTop: '1rem' }}>
                      <thead>
                        <tr style={{ color: '#64748b', borderBottom: '1px solid #eee' }}>
                          <th style={{ padding: '8px 0' }}>Name</th>
                          <th>Commits</th>
                        </tr>
                      </thead>
                      <tbody>
                        {contributors.map((c, i) => (
                          <tr key={i} style={{ borderBottom: '1px solid #f9f9f9' }}>
                            <td style={{ padding: '8px 0' }}>{c.canonical_name}</td>
                            <td>{c.commits}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </section>
        )}

        {view === 'top' && (
          <section className="panel">
            <h2 style={{ marginTop: 0 }}>Top Ranked Projects</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {topProjects.map((p, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', padding: '1rem', border: '1px solid #eee', borderRadius: '12px' }}>
                  <span style={{ fontSize: '1.5rem', fontWeight: '800', color: '#2e6cf4' }}>#{i + 1}</span>
                  <div>
                    <h3 style={{ margin: 0 }}>{p.name}</h3>
                    <p style={{ margin: 0, color: '#64748b' }}>Score: {p.rank_score?.toFixed(2)}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {view === 'skills' && (
          <section className="panel">
            <h2 style={{ marginTop: 0 }}>Skills Timeline</h2>
            <div style={{ borderLeft: '2px solid #e2e8f0', marginLeft: '1rem', paddingLeft: '2rem' }}>
              {chronologicalSkills.map((event, i) => (
                <div key={i} style={{ marginBottom: '2rem', position: 'relative' }}>
                  <div style={{ position: 'absolute', left: '-2.45rem', top: '0.25rem', width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#2e6cf4', border: '4px solid white' }}></div>
                  <span style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 'bold' }}>{dashHelpers.formatDate(event.first_seen_ts)}</span>
                  <h4 style={{ margin: '0.25rem 0' }}>{event.skill}</h4>
                  <p style={{ margin: 0, fontSize: '0.85rem', color: '#64748b' }}>Project: {event.project_name}</p>
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