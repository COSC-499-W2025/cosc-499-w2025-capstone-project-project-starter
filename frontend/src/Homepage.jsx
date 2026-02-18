import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { API_BASE_URL, authApi, projectApi } from './api';

const TOKEN_STORAGE_KEY = 'artifactMiner.authToken';

function normalizeProjectName(filename) {
  return filename.replace(/\.zip$/i, '');
}

function formatDate(value) {
  if (!value) return 'N/A';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return 'N/A';
  return parsed.toLocaleDateString();
}

function Homepage() {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_STORAGE_KEY) || '');
  const [currentUser, setCurrentUser] = useState(null);
  const [sessionLoading, setSessionLoading] = useState(true);
  const [authMode, setAuthMode] = useState('login');
  const [authBusy, setAuthBusy] = useState(false);
  const [authError, setAuthError] = useState('');

  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  const [registerDisplayName, setRegisterDisplayName] = useState('');
  const [registerEmail, setRegisterEmail] = useState('');
  const [registerPassword, setRegisterPassword] = useState('');
  const [registerConfirmPassword, setRegisterConfirmPassword] = useState('');

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

  const isAuthenticated = Boolean(token && currentUser);

  const clearDashboardState = useCallback(() => {
    setPortfolioId(null);
    setProjects([]);
    setTopProjects([]);
    setChronologicalSkills([]);
    setSelectedProject(null);
    setProjectReport(null);
    setProjectSkills(null);
    setContributors([]);
    setFile(null);
    setUploadProjectName('');
    setView('projects');
  }, []);

  const clearSession = useCallback(() => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken('');
    setCurrentUser(null);
    setDashboardError('');
    setFlashMessage('');
    clearDashboardState();
  }, [clearDashboardState]);

  useEffect(() => {
    let cancelled = false;
    const bootstrapSession = async () => {
      if (!token) {
        setSessionLoading(false);
        return;
      }
      try {
        const me = await authApi.me(token);
        if (!cancelled) {
          setCurrentUser(me.user || null);
        }
      } catch (error) {
        if (!cancelled) {
          clearSession();
          setAuthError('Your session expired. Please sign in again.');
        }
      } finally {
        if (!cancelled) {
          setSessionLoading(false);
        }
      }
    };
    bootstrapSession();
    return () => {
      cancelled = true;
    };
  }, [token, clearSession]);

  const fetchProjects = useCallback(async () => {
    if (!token) return;
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
  }, [token]);

  const fetchTopProjects = useCallback(async () => {
    if (!token || !portfolioId) return;
    setLoading(true);
    setDashboardError('');
    try {
      const data = await projectApi.getPortfolioTopProjects(token, portfolioId, 5);
      setTopProjects(data.top_projects || []);
    } catch (error) {
      setDashboardError(error.message || 'Unable to load top projects.');
    } finally {
      setLoading(false);
    }
  }, [token, portfolioId]);

  const fetchChronologicalSkills = useCallback(async () => {
    if (!token || !portfolioId) return;
    setLoading(true);
    setDashboardError('');
    try {
      const data = await projectApi.getPortfolioSkillTimeline(token, portfolioId, 50);
      setChronologicalSkills(data.skill_events || []);
    } catch (error) {
      setDashboardError(error.message || 'Unable to load skills timeline.');
    } finally {
      setLoading(false);
    }
  }, [token, portfolioId]);

  useEffect(() => {
    if (!isAuthenticated) return;
    fetchProjects();
  }, [isAuthenticated, fetchProjects]);

  useEffect(() => {
    if (!isAuthenticated) return;
    if (view === 'top') fetchTopProjects();
    if (view === 'skills') fetchChronologicalSkills();
  }, [view, isAuthenticated, fetchTopProjects, fetchChronologicalSkills]);

  const handleAuthSuccess = useCallback(
    (response) => {
      localStorage.setItem(TOKEN_STORAGE_KEY, response.token);
      setToken(response.token);
      setCurrentUser(response.user || null);
      setAuthError('');
      setFlashMessage('Signed in successfully.');
      clearDashboardState();
    },
    [clearDashboardState]
  );

  const handleLogin = async (event) => {
    event.preventDefault();
    setAuthBusy(true);
    setAuthError('');
    try {
      const response = await authApi.login({
        email: loginEmail,
        password: loginPassword,
      });
      handleAuthSuccess(response);
      setLoginPassword('');
    } catch (error) {
      setAuthError(error.message || 'Login failed.');
    } finally {
      setAuthBusy(false);
    }
  };

  const handleRegister = async (event) => {
    event.preventDefault();
    setAuthBusy(true);
    setAuthError('');
    if (registerPassword !== registerConfirmPassword) {
      setAuthBusy(false);
      setAuthError('Passwords do not match.');
      return;
    }
    try {
      const response = await authApi.register({
        email: registerEmail,
        password: registerPassword,
        displayName: registerDisplayName,
      });
      handleAuthSuccess(response);
      setRegisterPassword('');
      setRegisterConfirmPassword('');
    } catch (error) {
      setAuthError(error.message || 'Registration failed.');
    } finally {
      setAuthBusy(false);
    }
  };

  const handleLogout = async () => {
    if (!token) return;
    try {
      await authApi.logout(token);
    } catch (error) {
      // Ignore logout API failures and clear local session anyway.
    } finally {
      clearSession();
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setDashboardError('');
    setFlashMessage('');
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
    if (!token) return;
    setSelectedProject(project);
    setView('report');
    setProjectReport(null);
    setProjectSkills(null);
    setContributors([]);
    setLoading(true);
    setDashboardError('');
    try {
      const [reportResponse, contributorsResponse] = await Promise.all([
        projectApi.getProjectReport(token, project.id),
        projectApi.getProjectContributors(token, project.id),
      ]);
      setProjectReport(reportResponse);
      setContributors(contributorsResponse.contributors || []);

      const snapshotId = project.latest_snapshot?.id;
      if (snapshotId) {
        const skillsResponse = await projectApi.getSnapshotSkills(token, snapshotId, 20);
        setProjectSkills(skillsResponse);
      }
    } catch (error) {
      setDashboardError(error.message || 'Unable to load project details.');
    } finally {
      setLoading(false);
    }
  };

  const generateResume = async (projectId) => {
    if (!token) return;
    setLoading(true);
    setDashboardError('');
    try {
      const response = await projectApi.generateResume(token, projectId);
      setFlashMessage(`Resume generated: ${response.resume_id}`);
      window.open(`${API_BASE_URL}/resume/${response.resume_id}/pdf`, '_blank', 'noopener,noreferrer');
    } catch (error) {
      setDashboardError(error.message || 'Resume generation failed.');
    } finally {
      setLoading(false);
    }
  };

  const navButtons = useMemo(
    () => [
      { id: 'projects', label: 'Projects' },
      { id: 'upload', label: 'Upload' },
      { id: 'skills', label: 'Skills Timeline' },
      { id: 'top', label: 'Top Projects' },
    ],
    []
  );

  const reportStats = useMemo(() => {
    if (!projectReport) {
      return {
        totalFiles: 0,
        totalLines: 0,
        languageCount: 0,
        topLanguages: [],
      };
    }

    const snapshots = Array.isArray(projectReport.snapshots) ? projectReport.snapshots : [];
    const latestSnapshot = snapshots[snapshots.length - 1] || null;
    const parser = latestSnapshot?.analyses?.parser || {};
    const parserTotals = parser?.totals || {};
    const summary = projectReport.summary || {};

    const totalFiles =
      summary.total_files ??
      summary.files ??
      parserTotals.total_files ??
      parserTotals.files ??
      0;

    const totalLines =
      summary.total_lines ??
      summary.lines ??
      parserTotals.total_lines ??
      parserTotals.lines ??
      0;

    const inferredLanguageCount =
      summary.language_count ??
      summary.languages ??
      summary.total_languages ??
      parserTotals.language_count ??
      (parser?.language_counts ? Object.keys(parser.language_counts).length : undefined) ??
      0;

    const topLanguages =
      (Array.isArray(projectReport.top_languages) && projectReport.top_languages) ||
      (Array.isArray(parser?.top_languages) && parser.top_languages) ||
      [];

    return {
      totalFiles: Number(totalFiles) || 0,
      totalLines: Number(totalLines) || 0,
      languageCount: Number(inferredLanguageCount) || 0,
      topLanguages,
    };
  }, [projectReport]);

  if (sessionLoading) {
    return (
      <div className="screen-shell">
        <div className="loading-card">Restoring your session...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="screen-shell">
        <div className="auth-layout">
          <section className="auth-hero">
            <p className="eyebrow">Artifact Miner</p>
            <h1>Project portfolio intelligence built around real ownership.</h1>
            <p>
              Sign in to manage your own project snapshots, timelines, and generated resume artifacts without relying on
              hardcoded test identities.
            </p>
          </section>
          <section className="auth-panel">
            <div className="auth-toggle">
              <button
                className={authMode === 'login' ? 'tab active' : 'tab'}
                type="button"
                onClick={() => setAuthMode('login')}
              >
                Log In
              </button>
              <button
                className={authMode === 'register' ? 'tab active' : 'tab'}
                type="button"
                onClick={() => setAuthMode('register')}
              >
                Create Account
              </button>
            </div>

            {authMode === 'login' ? (
              <form className="auth-form" onSubmit={handleLogin}>
                <label>
                  Email
                  <input
                    type="email"
                    value={loginEmail}
                    onChange={(e) => setLoginEmail(e.target.value)}
                    required
                  />
                </label>
                <label>
                  Password
                  <input
                    type="password"
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    required
                  />
                </label>
                <button className="primary-btn" type="submit" disabled={authBusy}>
                  {authBusy ? 'Signing in...' : 'Sign In'}
                </button>
              </form>
            ) : (
              <form className="auth-form" onSubmit={handleRegister}>
                <label>
                  Display Name (optional)
                  <input
                    type="text"
                    value={registerDisplayName}
                    onChange={(e) => setRegisterDisplayName(e.target.value)}
                  />
                </label>
                <label>
                  Email
                  <input
                    type="email"
                    value={registerEmail}
                    onChange={(e) => setRegisterEmail(e.target.value)}
                    required
                  />
                </label>
                <label>
                  Password
                  <input
                    type="password"
                    value={registerPassword}
                    onChange={(e) => setRegisterPassword(e.target.value)}
                    minLength={8}
                    required
                  />
                </label>
                <label>
                  Confirm Password
                  <input
                    type="password"
                    value={registerConfirmPassword}
                    onChange={(e) => setRegisterConfirmPassword(e.target.value)}
                    minLength={8}
                    required
                  />
                </label>
                <button className="primary-btn" type="submit" disabled={authBusy}>
                  {authBusy ? 'Creating account...' : 'Create Account'}
                </button>
              </form>
            )}

            {authError && <p className="error-banner">{authError}</p>}
          </section>
        </div>
      </div>
    );
  }

  return (
    <div className="screen-shell">
      <div className="dashboard-shell">
        <header className="dashboard-header">
          <div>
            <p className="eyebrow">Signed in as</p>
            <h1>{currentUser.display_name || currentUser.email}</h1>
          </div>
          <button className="ghost-btn" type="button" onClick={handleLogout}>
            Log Out
          </button>
        </header>

        <nav className="dashboard-nav">
          {navButtons.map((item) => (
            <button
              key={item.id}
              type="button"
              className={view === item.id ? 'nav-btn active' : 'nav-btn'}
              onClick={() => setView(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>

        {flashMessage && <p className="success-banner">{flashMessage}</p>}
        {dashboardError && <p className="error-banner">{dashboardError}</p>}

        <main className="dashboard-main">
          {view === 'projects' && (
            <section className="panel">
              <h2>Your Projects</h2>
              {loading ? (
                <p>Loading projects...</p>
              ) : projects.length === 0 ? (
                <p>No projects yet. Upload a ZIP to begin.</p>
              ) : (
                <div className="project-grid">
                  {projects.map((project) => (
                    <article key={project.id} className="project-card">
                      <h3>{project.name}</h3>
                      <p>Type: {project.project_type || 'Unknown'}</p>
                      <p>Commits: {project.metrics?.total_commits || 0}</p>
                      <p>Your commits: {project.metrics?.user_commits || 0}</p>
                      <p>Contributors: {project.metrics?.contributor_count || 0}</p>
                      {project.metrics?.rank_score != null && (
                        <p className="rank-pill">Rank score {project.metrics.rank_score.toFixed(2)}</p>
                      )}
                      <div className="card-actions">
                        <button className="primary-btn" type="button" onClick={() => viewProjectDetails(project)}>
                          View Details
                        </button>
                        <button className="secondary-btn" type="button" onClick={() => generateResume(project.id)}>
                          Generate Resume
                        </button>
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
              <label className="field">
                Project name override (optional)
                <input
                  type="text"
                  value={uploadProjectName}
                  placeholder="Defaults to filename"
                  onChange={(e) => setUploadProjectName(e.target.value)}
                />
              </label>
              <label className="field">
                ZIP file
                <input
                  type="file"
                  accept=".zip"
                  onChange={(e) => {
                    const selected = e.target.files?.[0] || null;
                    setFile(selected);
                    if (selected && !uploadProjectName.trim()) {
                      setUploadProjectName(normalizeProjectName(selected.name));
                    }
                  }}
                />
              </label>
              {file && <p className="muted">Selected file: {file.name}</p>}
              <button className="primary-btn" type="button" disabled={!file || uploading} onClick={handleUpload}>
                {uploading ? 'Uploading...' : 'Upload Project'}
              </button>
            </section>
          )}

          {view === 'report' && selectedProject && (
            <section className="panel">
              <div className="panel-title-row">
                <button className="ghost-btn" type="button" onClick={() => setView('projects')}>
                  Back to Projects
                </button>
                <h2>{selectedProject.name}</h2>
              </div>
              {loading ? (
                <p>Loading project details...</p>
              ) : (
                <>
                  {projectReport && (
                    <div className="stack-block">
                      <h3>Summary</h3>
                      <div className="summary-grid">
                        <p>Total files: {reportStats.totalFiles}</p>
                        <p>Total lines: {reportStats.totalLines}</p>
                        <p>Languages: {reportStats.languageCount}</p>
                      </div>
                      {reportStats.topLanguages.length > 0 && (
                        <>
                          <h4>Top languages</h4>
                          <ul className="simple-list">
                            {reportStats.topLanguages.map((language, index) => (
                              <li key={`${language.language || language.name || 'unknown'}-${index}`}>
                                <span>{language.language || language.name || 'Unknown'}</span>
                                <span>
                                  {typeof language.percentage === 'number'
                                    ? `${language.percentage.toFixed(1)}%`
                                    : `${Number(language.files || 0)} files`}
                                </span>
                              </li>
                            ))}
                          </ul>
                        </>
                      )}
                    </div>
                  )}

                  {projectSkills?.skills?.length > 0 && (
                    <div className="stack-block">
                      <h3>Detected Skills</h3>
                      <div className="badge-row">
                        {projectSkills.skills.map((skill, index) => (
                          <span key={`${skill.skill_name}-${index}`} className="skill-badge">
                            {skill.skill_name}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {contributors.length > 0 && (
                    <div className="stack-block">
                      <h3>Contributors</h3>
                      <div className="table-wrap">
                        <table>
                          <thead>
                            <tr>
                              <th>Name</th>
                              <th>Email</th>
                              <th>Commits</th>
                              <th>Marked as You</th>
                            </tr>
                          </thead>
                          <tbody>
                            {contributors.map((contributor) => (
                              <tr key={contributor.contributor_id}>
                                <td>{contributor.canonical_name}</td>
                                <td>{contributor.email || '-'}</td>
                                <td>{contributor.commits}</td>
                                <td>{contributor.is_user ? 'Yes' : 'No'}</td>
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
              {loading ? (
                <p>Loading top projects...</p>
              ) : topProjects.length === 0 ? (
                <p>No ranked projects yet.</p>
              ) : (
                <div className="top-list">
                  {topProjects.map((project, index) => (
                    <article key={project.project_id} className="top-card">
                      <p className="top-rank">#{index + 1}</p>
                      <div>
                        <h3>{project.name}</h3>
                        <p>Score: {project.rank_score?.toFixed(2) || 'N/A'}</p>
                        <p>Your commits: {project.features?.user_commits || 0}</p>
                        <p>Total commits: {project.features?.total_commits || 0}</p>
                        {project.summary?.top_languages && <p>Languages: {project.summary.top_languages}</p>}
                        {project.summary?.top_skills && <p>Skills: {project.summary.top_skills}</p>}
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
              {loading ? (
                <p>Loading skills timeline...</p>
              ) : chronologicalSkills.length === 0 ? (
                <p>No skill events available yet.</p>
              ) : (
                <div className="timeline">
                  {chronologicalSkills.map((event, index) => (
                    <article key={`${event.skill}-${event.snapshot_id}-${index}`} className="timeline-item">
                      <p className="timeline-date">{formatDate(event.first_seen_ts)}</p>
                      <div>
                        <h3>{event.skill}</h3>
                        <p className="muted">Project: {event.project_name}</p>
                        {event.max_prob != null && <p>Confidence: {(event.max_prob * 100).toFixed(0)}%</p>}
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>
          )}
        </main>
      </div>
    </div>
  );
}

export default Homepage;
