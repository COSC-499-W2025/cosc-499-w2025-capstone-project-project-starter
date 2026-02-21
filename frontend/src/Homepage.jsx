import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { API_BASE_URL, authApi, projectApi } from './api';

const TOKEN_STORAGE_KEY = 'artifactMiner.authToken';
const ANALYSIS_POLL_INTERVAL_MS = 5000;
const ACTIVE_ANALYSIS_STATUSES = new Set(['pending', 'running']);
const ANALYSIS_TYPE_LABELS = {
  parser: 'Parser',
  git_metrics: 'Git Metrics',
  local_ml: 'Local ML',
  external_llm: 'Ollama',
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

function formatDateTime(value) {
  if (!value) return 'N/A';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return 'N/A';
  return parsed.toLocaleString();
}

function normalizeAnalysisStatus(status) {
  return typeof status === 'string' ? status.toLowerCase() : 'pending';
}

function normalizeMetricCount(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function summarizeSnapshotAnalyses(analyses) {
  const rows = Array.isArray(analyses) ? analyses : [];

  if (rows.length === 0) {
    return {
      badge: 'Analysis queued',
      detail: 'Waiting for workers to pick up this snapshot.',
      progress: null,
      isRunning: true,
    };
  }

  const normalized = rows.map((analysis) => ({
    analysisType: analysis?.analysis_type || 'unknown',
    status: normalizeAnalysisStatus(analysis?.status),
  }));

  const total = normalized.length;
  const completeCount = normalized.filter((entry) => entry.status === 'complete').length;
  const failed = normalized.filter((entry) => entry.status === 'failed');
  const active = normalized.filter((entry) => ACTIVE_ANALYSIS_STATUSES.has(entry.status));
  const external = normalized.find((entry) => entry.analysisType === 'external_llm');

  if (failed.length > 0) {
    const failedLabels = failed
      .map((entry) => ANALYSIS_TYPE_LABELS[entry.analysisType] || entry.analysisType)
      .join(', ');
    return {
      badge: external?.status === 'failed' ? 'Ollama analysis failed' : 'Analysis failed',
      detail: `Failed jobs: ${failedLabels}`,
      progress: `${completeCount}/${total} complete`,
      isRunning: false,
    };
  }

  if (external?.status === 'running') {
    return {
      badge: 'Ollama analysis running',
      detail: 'External model generation is in progress and may take some time.',
      progress: `${completeCount}/${total} complete`,
      isRunning: true,
    };
  }

  if (external?.status === 'pending') {
    return {
      badge: 'Ollama analysis queued',
      detail: 'Waiting for the external model worker to start.',
      progress: `${completeCount}/${total} complete`,
      isRunning: true,
    };
  }

  if (active.length > 0) {
    const runningLabels = active
      .map((entry) => ANALYSIS_TYPE_LABELS[entry.analysisType] || entry.analysisType)
      .join(', ');
    return {
      badge: 'Analysis in progress',
      detail: `Running: ${runningLabels}`,
      progress: `${completeCount}/${total} complete`,
      isRunning: true,
    };
  }

  return {
    badge: external ? 'Analysis complete (Ollama done)' : 'Analysis complete',
    detail: 'All queued analyses finished.',
    progress: `${completeCount}/${total} complete`,
    isRunning: false,
  };
}

function getSnapshotStatus(snapshotId, snapshotAnalyses) {
  if (!snapshotId) {
    return {
      badge: 'No snapshot yet',
      detail: 'Upload a ZIP to start analysis.',
      progress: null,
      isRunning: false,
    };
  }

  const entry = snapshotAnalyses[snapshotId];

  if (entry === undefined) {
    return {
      badge: 'Checking analysis status...',
      detail: 'Fetching worker progress.',
      progress: null,
      isRunning: true,
    };
  }

  if (entry === null) {
    return {
      badge: 'Analysis status unavailable',
      detail: 'Could not fetch analysis status right now.',
      progress: null,
      isRunning: false,
    };
  }

  return summarizeSnapshotAnalyses(entry);
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
  const [uploadMode, setUploadMode] = useState('new');
  const [uploadTargetProjectId, setUploadTargetProjectId] = useState('');
  const [snapshotLabel, setSnapshotLabel] = useState('');
  const [uploadTargetReport, setUploadTargetReport] = useState(null);
  const [uploadHistoryLoading, setUploadHistoryLoading] = useState(false);
  const [uploadHistoryError, setUploadHistoryError] = useState('');
  const [deletingProjectId, setDeletingProjectId] = useState(null);
  const [snapshotAnalyses, setSnapshotAnalyses] = useState({});

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
    setUploadMode('new');
    setUploadTargetProjectId('');
    setSnapshotLabel('');
    setUploadTargetReport(null);
    setUploadHistoryLoading(false);
    setUploadHistoryError('');
    setSnapshotAnalyses({});
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

  const fetchUploadProjectHistory = useCallback(
    async (projectId) => {
      if (!token || !projectId) return null;
      return projectApi.getProjectReport(token, projectId);
    },
    [token]
  );

  useEffect(() => {
    if (!isAuthenticated) return;
    fetchProjects();
  }, [isAuthenticated, fetchProjects]);

  useEffect(() => {
    if (!isAuthenticated) return;
    if (view === 'top') fetchTopProjects();
    if (view === 'skills') fetchChronologicalSkills();
  }, [view, isAuthenticated, fetchTopProjects, fetchChronologicalSkills]);

  useEffect(() => {
    if (uploadMode !== 'incremental') return;
    if (projects.length === 0) {
      setUploadTargetProjectId('');
      return;
    }
    if (!projects.some((project) => project.id === uploadTargetProjectId)) {
      setUploadTargetProjectId(projects[0].id);
    }
  }, [uploadMode, projects, uploadTargetProjectId]);

  useEffect(() => {
    if (!token || view !== 'upload' || uploadMode !== 'incremental') {
      setUploadHistoryLoading(false);
      setUploadHistoryError('');
      if (uploadMode !== 'incremental') {
        setUploadTargetReport(null);
      }
      return;
    }
    if (!uploadTargetProjectId) {
      setUploadTargetReport(null);
      setUploadHistoryLoading(false);
      return;
    }

    let cancelled = false;

    const loadUploadHistory = async () => {
      setUploadHistoryLoading(true);
      setUploadHistoryError('');
      try {
        const report = await fetchUploadProjectHistory(uploadTargetProjectId);
        if (!cancelled) {
          setUploadTargetReport(report);
        }
      } catch (error) {
        if (!cancelled) {
          setUploadTargetReport(null);
          setUploadHistoryError(error.message || 'Unable to load snapshot history.');
        }
      } finally {
        if (!cancelled) {
          setUploadHistoryLoading(false);
        }
      }
    };

    loadUploadHistory();

    return () => {
      cancelled = true;
    };
  }, [token, view, uploadMode, uploadTargetProjectId, fetchUploadProjectHistory]);

  useEffect(() => {
    if (!token) {
      setSnapshotAnalyses({});
      return;
    }

    const snapshotIds = projects
      .map((project) => project.latest_snapshot?.id)
      .filter((snapshotId) => Boolean(snapshotId));

    if (snapshotIds.length === 0) {
      setSnapshotAnalyses({});
      return;
    }

    let cancelled = false;
    let timerId = null;

    const refreshAnalyses = async () => {
      const results = await Promise.allSettled(
        snapshotIds.map((snapshotId) => projectApi.getSnapshotAnalyses(token, snapshotId))
      );

      if (cancelled) return;

      let hasRunningAnalysis = false;
      const next = {};

      snapshotIds.forEach((snapshotId, index) => {
        const result = results[index];
        if (result.status === 'fulfilled') {
          const analyses = Array.isArray(result.value?.analyses) ? result.value.analyses : [];
          next[snapshotId] = analyses;
          if (analyses.some((entry) => ACTIVE_ANALYSIS_STATUSES.has(normalizeAnalysisStatus(entry?.status)))) {
            hasRunningAnalysis = true;
          }
        } else {
          next[snapshotId] = null;
        }
      });

      setSnapshotAnalyses(next);

      if (hasRunningAnalysis && !cancelled) {
        timerId = window.setTimeout(refreshAnalyses, ANALYSIS_POLL_INTERVAL_MS);
      }
    };

    refreshAnalyses();

    return () => {
      cancelled = true;
      if (timerId) {
        window.clearTimeout(timerId);
      }
    };
  }, [token, projects]);

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
    if (uploadMode === 'incremental' && !uploadTargetProjectId) {
      setDashboardError('Select an existing project for incremental upload.');
      return;
    }

    const selectedUploadProject = projects.find((project) => project.id === uploadTargetProjectId) || null;
    const normalizedUploadName = uploadProjectName.trim() || normalizeProjectName(file.name);
    const targetProjectName = uploadMode === 'incremental' ? selectedUploadProject?.name || '' : normalizedUploadName;

    if (!targetProjectName) {
      setDashboardError('Provide a project name before uploading.');
      return;
    }

    if (uploadMode === 'new') {
      const duplicateProject = projects.find(
        (project) => (project.name || '').trim().toLowerCase() === targetProjectName.trim().toLowerCase()
      );
      if (duplicateProject) {
        setDashboardError(
          `Project "${duplicateProject.name}" already exists. Switch to Incremental update to add another snapshot.`
        );
        return;
      }
    }

    setUploading(true);
    setDashboardError('');
    setFlashMessage('');
    try {
      const consentAccepted = window.confirm(
        'Privacy notice: external analysis sends project data to an external language model service. Click OK to consent (uses both local and external analysis), or Cancel to continue with local-only analysis.'
      );

      await authApi.submitPrivacyConsent(token, {
        userId: currentUser?.user_id,
        consentType: 'external_services',
        granted: consentAccepted,
      });

      const uploadResponse = await projectApi.uploadProject(token, {
        file,
        projectName: targetProjectName,
        snapshotLabel: snapshotLabel.trim() || undefined,
        analysisMode: consentAccepted ? 'both' : 'local',
      });
      setFile(null);
      if (uploadMode === 'new') {
        setUploadProjectName('');
      }
      setSnapshotLabel('');
      await fetchProjects();

      const createdCount = Array.isArray(uploadResponse?.created) ? uploadResponse.created.length : 0;
      const skippedCount = Array.isArray(uploadResponse?.skipped) ? uploadResponse.skipped.length : 0;

      if (uploadMode === 'incremental') {
        let refreshedReport = null;
        try {
          refreshedReport = await fetchUploadProjectHistory(uploadTargetProjectId);
          setUploadTargetReport(refreshedReport);
          setUploadHistoryError('');
        } catch (historyError) {
          setUploadHistoryError(historyError.message || 'Unable to refresh snapshot history.');
        }

        const snapshotTotal = Array.isArray(refreshedReport?.snapshots) ? refreshedReport.snapshots.length : null;
        if (createdCount > 0) {
          const snapshotSuffix =
            snapshotTotal == null ? '' : ` ${snapshotTotal} snapshot${snapshotTotal === 1 ? '' : 's'} now recorded.`;
          setFlashMessage(
            `Incremental upload complete for "${targetProjectName}". Files were merged into the existing project.${snapshotSuffix}`
          );
        } else if (skippedCount > 0) {
          setFlashMessage(
            `No new snapshot was created for "${targetProjectName}" because this ZIP already exists in that project's history.`
          );
        } else {
          setFlashMessage(`Upload finished for "${targetProjectName}".`);
        }
        setView('upload');
      } else {
        setFlashMessage('Project uploaded. Analysis has started and status will update in Your Projects.');
        setView('projects');
      }
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

  const deleteProject = async (project) => {
    if (!token) return;

    const confirmed = window.confirm(
      `Delete project "${project.name}"? This will permanently remove it from your account.`
    );
    if (!confirmed) return;

    setDeletingProjectId(project.id);
    setDashboardError('');
    setFlashMessage('');

    try {
      await projectApi.deleteProject(token, project.id);
      setFlashMessage('Project deleted successfully.');
      await fetchProjects();
    } catch (error) {
      setDashboardError(error.message || 'Project deletion failed.');
    } finally {
      setDeletingProjectId(null);
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
    const toNumber = (value) => {
      if (value === null || value === undefined) return null;
      if (typeof value === 'number' && Number.isFinite(value)) return value;
      if (typeof value === 'string') {
        const normalized = value.replace(/[^0-9.-]/g, '');
        if (!normalized) return null;
        const parsed = Number(normalized);
        return Number.isFinite(parsed) ? parsed : null;
      }
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : null;
    };

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

    const totalFilesRaw =
      summary.total_files ??
      summary.files ??
      parserTotals.total_files ??
      parserTotals.files ??
      0;

    const totalLinesRaw =
      summary.total_lines ??
      summary.totalLines ??
      summary.lines ??
      summary.line_count ??
      summary.lineCount ??
      summary.loc ??
      summary.sloc ??
      parserTotals.total_lines ??
      parserTotals.totalLines ??
      parserTotals.lines ??
      parserTotals.line_count ??
      parserTotals.lineCount ??
      parserTotals.loc ??
      parserTotals.sloc ??
      0;

    const inferredLanguageCountRaw =
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
      totalFiles: toNumber(totalFilesRaw) ?? 0,
      totalLines: toNumber(totalLinesRaw) ?? 0,
      languageCount: toNumber(inferredLanguageCountRaw) ?? 0,
      topLanguages,
    };
  }, [projectReport]);

  const selectedProjectStatus = useMemo(() => {
    if (!selectedProject) return null;
    return getSnapshotStatus(selectedProject.latest_snapshot?.id, snapshotAnalyses);
  }, [selectedProject, snapshotAnalyses]);

  const selectedUploadProject = useMemo(
    () => projects.find((project) => project.id === uploadTargetProjectId) || null,
    [projects, uploadTargetProjectId]
  );

  const uploadSnapshotHistory = useMemo(() => {
    const snapshots = Array.isArray(uploadTargetReport?.snapshots) ? uploadTargetReport.snapshots : [];
    const getTimestamp = (value) => {
      const parsed = new Date(value);
      const timestamp = parsed.getTime();
      return Number.isFinite(timestamp) ? timestamp : 0;
    };

    return snapshots
      .map((entry) => entry?.snapshot)
      .filter((snapshot) => Boolean(snapshot?.id))
      .sort((left, right) => getTimestamp(right.ingested_at) - getTimestamp(left.ingested_at));
  }, [uploadTargetReport]);

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
                  {projects.map((project) => {
                    const totalCommits = normalizeMetricCount(project.metrics?.total_commits);
                    const userCommits = normalizeMetricCount(project.metrics?.user_commits);
                    const contributorCount = normalizeMetricCount(project.metrics?.contributor_count);
                    const showContributionStats = totalCommits > 0 || userCommits > 0 || contributorCount > 0;
                    const analysisStatus = getSnapshotStatus(project.latest_snapshot?.id, snapshotAnalyses);

                    return (
                      <article key={project.id} className="project-card">
                        <h3>{project.name}</h3>
                        <p>Type: {project.project_type || 'Unknown'}</p>
                        {showContributionStats && (
                          <>
                            <p>Commits: {totalCommits}</p>
                            <p>Your commits: {userCommits}</p>
                            <p>Contributors: {contributorCount}</p>
                          </>
                        )}
                        <p className={analysisStatus.isRunning ? 'analysis-pill analysis-pill-running' : 'analysis-pill'}>
                          {analysisStatus.badge}
                        </p>
                        {analysisStatus.progress && <p className="muted">{analysisStatus.progress}</p>}
                        {analysisStatus.detail && <p className="muted">{analysisStatus.detail}</p>}
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
                          <button
                            className="secondary-btn"
                            type="button"
                            onClick={() => deleteProject(project)}
                            disabled={deletingProjectId === project.id}
                          >
                            {deletingProjectId === project.id ? 'Deleting...' : 'Delete Project'}
                          </button>
                        </div>
                      </article>
                    );
                  })}
                </div>
              )}
            </section>
          )}

          {view === 'upload' && (
            <section className="panel">
              <h2>Upload Project ZIP</h2>
              <p className="muted">Active portfolio: {portfolioId || 'default'}</p>
              <div className="upload-mode-toggle">
                <label className="mode-option">
                  <input
                    type="radio"
                    name="uploadMode"
                    value="new"
                    checked={uploadMode === 'new'}
                    onChange={() => setUploadMode('new')}
                  />
                  New project upload
                </label>
                <label className="mode-option">
                  <input
                    type="radio"
                    name="uploadMode"
                    value="incremental"
                    checked={uploadMode === 'incremental'}
                    onChange={() => setUploadMode('incremental')}
                  />
                  Incremental update for existing project
                </label>
              </div>

              {uploadMode === 'new' ? (
                <>
                  <p className="muted">
                    New project mode creates a separate project record. To add another snapshot to an existing project,
                    choose Incremental update.
                  </p>
                  <label className="field">
                    Project name override (optional)
                    <input
                      type="text"
                      value={uploadProjectName}
                      placeholder="Defaults to filename"
                      onChange={(e) => setUploadProjectName(e.target.value)}
                    />
                  </label>
                </>
              ) : (
                <>
                  <p className="muted">
                    Incremental uploads append a new snapshot and merge data into the selected project. Existing
                    snapshots are preserved, and duplicate files are deduplicated by the backend.
                  </p>
                  {projects.length === 0 ? (
                    <p>No existing projects available yet. Upload a new project first.</p>
                  ) : (
                    <>
                      <label className="field">
                        Project to update
                        <select
                          value={uploadTargetProjectId}
                          onChange={(e) => setUploadTargetProjectId(e.target.value)}
                        >
                          <option value="" disabled>
                            Select a project
                          </option>
                          {projects.map((project) => (
                            <option key={project.id} value={project.id}>
                              {project.name}
                            </option>
                          ))}
                        </select>
                      </label>
                      {selectedUploadProject && (
                        <p className="muted">ZIP contents will be added to: {selectedUploadProject.name}</p>
                      )}
                      <div className="stack-block">
                        <h3>Snapshot history</h3>
                        {uploadHistoryLoading ? (
                          <p>Loading snapshot history...</p>
                        ) : uploadHistoryError ? (
                          <p className="muted">{uploadHistoryError}</p>
                        ) : uploadSnapshotHistory.length === 0 ? (
                          <p className="muted">No snapshots have been recorded for this project yet.</p>
                        ) : (
                          <ul className="simple-list">
                            {uploadSnapshotHistory.map((snapshot, index) => (
                              <li key={snapshot.id}>
                                <span>{snapshot.snapshot_label || `Snapshot ${uploadSnapshotHistory.length - index}`}</span>
                                <span className="muted">
                                  Uploaded {formatDateTime(snapshot.ingested_at)} from{' '}
                                  {snapshot.source_zip_name || 'Unnamed ZIP'}
                                </span>
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    </>
                  )}
                </>
              )}

              <label className="field">
                Snapshot label (optional)
                <input
                  type="text"
                  value={snapshotLabel}
                  placeholder={uploadMode === 'incremental' ? 'e.g. sprint-3 update' : 'e.g. initial import'}
                  onChange={(e) => setSnapshotLabel(e.target.value)}
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
                    if (selected && uploadMode === 'new' && !uploadProjectName.trim()) {
                      setUploadProjectName(normalizeProjectName(selected.name));
                    }
                  }}
                />
              </label>
              {file && <p className="muted">Selected file: {file.name}</p>}
              <button
                className="primary-btn"
                type="button"
                disabled={!file || uploading || (uploadMode === 'incremental' && !uploadTargetProjectId)}
                onClick={handleUpload}
              >
                {uploading ? 'Uploading...' : uploadMode === 'incremental' ? 'Upload Incremental Snapshot' : 'Upload Project'}
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
                  <div className="stack-block">
                    <h3>Analysis Status</h3>
                    {selectedProjectStatus && (
                      <>
                        <p
                          className={
                            selectedProjectStatus.isRunning ? 'analysis-pill analysis-pill-running' : 'analysis-pill'
                          }
                        >
                          {selectedProjectStatus.badge}
                        </p>
                        {selectedProjectStatus.progress && <p>{selectedProjectStatus.progress}</p>}
                        {selectedProjectStatus.detail && <p className="muted">{selectedProjectStatus.detail}</p>}
                      </>
                    )}
                  </div>

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
