import React, { useState } from 'react';
import './App.css';
import Auth from './Auth';
import Dashboard from './Dashboard'; 
import { authApi, projectApi } from './api';


function App() {
  const [token, setToken] = useState(() => localStorage.getItem('token'));
  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const user = localStorage.getItem('user');
      return user ? JSON.parse(user) : null;
    } catch {
      return null;
    }
  });

  const handleAuthSuccess = (data) => {
    localStorage.setItem('token', data.token);
    localStorage.setItem('user', JSON.stringify(data.user));
    setToken(data.token);
    setCurrentUser(data.user);
  };

  const handleLogout = () => {
    localStorage.clear();
    setToken(null);
    setCurrentUser(null);
  };

  if (!token) {
    return <Auth onAuthSuccess={handleAuthSuccess} authApi={authApi} />;
  }

  return (
    <Dashboard 
      token={token} 
      currentUser={currentUser} 
      onLogout={handleLogout} 
      projectApi={projectApi} 
    />
  );
}

export default App;