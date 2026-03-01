import React, { useState } from 'react';
import './App.css';
import Auth from './Auth';
import Dashboard from './Dashboard'; 


const BASE_URL = process.env.REACT_APP_API_URL; 

// --- AUTH API ---
const authApi = {
  login: async (credentials) => {
    const response = await fetch(`${BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials),
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || 'Login failed');
    }
    return response.json();
  },
  register: async (userData) => {
    const response = await fetch(`${BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(userData),
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || 'Registration failed');
    }
    return response.json();
  }
};

// --- PROJECT API ---
const projectApi = {
  listProjects: async (token) => {
    const response = await fetch(`${BASE_URL}/projects`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    if (!response.ok) throw new Error('Failed to fetch projects');
    return response.json();
  },
  
  uploadProject: async (token, { file, projectName }) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('project_name', projectName);

    const response = await fetch(`${BASE_URL}/projects/upload`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData,
    });
    if (!response.ok) throw new Error('Upload failed');
    return response.json();
  },

  getProjectReport: async (token, projectId) => {
    const response = await fetch(`${BASE_URL}/projects/${projectId}/report`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    return response.json();
  },

  getProjectContributors: async (token, projectId) => {
    const response = await fetch(`${BASE_URL}/projects/${projectId}/contributors`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    return response.json();
  },

  getSnapshotSkills: async (token, snapshotId) => {
    const response = await fetch(`${BASE_URL}/snapshots/${snapshotId}/skills`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    return response.json();
  },

  getPortfolioTopProjects: async (token, portfolioId) => {
    const response = await fetch(`${BASE_URL}/portfolio/${portfolioId}/top-projects`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    if (!response.ok) throw new Error('Top projects route not found');
    return response.json();
  },

  getPortfolioSkillTimeline: async (token, portfolioId) => {
    const response = await fetch(`${BASE_URL}/portfolio/${portfolioId}/skills/chronological`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    if (!response.ok) throw new Error('Timeline route not found');
    return response.json();
  },

  generateResume: async (token, projectId) => {
    const response = await fetch(`${BASE_URL}/resume/generate`, {
      method: 'POST',
      headers: { 
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ project_id: projectId })
    });
    if (!response.ok) throw new Error('Resume generation failed');
    return response.json();
  }
};

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