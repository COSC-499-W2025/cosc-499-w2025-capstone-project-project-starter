import { initApp, submitPrivacyConsent } from './js/core.js';
import { toggleSubmenu, showView, selectProject } from './js/ui.js';
import {
    uploadFile,
    refreshProjects,
    onProjectSelect,
    analyzeProject,
    analyzeProjectGemini,
    rankProjects,
    rankTop3,
    loadRankings,
    cleanupInsights,
    loadSkills,
    savePreferences,
    generateResume,
    viewResume,
    deleteResume,
    viewPortfolio,
    generatePortfolio,
    addThumbnail,
    runLLMSummary,
    logout
} from './js/actions.js';
import { toggleTheme, initTheme } from './js/theme.js';

initApp();
initTheme();

window.toggleSubmenu = toggleSubmenu;
window.showView = showView;
window.selectProject = selectProject;
window.onProjectSelect = onProjectSelect;
window.submitPrivacyConsent = submitPrivacyConsent;
window.uploadFile = uploadFile;
window.refreshProjects = refreshProjects;
window.analyzeProject = analyzeProject;
window.analyzeProjectGemini = analyzeProjectGemini;
window.rankProjects = rankProjects;
window.rankTop3 = rankTop3;
window.loadRankings = loadRankings;
window.cleanupInsights = cleanupInsights;
window.loadSkills = loadSkills;
window.savePreferences = savePreferences;
window.generateResume = generateResume;
window.viewResume = viewResume;
window.deleteResume = deleteResume;
window.viewPortfolio = viewPortfolio;
window.generatePortfolio = generatePortfolio;
window.addThumbnail = addThumbnail;
window.runLLMSummary = runLLMSummary;
window.logout = logout;
window.toggleTheme = toggleTheme;
