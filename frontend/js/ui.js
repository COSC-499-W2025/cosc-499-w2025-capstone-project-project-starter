import { API_BASE_URL, state, setSelectedProjectId } from './state.js';
import { getViews } from './views.js';

export function toggleSubmenu(submenuId, toggleId) {
    const submenu = document.getElementById(submenuId);
    const toggle = document.getElementById(toggleId);
    const isOpen = submenu.classList.toggle('open');
    toggle.classList.toggle('open', isOpen);
}

export function renderProjectsList(containerId, onSelect) {
    const container = document.getElementById(containerId);
    if (!state.projects.length) {
        container.innerHTML = '<p>No projects found</p>';
        return;
    }
    container.innerHTML = state.projects.map(p => {
        const thumb = p.has_thumbnail
            ? `<img class="project-thumb" src="${API_BASE_URL}/api/projects/${p.id}/thumbnail" alt="Thumbnail for ${p.filename}" onerror="this.style.display='none'">`
            : '';
        return `<div class="project-item" onclick="selectProject(${p.id}, '${containerId}', '${onSelect}')">
            ${thumb}
            <div class="project-info">
                <strong>${p.filename}</strong> (ID: ${p.id})<br>
                <small>Files: ${p.file_count || 0} | Created: ${new Date(p.created_at).toLocaleDateString()}</small>
            </div>
        </div>`;
    }).join('');
}

const projectListViews = {
    list: 'projectsList',
    analyze: 'analyzeProjectsList',
    cleanup: 'cleanupProjectsList',
    thumbnail: 'thumbnailProjectsList',
    'llm-summary': 'llmProjectsList'
};

export function initProjectList(viewName) {
    const listId = projectListViews[viewName];
    if (!listId) return;
    setTimeout(() => {
        renderProjectsList(listId, 'onProjectSelect');
    }, 100);
}

export function selectProject(id, containerId, callback) {
    setSelectedProjectId(id);
    document.querySelectorAll(`#${containerId} .project-item`).forEach(el => el.classList.remove('selected'));
    event.target.closest('.project-item').classList.add('selected');
    if (window[callback]) window[callback](id);
}

export function showView(viewName) {
    const container = document.getElementById('viewContainer');
    setSelectedProjectId(null);

    const views = getViews(state.currentUser);
    container.innerHTML = views[viewName] || '<div class="view-panel"><p>View not found</p></div>';

    initProjectList(viewName);
}
