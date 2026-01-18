// frontend/js/ui.js

// ========== ADD THIS FUNCTION AT THE TOP ==========
function safeStringify(obj, space = 2) {
    const seen = new WeakSet();
    
    function replacer(key, value) {
        // Handle circular references
        if (typeof value === 'object' && value !== null) {
            if (seen.has(value)) {
                return '[Circular Reference]';
            }
            seen.add(value);
        }
        
        // Handle very large arrays
        if (Array.isArray(value) && value.length > 100) {
            return value.slice(0, 100).concat(`[ ... ${value.length - 100} more items ]`);
        }
        
        // Handle very large objects
        if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
            const keys = Object.keys(value);
            if (keys.length > 50) {
                const limited = {};
                for (let i = 0; i < Math.min(50, keys.length); i++) {
                    const k = keys[i];
                    limited[k] = value[k];
                }
                limited['...'] = `${keys.length - 50} more keys`;
                return limited;
            }
        }
        
        return value;
    }
    
    try {
        return JSON.stringify(obj, replacer, space);
    } catch (error) {
        return `Error stringifying: ${error.message}`;
    }
}
// ==================================================

let currentUser = null;

// Navigation
function showSection(sectionId) {
    // Update active nav button
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    // Show selected section
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.remove('active');
    });
    document.getElementById(sectionId).classList.add('active');
}

// Upload Form Handler
document.getElementById('uploadForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const fileInput = document.getElementById('zipFile');
    const userId = document.getElementById('userId').value || null;
    const portfolioId = document.getElementById('portfolioId').value || null;
    const projectName = document.getElementById('projectName').value || null;
    const snapshotLabel = document.getElementById('snapshotLabel').value || null;
    
    if (!fileInput.files[0]) {
        showStatus('uploadStatus', 'Please select a ZIP file', 'error');
        return;
    }
    
    // First, handle consent
    try {
        const consent = await postConsent(userId, 'data_access', true);
        currentUser = consent.user_id;
        showStatus('uploadStatus', 'Consent granted. Uploading...', 'success');
        
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        if (currentUser) formData.append('user_id', currentUser);
        if (portfolioId) formData.append('portfolio_id', portfolioId);
        if (projectName) formData.append('project_name', projectName);
        if (snapshotLabel) formData.append('snapshot_label', snapshotLabel);
        
        const result = await uploadProject(formData);
        document.getElementById('uploadResult').textContent = safeStringify(result);
        
        // Store portfolio ID for later use
        if (result.portfolio_id) {
            localStorage.setItem('lastPortfolioId', result.portfolio_id);
        }
        
        showStatus('uploadStatus', `Upload successful! Created ${result.created?.length || 0} projects`, 'success');
        
        // Switch to projects view
        setTimeout(() => showSection('projects'), 2000);
        
    } catch (error) {
        showStatus('uploadStatus', `Upload failed: ${error.message}`, 'error');
    }
});

// Projects Loading
async function loadProjects() {
    const searchInput = document.getElementById('searchPortfolio').value;
    const projectsList = document.getElementById('projectsList');
    projectsList.innerHTML = '<div class="loading">Loading projects...</div>';
    
    try {
        let result;
        if (searchInput) {
            // Try to determine if input is portfolio ID or user ID
            if (searchInput.includes('-')) { // Likely UUID
                result = await getProjects(searchInput, null);
            } else {
                result = await getProjects(null, searchInput);
            }
        } else {
            // Use last portfolio ID or user ID
            const lastPortfolioId = localStorage.getItem('lastPortfolioId');
            if (lastPortfolioId) {
                result = await getProjects(lastPortfolioId, null);
            } else if (currentUser) {
                result = await getProjects(null, currentUser);
            } else {
                throw new Error('Please enter a Portfolio ID or User ID');
            }
        }
        
        displayProjects(result.projects || []);
        document.getElementById('projectsResult').textContent = safeStringify(result);
        
    } catch (error) {
        projectsList.innerHTML = `<div class="status status-error">Error: ${error.message}</div>`;
    }
}

async function loadTopProjects() {
    const searchInput = document.getElementById('searchPortfolio').value;
    const projectsList = document.getElementById('projectsList');
    projectsList.innerHTML = '<div class="loading">Loading top projects...</div>';
    
    try {
        const portfolioId = searchInput || localStorage.getItem('lastPortfolioId');
        if (!portfolioId) throw new Error('Please enter a Portfolio ID');
        
        const result = await getTopProjects(portfolioId);
        displayTopProjects(result.top_projects || []);
        document.getElementById('projectsResult').textContent = safeStringify(result);
        
    } catch (error) {
        projectsList.innerHTML = `<div class="status status-error">Error: ${error.message}</div>`;
    }
}

function displayProjects(projects) {
    const container = document.getElementById('projectsList');
    
    if (!projects || projects.length === 0) {
        container.innerHTML = '<div class="card">No projects found</div>';
        return;
    }
    
    container.innerHTML = projects.map(project => `
        <div class="project-card">
            <h3>${project.name || 'Unnamed Project'}</h3>
            <p><strong>ID:</strong> ${project.id}</p>
            <p><strong>Type:</strong> ${project.project_type || 'N/A'}</p>
            <p><strong>Collaboration:</strong> ${project.collaboration_type || 'N/A'}</p>
            <div class="mt-2">
                <span class="status ${project.metrics?.user_commits ? 'status-success' : 'status-warning'}">
                    ${project.metrics?.user_commits || 0} user commits
                </span>
                <span class="status">
                    ${project.metrics?.total_commits || 0} total commits
                </span>
            </div>
            <div class="mt-3">
                <button class="btn btn-secondary" onclick="viewProjectDetails('${project.id}')">
                    View Details
                </button>
            </div>
        </div>
    `).join('');
}

function displayTopProjects(topProjects) {
    const container = document.getElementById('projectsList');
    
    if (!topProjects || topProjects.length === 0) {
        container.innerHTML = '<div class="card">No top projects found</div>';
        return;
    }
    
    container.innerHTML = topProjects.map(project => `
        <div class="project-card">
            <h3>${project.name || 'Unnamed Project'}</h3>
            <p><strong>Rank Score:</strong> ${project.rank_score?.toFixed(2) || 'N/A'}</p>
            ${project.features?.user_commits ? 
                `<p><strong>User Commits:</strong> ${project.features.user_commits}</p>` : ''}
            ${project.summary?.top_languages ? 
                `<p><strong>Top Languages:</strong> ${project.summary.top_languages}</p>` : ''}
            ${project.summary?.top_skills ? 
                `<p><strong>Top Skills:</strong> ${project.summary.top_skills}</p>` : ''}
            <div class="mt-3">
                <button class="btn btn-primary" onclick="generateResumeFromProject('${project.project_id}')">
                    Generate Resume
                </button>
            </div>
        </div>
    `).join('');
}

// Skills Analysis
async function getSkills() {
    const snapshotId = document.getElementById('snapshotId').value;
    if (!snapshotId) {
        showStatus('skillsContainer', 'Please enter a Snapshot ID', 'error');
        return;
    }
    
    showStatus('skillsContainer', 'Loading skills...', 'info');
    
    try {
        const skills = await getSnapshotSkills(snapshotId);
        const analyses = await getSnapshotAnalyses(snapshotId);
        
        // Display skills
        const skillsHTML = (skills.skills || []).map(skill => `
            <div class="skill-tag">
                ${skill.skill_name || 'Unknown'}
                <small>(${skill.confidence ? (skill.confidence * 100).toFixed(1) + '%' : 'N/A'})</small>
            </div>
        `).join('');
        
        document.getElementById('skillsContainer').innerHTML = `
            <h4>Top ${(skills.skills || []).length} Skills:</h4>
            <div class="flex flex-wrap">${skillsHTML || 'No skills found'}</div>
        `;
        
        // Display analyses
        const analysesHTML = (analyses.analyses || []).map(analysis => `
            <div class="status ${analysis.status === 'complete' ? 'status-success' : 
                              analysis.status === 'failed' ? 'status-error' : 'status-warning'}">
                ${analysis.analysis_type || 'Unknown'}: ${analysis.status || 'unknown'}
                ${analysis.error ? `<br><small>Error: ${analysis.error}</small>` : ''}
            </div>
        `).join('');
        
        document.getElementById('analysisResults').innerHTML = `
            <h4>Analyses:</h4>
            <div class="flex flex-wrap">${analysesHTML || 'No analyses found'}</div>
        `;
        
    } catch (error) {
        showStatus('skillsContainer', `Error: ${error.message}`, 'error');
    }
}

// ========== FIXED requestExternalAnalysis FUNCTION ==========
async function requestExternalAnalysis() {
    const snapshotId = document.getElementById('snapshotId').value;
    if (!snapshotId) {
        alert('Please enter a Snapshot ID');
        return;
    }
    
    try {
        const result = await apiCall(`/snapshots/${snapshotId}/external-analysis`, {
            method: 'POST'
        });
        
        // SAFELY check for status
        const status = result?.status || result?.analysis?.status || 'unknown';
        alert(`External analysis requested. Status: ${status}`);
        
        // Refresh the display
        getSkills();
        
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}
// ============================================================

// Resume Generation
async function generateResume() {
    const projectId = document.getElementById('resumeProjectId').value;
    if (!projectId) {
        alert('Please enter a Project ID');
        return;
    }
    
    try {
        const resume = await generateResumeItem(projectId);
        document.getElementById('resumeItems').innerHTML = `
            <div class="card">
                <h4>Generated Resume Item</h4>
                <p><strong>Resume ID:</strong> ${resume.resume_id || 'N/A'}</p>
                <p><strong>Project:</strong> ${resume.project_name || 'N/A'}</p>
                <p><strong>Generated At:</strong> ${resume.generated_at ? new Date(resume.generated_at).toLocaleString() : 'N/A'}</p>
                <button class="btn btn-success mt-2" onclick="downloadResumePDF('${resume.resume_id || ''}')">
                    Download PDF
                </button>
                <div class="mt-2">
                    <strong>Content Preview:</strong>
                    <pre>${safeStringify(resume.content_json || {}).substring(0, 500)}...</pre>
                </div>
            </div>
        `;
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

async function generatePortfolioSummary() {
    const projectId = document.getElementById('resumeProjectId').value;
    if (!projectId) {
        // Need portfolio ID, try to get from localStorage
        const portfolioId = localStorage.getItem('lastPortfolioId');
        if (!portfolioId) {
            alert('Please enter a Project ID or upload a project first');
            return;
        }
        
        try {
            const summary = await generatePortfolioSummary(portfolioId);
            const count = summary?.generated?.length || 0;
            alert(`Portfolio summary generated for ${count} projects`);
        } catch (error) {
            alert(`Error: ${error.message}`);
        }
    }
}

// Identity Management
async function setIdentityRules() {
    const userId = document.getElementById('identityUserId').value || currentUser;
    const emails = document.getElementById('matchEmails').value;
    const names = document.getElementById('matchNames').value;
    
    if (!userId) {
        alert('Please enter a User ID or upload a project first');
        return;
    }
    
    try {
        const result = await setIdentityRules(userId, emails, names);
        alert('Identity rules updated successfully');
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

async function autoLinkIdentity(apply = false) {
    const userId = document.getElementById('identityUserId').value || currentUser;
    const portfolioId = document.getElementById('autoLinkPortfolio').value || null;
    
    if (!userId) {
        alert('Please enter a User ID or upload a project first');
        return;
    }
    
    try {
        const result = await autoLinkIdentity(userId, portfolioId, !apply, true);
        
        const results = result.results || [];
        const resultsHTML = results.map(r => `
            <div class="status ${r.applied ? 'status-success' : 'status-warning'}">
                ${r.project_id || 'Unknown'}: ${r.chosen_contributor_id || 'No match'} (${r.reason || 'unknown'})
            </div>
        `).join('');
        
        document.getElementById('autoLinkResults').innerHTML = `
            <h4>Auto-link Results (${apply ? 'Applied' : 'Dry Run'}):</h4>
            <div>${resultsHTML || 'No results'}</div>
            <p class="mt-2">Processed ${results.length} projects</p>
        `;
        
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

// Analytics
async function checkHealth() {
    try {
        const health = await checkHealth();
        document.getElementById('healthStatus').innerHTML = `
            <div class="status status-success">
                API and Database are healthy
            </div>
        `;
    } catch (error) {
        document.getElementById('healthStatus').innerHTML = `
            <div class="status status-error">
                Health check failed: ${error.message}
            </div>
        `;
    }
}

async function getProjectReport() {
    const projectId = document.getElementById('reportProjectId').value;
    if (!projectId) {
        alert('Please enter a Project ID');
        return;
    }
    
    try {
        const report = await apiCall(`/projects/${projectId}/report?include_raw_analyses=false`);
        document.getElementById('analyticsResult').textContent = safeStringify(report);
    } catch (error) {
        document.getElementById('analyticsResult').textContent = `Error: ${error.message}`;
    }
}

async function getChronologicalSkills() {
    const portfolioId = document.getElementById('chronoPortfolio').value;
    if (!portfolioId) {
        alert('Please enter a Portfolio ID');
        return;
    }
    
    try {
        const skills = await getChronologicalSkills(portfolioId);
        document.getElementById('analyticsResult').textContent = safeStringify(skills);
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

async function refreshCollaboration() {
    const projectId = document.getElementById('reportProjectId').value;
    if (!projectId) {
        alert('Please enter a Project ID');
        return;
    }
    
    try {
        const result = await refreshCollaboration(projectId);
        alert(`Collaboration refreshed: ${result.collaboration_type || 'unknown'} (${result.contributor_count || 0} contributors)`);
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

async function listContributors() {
    const projectId = document.getElementById('reportProjectId').value;
    if (!projectId) {
        alert('Please enter a Project ID');
        return;
    }
    
    try {
        const contributors = await listContributors(projectId);
        document.getElementById('analyticsResult').textContent = safeStringify(contributors);
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

// Helper functions
function showStatus(elementId, message, type = 'info') {
    const element = document.getElementById(elementId);
    const className = `status status-${type}`;
    element.innerHTML = `<div class="${className}">${message}</div>`;
}

// Utility functions for other sections
function viewProjectDetails(projectId) {
    document.getElementById('reportProjectId').value = projectId;
    document.getElementById('resumeProjectId').value = projectId;
    showSection('analytics');
}

function generateResumeFromProject(projectId) {
    document.getElementById('resumeProjectId').value = projectId;
    showSection('resume');
    setTimeout(() => generateResume(), 100);
}