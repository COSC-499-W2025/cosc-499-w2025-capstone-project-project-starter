const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001';

async function parseResponse(response) {
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return response.json();
  }
  const text = await response.text();
  return text ? { detail: text } : {};
}

async function apiRequest(path, { method = 'GET', token, body, headers = {}, isForm = false } = {}) {
  const requestHeaders = { ...headers };
  if (!isForm) {
    requestHeaders['Content-Type'] = 'application/json';
  }
  if (token) {
    requestHeaders.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: requestHeaders,
    body: isForm ? body : body ? JSON.stringify(body) : undefined,
  });

  const payload = await parseResponse(response);
  if (!response.ok) {
    const message = (payload && payload.detail) || `Request failed with status ${response.status}`;
    const error = new Error(typeof message === 'string' ? message : 'Request failed');
    error.status = response.status;
    error.payload = payload;
    throw error;
  }
  return payload;
}

export const authApi = {
  register: ({ email, password, displayName }) =>
    apiRequest('/auth/register', {
      method: 'POST',
      body: {
        email,
        password,
        display_name: displayName || null,
        consent_data_access: true,
      },
    }),
  login: ({ email, password }) =>
    apiRequest('/auth/login', {
      method: 'POST',
      body: { email, password },
    }),
  me: (token) => apiRequest('/auth/me', { token }),
  logout: (token) => apiRequest('/auth/logout', { method: 'POST', token }),
  submitPrivacyConsent: (token, { userId, consentType, granted, version = 1 }) =>
    apiRequest('/privacy-consent', {
      method: 'POST',
      token,
      body: {
        user_id: userId,
        consent_type: consentType,
        granted,
        version,
      },
    }),
};

export const projectApi = {
  listProjects: (token) => apiRequest('/projects', { token }),
  updateProject: (
    token,
    projectId,
    { displayName, userRole, evidenceJson, evidence, metrics, feedback, evaluation } = {}
  ) => {
    const body = {};
    if (displayName !== undefined) body.display_name = displayName;
    if (userRole !== undefined) body.user_role = userRole;
    if (evidenceJson !== undefined) body.evidence_json = evidenceJson;
    if (evidence !== undefined) body.evidence = evidence;
    if (metrics !== undefined) body.metrics = metrics;
    if (feedback !== undefined) body.feedback = feedback;
    if (evaluation !== undefined) body.evaluation = evaluation;
    return apiRequest(`/projects/${projectId}`, {
      method: 'PATCH',
      token,
      body,
    });
  },
  deleteProject: (token, projectId) => apiRequest(`/projects/${projectId}`, { method: 'DELETE', token }),
  uploadProject: (token, { file, projectName, snapshotLabel, analysisMode }) => {
    const formData = new FormData();
    formData.append('file', file);
    if (projectName) {
      formData.append('project_name', projectName);
    }
    if (snapshotLabel) {
      formData.append('snapshot_label', snapshotLabel);
    }
    if (analysisMode) {
      formData.append('analysis_mode', analysisMode);
    }
    return apiRequest('/projects/upload', {
      method: 'POST',
      token,
      body: formData,
      isForm: true,
    });
  },
  getProjectReport: (token, projectId) => apiRequest(`/projects/${projectId}/report`, { token }),
  getProjectContributors: (token, projectId) => apiRequest(`/projects/${projectId}/contributors`, { token }),
  getSnapshotAnalyses: (token, snapshotId) => apiRequest(`/snapshots/${snapshotId}/analyses`, { token }),
  getSnapshotSkills: (token, snapshotId, limit = 20) =>
    apiRequest(`/snapshots/${snapshotId}/skills?limit=${limit}`, { token }),
  getPortfolioTopProjects: (token, portfolioId, limit = 5) =>
    apiRequest(`/portfolio/${portfolioId}/top-projects?limit=${limit}`, { token }),
  getPortfolioSkillTimeline: (token, portfolioId, limit = 50) =>
    apiRequest(`/portfolio/${portfolioId}/skills/chronological?limit=${limit}`, { token }),
  generateResume: (token, projectId) =>
    apiRequest('/resume/generate', {
      method: 'POST',
      token,
      body: {
        project_id: projectId,
        prefer_external_bullets: true,
      },
    }),
  compareProjects: (token, { projectIds = [], attributes = [] }) => {
    const params = new URLSearchParams();
    projectIds.forEach((projectId) => {
      if (projectId) {
        params.append('project_ids', projectId);
      }
    });
    attributes.forEach((attribute) => {
      if (attribute) {
        params.append('attributes', attribute);
      }
    });
    return apiRequest(`/projects/compare?${params.toString()}`, { token });
  },
};

export const userConfigApi = {
  getConfig: (token, userId) => apiRequest(`/users/${userId}/config`, { token }),
  patchConfig: (token, userId, patch) =>
    apiRequest(`/users/${userId}/config`, {
      method: 'PATCH',
      token,
      body: patch,
    }),
};

export { API_BASE_URL };
