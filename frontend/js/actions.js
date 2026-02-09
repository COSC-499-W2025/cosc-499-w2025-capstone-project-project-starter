import { state } from './state.js';
import { apiCall, showMessage, loadProjects } from './core.js';
import { renderProjectsList } from './ui.js';
import { formatAnalysisResults, formatGeminiAnalysis } from './analysis.js';

export async function uploadFile() {
    const fileInput = document.getElementById('zipFile');
    const resultDiv = document.getElementById('uploadResult');
    if (!fileInput?.files[0]) {
        showMessage('Please select a file', 'error');
        return;
    }
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    resultDiv.innerHTML = 'Uploading...';
    try {
        const response = await fetch(`${window.location.origin}/api/projects/upload?user_name=${state.currentUser.user_name}`, {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        if (data.success) {
            resultDiv.innerHTML = `Upload successful! Project ID: ${data.project_id}`;
            showMessage('Upload successful!', 'success');
            loadProjects();
        } else {
            resultDiv.innerHTML = data.message || 'Upload failed';
            showMessage('Upload failed', 'error');
        }
    } catch (e) {
        resultDiv.innerHTML = `Error: ${e.message}`;
        showMessage('Upload error', 'error');
    }
}

export function refreshProjects() {
    loadProjects().then(() => {
        renderProjectsList('projectsList', 'onProjectSelect');
        showMessage('Projects refreshed', 'success');
    });
}

export function onProjectSelect(id) {
    state.selectedProjectId = id;
}

export async function analyzeProject() {
    if (!state.selectedProjectId) {
        showMessage('Please select a project', 'error');
        return;
    }
    const resultDiv = document.getElementById('analyzeResult');
    resultDiv.innerHTML = 'Analyzing locally...';
    try {
        const data = await apiCall(`/api/projects/${state.selectedProjectId}/analyze?user_name=${state.currentUser.user_name}`, { method: 'POST' });
        if (data.success) {
            resultDiv.innerHTML = formatAnalysisResults(data.analysis);
            showMessage('Local analysis complete', 'success');
        } else {
            resultDiv.innerHTML = `Error: ${data.error || 'Analysis failed'}`;
            showMessage('Analysis failed', 'error');
        }
    } catch (e) {
        resultDiv.innerHTML = `Error: ${e.message}`;
        showMessage('Analysis failed', 'error');
    }
}

export async function analyzeProjectGemini() {
    if (!state.selectedProjectId) {
        showMessage('Please select a project', 'error');
        return;
    }
    const resultDiv = document.getElementById('analyzeResult');
    resultDiv.innerHTML = '<div style="text-align: center; padding: 20px;"><div class="spinner"></div><p style="margin-top: 10px;">Running AI-powered deep analysis with Gemini...</p><p class="text-muted">This may take 15-30 seconds</p></div>';
    try {
        const data = await apiCall(`/api/projects/${state.selectedProjectId}/analyze-gemini?user_name=${state.currentUser.user_name}`, { method: 'POST' });
        if (data.success) {
            resultDiv.innerHTML = formatGeminiAnalysis(data.analysis);
            showMessage('Gemini analysis complete', 'success');
        } else {
            resultDiv.innerHTML = `Error: ${data.error || 'Gemini analysis failed'}`;
            showMessage('Gemini analysis failed', 'error');
        }
    } catch (e) {
        resultDiv.innerHTML = `Error: ${e.message}`;
        showMessage('Gemini analysis failed', 'error');
    }
}

export async function rankProjects() {
    const resultDiv = document.getElementById('rankResult');
    resultDiv.innerHTML = 'Ranking...';
    try {
        const data = await apiCall(`/api/projects/rank?user_name=${state.currentUser.user_name}`, { method: 'POST' });
        if (data.success) {
            resultDiv.innerHTML = `Ranked ${data.count} projects\nTop: ${data.ranked_projects.map((p, i) => `${i+1}. ${p.filename} (${p.score})`).join('\n')}`;
            showMessage('Projects ranked', 'success');
        }
    } catch (e) {
        resultDiv.innerHTML = `Error: ${e.message}`;
    }
}

export async function rankTop3() {
    const resultDiv = document.getElementById('rankTop3Result');
    resultDiv.innerHTML = 'Ranking and summarizing...';
    try {
        const data = await apiCall(`/api/projects/rank-top3?user_name=${state.currentUser.user_name}`, { method: 'POST' });
        if (data.success) {
            resultDiv.innerHTML = `Top 3 Projects:\n${data.top3.map((p, i) => `${i+1}. ${p.filename} (Score: ${p.score})`).join('\n')}`;
            showMessage('Top 3 ranked and summarized', 'success');
        }
    } catch (e) {
        resultDiv.innerHTML = `Error: ${e.message}`;
    }
}

export async function loadRankings() {
    const resultDiv = document.getElementById('rankingsList');
    resultDiv.innerHTML = 'Loading...';
    try {
        const data = await apiCall('/api/projects/rankings');
        if (data.success) {
            resultDiv.innerHTML = data.rankings.length ? data.rankings.map(r => `${r.rank_position}. Project ${r.project_id} (Score: ${r.score})`).join('\n') : 'No rankings found';
        }
    } catch (e) {
        resultDiv.innerHTML = `Error: ${e.message}`;
    }
}

export async function cleanupInsights() {
    if (!state.selectedProjectId) {
        showMessage('Please select a project', 'error');
        return;
    }
    if (!confirm('Delete all insights for this project?')) return;
    const resultDiv = document.getElementById('cleanupResult');
    resultDiv.innerHTML = 'Cleaning up...';
    try {
        const data = await apiCall(`/api/projects/${state.selectedProjectId}/insights`, { method: 'DELETE' });
        if (data.success) {
            resultDiv.innerHTML = `Deleted: ${data.deleted.metrics} metrics, ${data.deleted.files} files, ${data.deleted.projects} projects`;
            showMessage('Insights cleaned up', 'success');
            loadProjects();
        }
    } catch (e) {
        resultDiv.innerHTML = `Error: ${e.message}`;
    }
}

export async function loadSkills() {
    const resultDiv = document.getElementById('skillsResult');
    resultDiv.innerHTML = 'Loading skills...';
    try {
        const data = await apiCall(`/api/skills?user_name=${state.currentUser.user_name}`);
        if (data.success) {
            const skills = data.skills || [];
            const langs = data.languages || [];
            resultDiv.innerHTML = `Skills (${skills.length}): ${skills.slice(0, 10).join(', ')}${skills.length > 10 ? '...' : ''}\nLanguages: ${langs.join(', ') || 'None'}`;
        }
    } catch (e) {
        resultDiv.innerHTML = `Error: ${e.message}`;
    }
}

export async function savePreferences() {
    const gitUsername = document.getElementById('gitUsername')?.value;
    const resultDiv = document.getElementById('preferencesResult');
    resultDiv.innerHTML = 'Saving...';
    try {
        const data = await apiCall('/api/preferences', {
            method: 'POST',
            body: JSON.stringify({ git_username: gitUsername || null })
        });
        if (data.success) {
            resultDiv.innerHTML = `Saved! Git username: ${data.git_username || 'None'}`;
            showMessage('Preferences saved', 'success');
        }
    } catch (e) {
        resultDiv.innerHTML = `Error: ${e.message}`;
    }
}

export async function generateResume() {
    const resultDiv = document.getElementById('resumeGenResult');
    resultDiv.innerHTML = 'Generating resume...';
    try {
        const data = await apiCall(`/api/resume/generate?user_name=${state.currentUser.user_name}`, {
            method: 'POST',
            body: JSON.stringify({ top_projects_count: 5 })
        });
        if (data.success) {
            resultDiv.innerHTML = `Resume generated! Projects: ${data.resume.top_projects_displayed}, Skills: ${data.resume.all_skills?.length || 0}`;
            showMessage('Resume generated successfully', 'success');
        }
    } catch (e) {
        resultDiv.innerHTML = `Error: ${e.message}`;
    }
}

export async function viewResume() {
    const resultDiv = document.getElementById('resumeViewResult');
    resultDiv.innerHTML = 'Loading resume...';
    try {
        const data = await apiCall(`/api/resume/${state.currentUser.user_name}`);
        if (data.success) {
            const r = data.resume.resume_data;
            resultDiv.innerHTML = `Name: ${r.display_name}\nProjects: ${r.top_projects_displayed}/${r.total_projects_analyzed}\nSkills: ${r.all_skills?.length || 0}\nLanguages: ${r.languages?.join(', ') || 'None'}`;
        }
    } catch (e) {
        resultDiv.innerHTML = `Error: ${e.message}`;
    }
}

export async function deleteResume() {
    const resultDiv = document.getElementById('resumeDeleteResult');
    if (!confirm('Delete your resume?')) return;
    resultDiv.innerHTML = 'Deleting...';
    try {
        const data = await apiCall(`/api/resume/${state.currentUser.user_name}`, { method: 'DELETE' });
        if (data.success) {
            resultDiv.innerHTML = 'Resume deleted';
            showMessage('Resume deleted', 'success');
        }
    } catch (e) {
        resultDiv.innerHTML = `Error: ${e.message}`;
    }
}

export async function viewPortfolio() {
    const resultDiv = document.getElementById('portfolioResult');
    resultDiv.innerHTML = 'Loading portfolio...';
    try {
        const data = await apiCall(`/api/portfolio/${state.currentUser.user_name}`);
        if (data.success) {
            const p = data.portfolio;
            resultDiv.innerHTML = `Portfolio Summary\nProjects: ${p.summary?.total_projects || 0}\nTotal LOC: ${p.summary?.total_lines_of_code || 0}\nLanguages: ${p.summary?.unique_languages || 0}`;
        }
    } catch (e) {
        resultDiv.innerHTML = `Error: ${e.message}`;
    }
}

export async function generatePortfolio() {
    const resultDiv = document.getElementById('portfolioResult');
    resultDiv.innerHTML = 'Generating portfolio...';
    try {
        const data = await apiCall(`/api/portfolio/generate?user_name=${state.currentUser.user_name}`, {
            method: 'POST',
            body: JSON.stringify({ top_n: null })
        });
        if (data.success) {
            const p = data.portfolio;
            resultDiv.innerHTML = `Portfolio Generated!\nProjects: ${p.summary?.total_projects || 0}\nTotal LOC: ${p.summary?.total_lines_of_code || 0}\nLanguages: ${p.summary?.unique_languages || 0}`;
            showMessage('Portfolio generated successfully', 'success');
        }
    } catch (e) {
        resultDiv.innerHTML = `Error: ${e.message}`;
    }
}

export async function addThumbnail() {
    if (!state.selectedProjectId) {
        showMessage('Please select a project', 'error');
        return;
    }
    const fileInput = document.getElementById('thumbnailFile');
    const resultDiv = document.getElementById('thumbnailResult');
    if (!fileInput?.files[0]) {
        showMessage('Please select an image file', 'error');
        return;
    }
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    resultDiv.innerHTML = 'Uploading thumbnail...';
    try {
        const response = await fetch(`${window.location.origin}/api/projects/${state.selectedProjectId}/thumbnail?user_name=${state.currentUser.user_name}`, {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        if (data.success) {
            resultDiv.innerHTML = data.message || 'Thumbnail uploaded successfully';
            showMessage('Thumbnail updated', 'success');
            loadProjects();
        } else {
            resultDiv.innerHTML = data.message || 'Thumbnail upload failed';
            showMessage('Thumbnail upload failed', 'error');
        }
    } catch (e) {
        resultDiv.innerHTML = `Error: ${e.message}`;
        showMessage('Thumbnail upload failed', 'error');
    }
}

export async function runLLMSummary() {
    if (!state.selectedProjectId) {
        showMessage('Please select a project', 'error');
        return;
    }
    const resultDiv = document.getElementById('llmSummaryResult');
    resultDiv.innerHTML = '<div style="text-align: center; padding: 20px;">Generating AI summary...</div>';
    try {
        const data = await apiCall(`/api/projects/${state.selectedProjectId}/quick-summary?user_name=${state.currentUser.user_name}`, { method: 'POST' });
        if (data.success) {
            resultDiv.innerHTML = `<div class="analysis-section"><h4>AI-Generated Summary for ${data.project_name}</h4><p style="font-style: italic; line-height: 1.6;">"${data.summary}"</p><p class="text-muted" style="margin-top: 10px; font-size: 0.9em;">Use this summary in your resume or portfolio!</p></div>`;
            showMessage('Summary generated', 'success');
        } else {
            resultDiv.innerHTML = `Error: ${data.error || 'Summary generation failed'}`;
            showMessage('Summary generation failed', 'error');
        }
    } catch (e) {
        resultDiv.innerHTML = `Error: ${e.message}`;
        showMessage('Summary generation failed', 'error');
    }
}

export async function logout() {
    try {
        await fetch(`${window.location.origin}/api/auth/logout`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: state.currentUser.user_name })
        });
    } catch (e) {
        console.error('Logout error:', e);
    } finally {
        localStorage.removeItem('user');
        window.location.href = 'index.html';
    }
}
