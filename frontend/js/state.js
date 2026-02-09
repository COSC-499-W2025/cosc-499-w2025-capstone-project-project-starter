export const API_BASE_URL = window.location.origin;

export const state = {
    currentUser: null,
    projects: [],
    selectedProjectId: null
};

export function setCurrentUser(user) {
    state.currentUser = user;
}

export function setProjects(projectList) {
    state.projects = projectList;
}

export function setSelectedProjectId(projectId) {
    state.selectedProjectId = projectId;
}
