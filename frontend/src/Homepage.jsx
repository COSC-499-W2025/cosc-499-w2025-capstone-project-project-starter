import React, { useCallback, useEffect, useState } from 'react';
import { authApi, projectApi } from './api';

const AUTH_TOKEN_KEY = 'artifactMiner.authToken';

function defaultProjectName(filename) {
  return filename.replace(/\.zip$/i, '');
}

function Homepage() {
  const [token, setToken] = useState(() => localStorage.getItem(AUTH_TOKEN_KEY) || '');
  const [sessionLoading, setSessionLoading] = useState(true);
  const [user, setUser] = useState(null);
  const [authMode, setAuthMode] = useState('login');
  const [authError, setAuthError] = useState('');
  const [authBusy, setAuthBusy] = useState(false);

  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  const [registerDisplayName, setRegisterDisplayName] = useState('');
  const [registerEmail, setRegisterEmail] = useState('');
  const [registerPassword, setRegisterPassword] = useState('');
  const [registerConfirmPassword, setRegisterConfirmPassword] = useState('');

  const [view, setView] = useState('projects');
  const [projects, setProjects] = useState([]);
  const [loadingProjects, setLoadingProjects] = useState(false);
  const [dashboardError, setDashboardError] = useState('');
  const [dashboardMessage, setDashboardMessage] = useState('');

  const [file, setFile] = useState(null);
  const [projectName, setProjectName] = useState('');
  const [uploading, setUploading] = useState(false);

  const resetDashboard = useCallback(() => {
    setProjects([]);
    setView('projects');
    setDashboardError('');
    setDashboardMessage('');
    setFile(null);
    setProjectName('');
  }, []);

  const clearSession = useCallback(() => {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    setToken('');
    setUser(null);
    setAuthError('');
    resetDashboard();
  }, [resetDashboard]);

  useEffect(() => {
    let active = true;

    async function restoreSession() {
      if (!token) {
        if (active) {
          setSessionLoading(false);
        }
        return;
      }
      try {
        const response = await authApi.me(token);
        if (active) {
          setUser(response.user || null);
        }
      } catch (error) {
        if (active) {
          clearSession();
          setAuthError('Session expired. Please sign in again.');
        }
      } finally {
        if (active) {
          setSessionLoading(false);
        }
      }
    }

    restoreSession();
    return () => {
      active = false;
    };
  }, [token, clearSession]);

  const fetchProjects = useCallback(async () => {
    if (!token) return;
    setLoadingProjects(true);
    setDashboardError('');
    try {
      const response = await projectApi.list(token);
      setProjects(response.projects || []);
    } catch (error) {
      setDashboardError(error.message || 'Unable to load projects.');
    } finally {
      setLoadingProjects(false);
    }
  }, [token]);

  useEffect(() => {
    if (!token || !user) return;
    fetchProjects();
  }, [token, user, fetchProjects]);

  const handleAuthSuccess = useCallback(
    (response) => {
      localStorage.setItem(AUTH_TOKEN_KEY, response.token);
      setToken(response.token);
      setUser(response.user || null);
      setAuthError('');
      resetDashboard();
      setDashboardMessage('Signed in successfully.');
    },
    [resetDashboard]
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
    if (token) {
      try {
        await authApi.logout(token);
      } catch (error) {
        // Clear session client-side even when server logout fails.
      }
    }
    clearSession();
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setDashboardError('');
    setDashboardMessage('');
    try {
      await projectApi.upload(token, {
        file,
        projectName: projectName.trim() || defaultProjectName(file.name),
      });
      setDashboardMessage('Project uploaded.');
      setFile(null);
      setProjectName('');
      await fetchProjects();
      setView('projects');
    } catch (error) {
      setDashboardError(error.message || 'Upload failed.');
    } finally {
      setUploading(false);
    }
  };

  if (sessionLoading) {
    return <div style={s.centered}>Loading session...</div>;
  }

  if (!token || !user) {
    return (
      <div style={s.centered}>
        <div style={s.authCard}>
          <h1 style={s.title}>Project Portfolio Dashboard</h1>
          <p style={s.subtitle}>Log in to access your own projects.</p>

          <div style={s.authToggle}>
            <button
              style={{ ...s.toggleButton, ...(authMode === 'login' ? s.toggleActive : {}) }}
              onClick={() => setAuthMode('login')}
            >
              Log In
            </button>
            <button
              style={{ ...s.toggleButton, ...(authMode === 'register' ? s.toggleActive : {}) }}
              onClick={() => setAuthMode('register')}
            >
              Create Account
            </button>
          </div>

          {authMode === 'login' ? (
            <form onSubmit={handleLogin} style={s.form}>
              <label style={s.label}>
                Email
                <input
                  style={s.input}
                  type="email"
                  value={loginEmail}
                  onChange={(e) => setLoginEmail(e.target.value)}
                  required
                />
              </label>
              <label style={s.label}>
                Password
                <input
                  style={s.input}
                  type="password"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  required
                />
              </label>
              <button style={s.primaryButton} type="submit" disabled={authBusy}>
                {authBusy ? 'Signing in...' : 'Sign In'}
              </button>
            </form>
          ) : (
            <form onSubmit={handleRegister} style={s.form}>
              <label style={s.label}>
                Display Name (optional)
                <input
                  style={s.input}
                  type="text"
                  value={registerDisplayName}
                  onChange={(e) => setRegisterDisplayName(e.target.value)}
                />
              </label>
              <label style={s.label}>
                Email
                <input
                  style={s.input}
                  type="email"
                  value={registerEmail}
                  onChange={(e) => setRegisterEmail(e.target.value)}
                  required
                />
              </label>
              <label style={s.label}>
                Password
                <input
                  style={s.input}
                  type="password"
                  minLength={8}
                  value={registerPassword}
                  onChange={(e) => setRegisterPassword(e.target.value)}
                  required
                />
              </label>
              <label style={s.label}>
                Confirm Password
                <input
                  style={s.input}
                  type="password"
                  minLength={8}
                  value={registerConfirmPassword}
                  onChange={(e) => setRegisterConfirmPassword(e.target.value)}
                  required
                />
              </label>
              <button style={s.primaryButton} type="submit" disabled={authBusy}>
                {authBusy ? 'Creating account...' : 'Create Account'}
              </button>
            </form>
          )}

          {authError && <p style={s.error}>{authError}</p>}
        </div>
      </div>
    );
  }

  return (
    <div style={s.page}>
      <header style={s.header}>
        <div>
          <h1 style={s.headerTitle}>{user.display_name || user.email}</h1>
          <p style={s.headerSubtitle}>Projects are now tied to your authenticated account.</p>
        </div>
        <button style={s.secondaryButton} onClick={handleLogout}>
          Log Out
        </button>
      </header>

      <nav style={s.nav}>
        <button style={{ ...s.navButton, ...(view === 'projects' ? s.navButtonActive : {}) }} onClick={() => setView('projects')}>
          Projects
        </button>
        <button style={{ ...s.navButton, ...(view === 'upload' ? s.navButtonActive : {}) }} onClick={() => setView('upload')}>
          Upload
        </button>
      </nav>

      {dashboardMessage && <p style={s.success}>{dashboardMessage}</p>}
      {dashboardError && <p style={s.error}>{dashboardError}</p>}

      <main style={s.main}>
        {view === 'projects' && (
          <section style={s.section}>
            <h2>Your Projects ({projects.length})</h2>
            {loadingProjects ? (
              <p>Loading projects...</p>
            ) : projects.length === 0 ? (
              <p>No projects yet. Upload one to get started.</p>
            ) : (
              <div style={s.grid}>
                {projects.map((project) => (
                  <article key={project.id} style={s.card}>
                    <h3>{project.name}</h3>
                    <p>Type: {project.project_type || 'Unknown'}</p>
                    <p>Total commits: {project.metrics?.total_commits || 0}</p>
                    <p>Your commits: {project.metrics?.user_commits || 0}</p>
                    <p>Contributors: {project.metrics?.contributor_count || 0}</p>
                  </article>
                ))}
              </div>
            )}
          </section>
        )}

        {view === 'upload' && (
          <section style={s.section}>
            <h2>Upload Project</h2>
            <label style={s.label}>
              Project Name (optional)
              <input
                style={s.input}
                type="text"
                placeholder="Defaults to ZIP filename"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
              />
            </label>
            <label style={s.label}>
              ZIP file
              <input
                style={s.input}
                type="file"
                accept=".zip"
                onChange={(e) => {
                  const selected = e.target.files?.[0] || null;
                  setFile(selected);
                  if (selected && !projectName.trim()) {
                    setProjectName(defaultProjectName(selected.name));
                  }
                }}
              />
            </label>
            {file && <p>Selected file: {file.name}</p>}
            <button style={s.primaryButton} disabled={uploading || !file} onClick={handleUpload}>
              {uploading ? 'Uploading...' : 'Upload Project'}
            </button>
          </section>
        )}
      </main>
    </div>
  );
}

const s = {
  page: {
    minHeight: '100vh',
    backgroundColor: '#f4f7fb',
    padding: '2rem',
    fontFamily: 'Arial, sans-serif',
  },
  centered: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#f4f7fb',
    padding: '1rem',
    fontFamily: 'Arial, sans-serif',
  },
  authCard: {
    width: '100%',
    maxWidth: '560px',
    backgroundColor: 'white',
    borderRadius: '12px',
    padding: '2rem',
    boxShadow: '0 12px 24px rgba(0, 0, 0, 0.08)',
  },
  title: { margin: '0 0 0.5rem 0' },
  subtitle: { margin: '0 0 1.25rem 0', color: '#5f6f86' },
  authToggle: { display: 'flex', gap: '0.5rem', marginBottom: '1rem' },
  toggleButton: {
    flex: 1,
    border: '1px solid #d4dce8',
    backgroundColor: 'white',
    borderRadius: '8px',
    padding: '0.65rem 1rem',
    cursor: 'pointer',
    fontWeight: 600,
  },
  toggleActive: { backgroundColor: '#1f66d8', color: 'white', borderColor: '#1f66d8' },
  form: { display: 'flex', flexDirection: 'column', gap: '0.85rem' },
  label: { display: 'flex', flexDirection: 'column', gap: '0.4rem', fontWeight: 600, fontSize: '0.92rem' },
  input: { border: '1px solid #c8d2e1', borderRadius: '8px', padding: '0.7rem 0.85rem', fontSize: '0.95rem' },
  primaryButton: {
    border: 'none',
    borderRadius: '8px',
    padding: '0.75rem 1rem',
    backgroundColor: '#1f66d8',
    color: 'white',
    fontWeight: 600,
    cursor: 'pointer',
  },
  secondaryButton: {
    border: '1px solid #c8d2e1',
    borderRadius: '8px',
    padding: '0.7rem 1rem',
    backgroundColor: 'white',
    cursor: 'pointer',
    fontWeight: 600,
  },
  header: {
    maxWidth: '1100px',
    margin: '0 auto',
    padding: '1.25rem 1.5rem',
    borderRadius: '12px',
    backgroundColor: 'white',
    boxShadow: '0 8px 20px rgba(0, 0, 0, 0.08)',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '1rem',
  },
  headerTitle: { margin: 0 },
  headerSubtitle: { margin: '0.45rem 0 0 0', color: '#5f6f86' },
  nav: { maxWidth: '1100px', margin: '1rem auto', display: 'flex', gap: '0.5rem' },
  navButton: {
    border: '1px solid #c8d2e1',
    borderRadius: '8px',
    backgroundColor: 'white',
    padding: '0.65rem 1rem',
    cursor: 'pointer',
    fontWeight: 600,
  },
  navButtonActive: { backgroundColor: '#1f66d8', color: 'white', borderColor: '#1f66d8' },
  main: { maxWidth: '1100px', margin: '0 auto' },
  section: {
    backgroundColor: 'white',
    borderRadius: '12px',
    boxShadow: '0 8px 20px rgba(0, 0, 0, 0.08)',
    padding: '1.5rem',
  },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '0.8rem', marginTop: '1rem' },
  card: { border: '1px solid #dee5f0', borderRadius: '10px', padding: '1rem', backgroundColor: '#f9fbff' },
  error: {
    marginTop: '0.9rem',
    backgroundColor: '#ffecec',
    border: '1px solid #f5b4b4',
    color: '#bb1b1b',
    borderRadius: '8px',
    padding: '0.6rem 0.8rem',
  },
  success: {
    maxWidth: '1100px',
    margin: '0 auto 1rem auto',
    backgroundColor: '#ecfaf1',
    border: '1px solid #aee3c1',
    color: '#1c7f45',
    borderRadius: '8px',
    padding: '0.6rem 0.8rem',
  },
};

export default Homepage;
