const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001';

async function parseResponse(response) {
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return response.json();
  }
  const text = await response.text();
  return text ? { detail: text } : {};
}

async function apiRequest(path, { method = 'GET', token, body, isForm = false } = {}) {
  const headers = {};
  if (!isForm) {
    headers['Content-Type'] = 'application/json';
  }
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: isForm ? body : body ? JSON.stringify(body) : undefined,
  });
  const payload = await parseResponse(response);
  if (!response.ok) {
    const detail = payload?.detail;
    throw new Error(typeof detail === 'string' ? detail : `Request failed (${response.status})`);
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
  logout: (token) =>
    apiRequest('/auth/logout', {
      method: 'POST',
      token,
    }),
};

export const projectApi = {
  list: (token) => apiRequest('/projects', { token }),
  upload: (token, { file, projectName }) => {
    const formData = new FormData();
    formData.append('file', file);
    if (projectName) {
      formData.append('project_name', projectName);
    }
    return apiRequest('/projects/upload', {
      method: 'POST',
      token,
      body: formData,
      isForm: true,
    });
  },
};

export { API_BASE_URL };
