import React, { useState } from 'react';
import './Auth.css';

function Auth({ onAuthSuccess, authApi }) {
  // UI State
  const [authMode, setAuthMode] = useState('login');
  const [authBusy, setAuthBusy] = useState(false);
  const [authError, setAuthError] = useState('');

  // Login Form State
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  // Registration Form State
  const [registerDisplayName, setRegisterDisplayName] = useState('');
  const [registerEmail, setRegisterEmail] = useState('');
  const [registerPassword, setRegisterPassword] = useState('');
  const [registerConfirmPassword, setRegisterConfirmPassword] = useState('');

  // --- LOGIC HANDLERS ---

  const handleLogin = async (event) => {
    event.preventDefault();
    setAuthBusy(true);
    setAuthError('');
    try {
      const response = await authApi.login({
        email: loginEmail,
        password: loginPassword,
      });
      onAuthSuccess(response);
    } catch (error) {
      setAuthError(error.message || 'Login failed. Please check your credentials.');
    } finally {
      setAuthBusy(false);
    }
  };

  const handleRegister = async (event) => {
    event.preventDefault();
    setAuthBusy(true);
    setAuthError('');

    if (registerPassword !== registerConfirmPassword) {
      setAuthError('Passwords do not match.');
      setAuthBusy(false);
      return;
    }

    try {
      const response = await authApi.register({
        email: registerEmail,
        password: registerPassword,
        displayName: registerDisplayName,
      });
      onAuthSuccess(response);
    } catch (error) {
      setAuthError(error.message || 'Registration failed.');
    } finally {
      setAuthBusy(false);
    }
  };

  return (
    <div className="screen-shell">
      <div className="auth-layout">
        
        {/* left column */}
        <section className="auth-hero">
          <p className="eyebrow">Artifact Miner</p>
          <h1>Project portfolio intelligence built around real ownership.</h1>
          <p>
            Securely manage, document, and showcase your technical contributions 
            with high-fidelity project snapshots.
          </p>
        </section>

        {/* Right column */}
        <section className="auth-panel">
          <div className="auth-form-container">
            
            
            <div className="auth-toggle">
              <button 
                className={authMode === 'login' ? 'tab active' : 'tab'} 
                onClick={() => { setAuthMode('login'); setAuthError(''); }}
              >
                Log In
              </button>
              <button 
                className={authMode === 'register' ? 'tab active' : 'tab'} 
                onClick={() => { setAuthMode('register'); setAuthError(''); }}
              >
                Create Account
              </button>
            </div>

            {}
            {authError && <div className="error-banner">{authError}</div>}

            {/* condition form rendering */}
            {authMode === 'login' ? (
              <form className="auth-form" onSubmit={handleLogin}>
                <label>
                  Email
                  <input
                    type="email"
                    value={loginEmail}
                    onChange={(e) => setLoginEmail(e.target.value)}
                    placeholder="email"
                    required
                  />
                </label>
                <label>
                  Password
                  <input
                    type="password"
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    placeholder="password"
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
                  Display Name
                  <input
                    type="text"
                    value={registerDisplayName}
                    onChange={(e) => setRegisterDisplayName(e.target.value)}
                    placeholder="John Doe"
                    required
                  />
                </label>
                <label>
                  Email
                  <input
                    type="email"
                    value={registerEmail}
                    onChange={(e) => setRegisterEmail(e.target.value)}
                    placeholder="name@company.com"
                    required
                  />
                </label>
                <label>
                  Password
                  <input
                    type="password"
                    value={registerPassword}
                    onChange={(e) => setRegisterPassword(e.target.value)}
                    placeholder="Create a password"
                    required
                  />
                </label>
                <label>
                  Confirm Password
                  <input
                    type="password"
                    value={registerConfirmPassword}
                    onChange={(e) => setRegisterConfirmPassword(e.target.value)}
                    placeholder="Repeat password"
                    required
                  />
                </label>
                <button className="primary-btn" type="submit" disabled={authBusy}>
                  {authBusy ? 'Creating account...' : 'Create Account'}
                </button>
              </form>
            )}

          </div>
        </section>
      </div>
    </div>
  );
}

export default Auth;