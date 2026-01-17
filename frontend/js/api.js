// frontend/js/api.js
const API_BASE = 'http://localhost:5001';

async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
            ...options,
        });

        if (!response.ok) {
            throw new Error(`API Error: ${response.status} ${response.statusText}`);
        }

        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        throw error;
    }
}

async function uploadProject(formData) {
    const response = await fetch(`${API_BASE}/projects/upload`, {
        method: 'POST',
        body: formData,
    });
    return response.json();
}

async function postConsent(userId, consentType, granted) {
    return apiCall('/privacy-consent', {
        method: 'POST',
        body: JSON.stringify({
            user_id: userId,
            consent_type: consentType,
            granted: granted,
            version: 1
        })
    });
}

async function getProjects(portfolioId, userId) {
    let url = '/projects';
    const params = new URLSearchParams();
    if (portfolioId) params.append('portfolio_id', portfolioId);
    if (userId) params.append('user_id', userId);
    if (params.toString()) url += `?${params.toString()}`;
    return apiCall(url);
}

async function getTopProjects(portfolioId, limit = 5) {
    return apiCall(`/portfolio/${portfolioId}/top-projects?limit=${limit}`);
}

async function getSnapshotSkills(snapshotId, limit = 20) {
    return apiCall(`/snapshots/${snapshotId}/skills?limit=${limit}`);
}

async function getSnapshotAnalyses(snapshotId) {
    return apiCall(`/snapshots/${snapshotId}/analyses`);
}

async function requestExternalAnalysis(snapshotId) {
    return apiCall(`/snapshots/${snapshotId}/external-analysis`, {
        method: 'POST'
    });
}

async function getExternalAnalysis(snapshotId) {
    return apiCall(`/snapshots/${snapshotId}/external-analysis`);
}

async function generateResumeItem(projectId, preferExternal = true) {
    return apiCall('/resume/generate', {
        method: 'POST',
        body: JSON.stringify({
            project_id: projectId,
            prefer_external_bullets: preferExternal
        })
    });
}

async function generatePortfolioSummary(portfolioId, limit = 5, persist = true) {
    return apiCall('/portfolio/generate', {
        method: 'POST',
        body: JSON.stringify({
            portfolio_id: portfolioId,
            limit: limit,
            persist: persist
        })
    });
}

async function getResumeItem(resumeId) {
    return apiCall(`/resume/${resumeId}`);
}

async function downloadResumePDF(resumeId) {
    window.open(`${API_BASE}/resume/${resumeId}/pdf`, '_blank');
}

async function setIdentityRules(userId, emails, names) {
    return apiCall(`/users/${userId}/identity/rules`, {
        method: 'POST',
        body: JSON.stringify({
            match_emails: emails.split(',').map(e => e.trim()).filter(e => e),
            match_names: names.split(',').map(n => n.trim()).filter(n => n)
        })
    });
}

async function autoLinkIdentity(userId, portfolioId = null, dryRun = true, persist = true) {
    return apiCall(`/users/${userId}/identity/auto-link`, {
        method: 'POST',
        body: JSON.stringify({
            portfolio_id: portfolioId,
            dry_run: dryRun,
            persist_project_map: persist
        })
    });
}

async function getProjectReport(projectId, includeRawAnalyses = false) {
    return apiCall(`/projects/${projectId}/report?include_raw_analyses=${includeRawAnalyses}`);
}

async function checkHealth() {
    return apiCall('/health');
}

async function refreshCollaboration(projectId) {
    return apiCall(`/projects/${projectId}/refresh-collaboration`, {
        method: 'POST'
    });
}

async function listContributors(projectId) {
    return apiCall(`/projects/${projectId}/contributors`);
}

async function getChronologicalSkills(portfolioId, direction = 'asc', limit = 500) {
    return apiCall(`/portfolio/${portfolioId}/skills/chronological?direction=${direction}&limit=${limit}`);
}