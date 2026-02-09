import { state, setCurrentUser, setProjects } from './state.js';

export function initApp() {
    document.addEventListener('DOMContentLoaded', () => {
        const storedUser = localStorage.getItem('user');
        if (!storedUser) {
            window.location.href = 'index.html';
            return;
        }
        try {
            const user = JSON.parse(storedUser);
            setCurrentUser(user);
            document.getElementById('username').textContent = state.currentUser.user_name;
            loadProjects();
        } catch (e) {
            localStorage.removeItem('user');
            window.location.href = 'index.html';
        }
    });
}

export function showMessage(text, type) {
    const msg = document.getElementById('messageBox');
    msg.textContent = text;
    msg.className = `message ${type}`;
    msg.style.display = 'block';
    setTimeout(() => msg.style.display = 'none', 5000);
}

export async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(`${window.location.origin}${endpoint}`, {
            headers: { 'Content-Type': 'application/json', ...options.headers },
            ...options
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Request failed');
        return data;
    } catch (e) {
        showMessage(e.message || 'Request failed', 'error');
        throw e;
    }
}

export async function loadProjects() {
    try {
        const data = await apiCall(`/api/projects?user_name=${state.currentUser.user_name}`);
        if (data.success) setProjects(data.projects || []);
    } catch (e) {
        console.error('Failed to load projects:', e);
    }
}

export async function getProjectDetails(id) {
    try {
        return await apiCall(`/api/projects/${id}?user_name=${state.currentUser.user_name}`);
    } catch (e) {
        return null;
    }
}

export async function submitPrivacyConsent(consentGiven) {
    try {
        const data = await apiCall('/api/privacy-consent', {
            method: 'POST',
            body: JSON.stringify({
                consent_given: consentGiven,
                user_id: state.currentUser.user_id || state.currentUser.user_name
            })
        });
        if (data.success) {
            showMessage(`Privacy consent ${consentGiven ? 'granted' : 'denied'}`, 'success');
        }
        return data;
    } catch (e) {
        return null;
    }
}
