import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Moon, Sun } from 'lucide-react';
import { API_BASE_URL, authApi, dashboardApi, projectApi, resumeApi, userConfigApi } from './api';

const TOKEN_STORAGE_KEY = 'artifactMiner.authToken';
const ANALYSIS_POLL_INTERVAL_MS = 5000;
const ACTIVE_ANALYSIS_STATUSES = new Set(['pending', 'running']);
const ANALYSIS_TYPE_LABELS = {
  parser: 'Parser',
  git_metrics: 'Git Metrics',
  local_ml: 'Local ML',
  external_llm: 'Ollama',
};
const COMPARISON_ATTRIBUTE_OPTIONS = [
  { value: 'meta', label: 'Project metadata' },
  { value: 'duration', label: 'Project duration' },
  { value: 'contributions', label: 'Contribution totals' },
  { value: 'languages', label: 'Languages' },
  { value: 'frameworks', label: 'Frameworks' },
  { value: 'skills_top', label: 'Top skills' },
  { value: 'skills_chronological', label: 'Chronological skills' },
  { value: 'ranking', label: 'Ranking details' },
  { value: 'activity_counts', label: 'Activity counts' },
  { value: 'evidence', label: 'Evidence JSON' },
];

function normalizeProjectName(filename) {
  return filename.replace(/\.zip$/i, '');
}

const YEAR_MIN = 1900;
const YEAR_MAX_OFFSET_EDU = 10; // allow up to 10 years in the future for expected graduation, covers almost any realistic grad timeline

function getEduYearErrors(startYear, endYear, isCurrent) {
  const currentYear = new Date().getFullYear();
  const maxEndYear = currentYear + YEAR_MAX_OFFSET_EDU;
  const errors = { start_year: null, end_year: null };

  if (startYear !== '' && startYear !== null && startYear !== undefined) {
    const sy = parseInt(startYear, 10);
    if (isNaN(sy) || sy < YEAR_MIN || sy > currentYear) {
      errors.start_year = `Must be between ${YEAR_MIN} and ${currentYear}.`;
    }
  }

  if (!isCurrent && endYear !== '' && endYear !== null && endYear !== undefined) {
    const ey = parseInt(endYear, 10);
    const sy = parseInt(startYear, 10);
    if (isNaN(ey) || ey < YEAR_MIN || ey > maxEndYear) {
      errors.end_year = `Must be between ${YEAR_MIN} and ${maxEndYear}.`;
    } else if (!isNaN(sy) && ey < sy) {
      errors.end_year = 'Cannot be before start year.';
    }
  }

  return errors;
}

function getAwardYearError(awardedYear) {
  const currentYear = new Date().getFullYear();
  if (awardedYear !== '' && awardedYear !== null && awardedYear !== undefined) {
    const y = parseInt(awardedYear, 10);
    if (isNaN(y) || y < YEAR_MIN || y > currentYear) {
      return `Must be between ${YEAR_MIN} and ${currentYear}.`;
    }
  }
  return null;
}

function formatDate(value) {
  if (!value) return 'N/A';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return 'N/A';
  return parsed.toLocaleDateString();
}

function formatDateTime(value) {
  if (!value) return 'N/A';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return 'N/A';
  return parsed.toLocaleString();
}

function normalizeAnalysisStatus(status) {
  return typeof status === 'string' ? status.toLowerCase() : 'pending';
}

function normalizeMetricCount(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function toCsvList(value) {
  if (!value) return [];
  return String(value)
    .split(',')
    .map((entry) => entry.trim())
    .filter((entry) => Boolean(entry));
}

function createDraftId() {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function formatProjectImageDataUrl(mimeType, dataBase64) {
  if (!dataBase64) return '';
  return `data:${mimeType || 'image/png'};base64,${dataBase64}`;
}

function formatEvidenceDraftValue(value) {
  if (value === undefined) return '';
  if (value === null) return 'null';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  try {
    return JSON.stringify(value);
  } catch (error) {
    return '';
  }
}

function normalizeEvidenceSections(evidence) {
  const source = evidence && typeof evidence === 'object' ? evidence : {};
  const metrics =
    source.metrics && typeof source.metrics === 'object' && !Array.isArray(source.metrics) ? source.metrics : {};
  const feedback = Array.isArray(source.feedback) ? source.feedback : [];
  const evaluation =
    source.evaluation && typeof source.evaluation === 'object' && !Array.isArray(source.evaluation)
      ? source.evaluation
      : {};
  return { metrics, feedback, evaluation };
}

function buildObjectEvidenceDraftRows(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return [];
  return Object.entries(value).map(([key, itemValue]) => ({
    id: createDraftId(),
    key: String(key),
    value: formatEvidenceDraftValue(itemValue),
  }));
}

function buildFeedbackDraftRows(value) {
  if (!Array.isArray(value)) return [];
  return value.map((item) => {
    if (item && typeof item === 'object' && !Array.isArray(item)) {
      let source = '';
      if (typeof item.from === 'string') {
        source = item.from;
      } else if (typeof item.source === 'string') {
        source = item.source;
      }

      if (typeof item.note === 'string') {
        return {
          id: createDraftId(),
          source,
          note: item.note,
        };
      }
      if (typeof item.feedback === 'string') {
        return {
          id: createDraftId(),
          source,
          note: item.feedback,
        };
      }
      if (typeof item.comment === 'string') {
        return {
          id: createDraftId(),
          source,
          note: item.comment,
        };
      }

      return {
        id: createDraftId(),
        source: '',
        note: formatEvidenceDraftValue(item),
      };
    }

    return {
      id: createDraftId(),
      source: '',
      note: formatEvidenceDraftValue(item),
    };
  });
}

function parseEvidenceValue(rawValue) {
  const text = String(rawValue ?? '').trim();
  if (!text) {
    return { ok: false, error: 'Value is required.' };
  }

  if (/^-?\d+(\.\d+)?$/.test(text)) {
    const parsedNumber = Number(text);
    if (Number.isFinite(parsedNumber)) {
      return { ok: true, value: parsedNumber };
    }
  }

  const lowered = text.toLowerCase();
  if (lowered === 'true') return { ok: true, value: true };
  if (lowered === 'false') return { ok: true, value: false };
  if (lowered === 'null') return { ok: true, value: null };

  if (text.startsWith('{') || text.startsWith('[') || text.startsWith('"')) {
    try {
      return { ok: true, value: JSON.parse(text) };
    } catch (error) {
      return { ok: false, error: 'Invalid JSON value.' };
    }
  }

  return { ok: true, value: text };
}

function buildObjectEvidencePayload(rows, sectionLabel) {
  const payload = {};
  const seenKeys = new Set();
  const entries = Array.isArray(rows) ? rows : [];

  for (let index = 0; index < entries.length; index += 1) {
    const row = entries[index] || {};
    const key = String(row.key || '').trim();
    const rawValue = String(row.value || '').trim();

    if (!key && !rawValue) {
      continue;
    }

    if (!key) {
      return { ok: false, error: `${sectionLabel}: row ${index + 1} is missing a key.` };
    }

    if (seenKeys.has(key)) {
      return { ok: false, error: `${sectionLabel}: "${key}" is duplicated.` };
    }

    const parsed = parseEvidenceValue(rawValue);
    if (!parsed.ok) {
      return { ok: false, error: `${sectionLabel}: "${key}" has an invalid value.` };
    }

    seenKeys.add(key);
    payload[key] = parsed.value;
  }

  return { ok: true, value: payload };
}

function buildFeedbackEvidencePayload(rows) {
  const payload = [];
  const entries = Array.isArray(rows) ? rows : [];

  for (let index = 0; index < entries.length; index += 1) {
    const row = entries[index] || {};
    const source = String(row.source || '').trim();
    const note = String(row.note || '').trim();

    if (!source && !note) {
      continue;
    }

    if (!note) {
      return { ok: false, error: `Feedback: row ${index + 1} is missing feedback text.` };
    }

    if (source) {
      payload.push({ from: source, note });
      continue;
    }

    const parsed = parseEvidenceValue(note);
    if (!parsed.ok) {
      return { ok: false, error: `Feedback: row ${index + 1} has an invalid JSON value.` };
    }
    payload.push(parsed.value);
  }

  return { ok: true, value: payload };
}

function summarizeSnapshotAnalyses(analyses) {
  const rows = Array.isArray(analyses) ? analyses : [];

  if (rows.length === 0) {
    return {
      badge: 'Analysis queued',
      detail: 'Waiting for workers to pick up this snapshot.',
      progress: null,
      isRunning: true,
    };
  }

  const normalized = rows.map((analysis) => ({
    analysisType: analysis?.analysis_type || 'unknown',
    status: normalizeAnalysisStatus(analysis?.status),
  }));

  const total = normalized.length;
  const completeCount = normalized.filter((entry) => entry.status === 'complete').length;
  const failed = normalized.filter((entry) => entry.status === 'failed');
  const active = normalized.filter((entry) => ACTIVE_ANALYSIS_STATUSES.has(entry.status));
  const external = normalized.find((entry) => entry.analysisType === 'external_llm');

  if (failed.length > 0) {
    const failedLabels = failed
      .map((entry) => ANALYSIS_TYPE_LABELS[entry.analysisType] || entry.analysisType)
      .join(', ');
    return {
      badge: external?.status === 'failed' ? 'Ollama analysis failed' : 'Analysis failed',
      detail: `Failed jobs: ${failedLabels}`,
      progress: `${completeCount}/${total} complete`,
      isRunning: false,
    };
  }

  if (external?.status === 'running') {
    return {
      badge: 'Ollama analysis running',
      detail: 'External model generation is in progress and may take some time.',
      progress: `${completeCount}/${total} complete`,
      isRunning: true,
    };
  }

  if (external?.status === 'pending') {
    return {
      badge: 'Ollama analysis queued',
      detail: 'Waiting for the external model worker to start.',
      progress: `${completeCount}/${total} complete`,
      isRunning: true,
    };
  }

  if (active.length > 0) {
    const runningLabels = active
      .map((entry) => ANALYSIS_TYPE_LABELS[entry.analysisType] || entry.analysisType)
      .join(', ');
    return {
      badge: 'Analysis in progress',
      detail: `Running: ${runningLabels}`,
      progress: `${completeCount}/${total} complete`,
      isRunning: true,
    };
  }

  return {
    badge: external ? 'Analysis complete (Ollama done)' : 'Analysis complete',
    detail: 'All queued analyses finished.',
    progress: `${completeCount}/${total} complete`,
    isRunning: false,
  };
}

function getSnapshotStatus(snapshotId, snapshotAnalyses) {
  if (!snapshotId) {
    return {
      badge: 'No snapshot yet',
      detail: 'Upload a ZIP to start analysis.',
      progress: null,
      isRunning: false,
    };
  }

  const entry = snapshotAnalyses[snapshotId];

  if (entry === undefined) {
    return {
      badge: 'Checking analysis status...',
      detail: 'Fetching worker progress.',
      progress: null,
      isRunning: true,
    };
  }

  if (entry === null) {
    return {
      badge: 'Analysis status unavailable',
      detail: 'Could not fetch analysis status right now.',
      progress: null,
      isRunning: false,
    };
  }

  return summarizeSnapshotAnalyses(entry);
}

function parseFractionProgress(progressText) {
  if (typeof progressText !== 'string') return null;
  const match = progressText.match(/(\d+)\s*\/\s*(\d+)/);
  if (!match) return null;

  const completed = Number(match[1]);
  const total = Number(match[2]);
  if (!Number.isFinite(completed) || !Number.isFinite(total) || total <= 0) return null;

  const rawRatio = completed / total;
  const ratio = Math.max(0, Math.min(1, rawRatio));
  return {
    completed,
    total,
    ratio,
    percent: Math.round(ratio * 100),
  };
}

function Homepage() {
  const [themeMode, setThemeMode] = useState(() => localStorage.getItem('artifactMiner.themeMode') || 'light');
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_STORAGE_KEY) || '');
  const [currentUser, setCurrentUser] = useState(null);
  const [sessionLoading, setSessionLoading] = useState(true);
  const [authMode, setAuthMode] = useState('login');
  const [authBusy, setAuthBusy] = useState(false);
  const [authError, setAuthError] = useState('');

  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  const [registerDisplayName, setRegisterDisplayName] = useState('');
  const [registerEmail, setRegisterEmail] = useState('');
  const [registerPassword, setRegisterPassword] = useState('');
  const [registerConfirmPassword, setRegisterConfirmPassword] = useState('');

  const [view, setView] = useState('projects');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [dashboardError, setDashboardError] = useState('');
  const [flashMessage, setFlashMessage] = useState('');

  const [portfolioId, setPortfolioId] = useState(null);
  const [projects, setProjects] = useState([]);
  const [topProjects, setTopProjects] = useState([]);
  const [chronologicalSkills, setChronologicalSkills] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [projectReport, setProjectReport] = useState(null);
  const [projectSkills, setProjectSkills] = useState(null);
  const [contributors, setContributors] = useState([]);
  const [file, setFile] = useState(null);
  const [uploadProjectName, setUploadProjectName] = useState('');
  const [uploadMode, setUploadMode] = useState('new');
  const [uploadTargetProjectId, setUploadTargetProjectId] = useState('');
  const [snapshotLabel, setSnapshotLabel] = useState('');
  const [uploadTargetReport, setUploadTargetReport] = useState(null);
  const [uploadHistoryLoading, setUploadHistoryLoading] = useState(false);
  const [uploadHistoryError, setUploadHistoryError] = useState('');
  const [deletingProjectId, setDeletingProjectId] = useState(null);
  const [snapshotAnalyses, setSnapshotAnalyses] = useState({});
  const [projectRoleDraft, setProjectRoleDraft] = useState('');
  const [savingProjectRole, setSavingProjectRole] = useState(false);
  const [projectMetricsDraft, setProjectMetricsDraft] = useState([]);
  const [projectFeedbackDraft, setProjectFeedbackDraft] = useState([]);
  const [projectEvaluationDraft, setProjectEvaluationDraft] = useState([]);
  const [projectEvidenceError, setProjectEvidenceError] = useState('');
  const [savingProjectEvidence, setSavingProjectEvidence] = useState(false);
  const [userConfig, setUserConfig] = useState(null);
  const [configLoading, setConfigLoading] = useState(false);
  const [configSaving, setConfigSaving] = useState(false);
  const [rankingMode, setRankingMode] = useState('auto');
  const [rankingAllowNoUserScore, setRankingAllowNoUserScore] = useState(false);
  const [rankingUserWeight, setRankingUserWeight] = useState('1');
  const [rankingOtherWeight, setRankingOtherWeight] = useState('0.1');
  const [rankingContributorWeight, setRankingContributorWeight] = useState('0');
  const [rankingManualRanks, setRankingManualRanks] = useState({});
  const [chronologyProjectDates, setChronologyProjectDates] = useState({});
  const [comparisonAttributes, setComparisonAttributes] = useState([]);
  const [highlightSkillsInput, setHighlightSkillsInput] = useState('');
  const [showcaseProjectIds, setShowcaseProjectIds] = useState([]);
  const [compareSelectedProjectIds, setCompareSelectedProjectIds] = useState([]);
  const [compareResults, setCompareResults] = useState(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [activeResumeId, setActiveResumeId] = useState(null);
  const [resumeWording, setResumeWording] = useState({ summary_text: '', resume_bullets: [] });
  const [savingResume, setSavingResume] = useState(false);
  const [resumeSaveStatus, setResumeSaveStatus] = useState(''); // Renamed to avoid collision
  const [projectThumbnails, setProjectThumbnails] = useState({});
  const [thumbnailUploadFile, setThumbnailUploadFile] = useState(null);
  const [thumbnailActionProjectId, setThumbnailActionProjectId] = useState(null);
  const [thumbnailActionError, setThumbnailActionError] = useState('');
  const [selectedShowcase, setSelectedShowcase] = useState(null);
  const [showcaseDraft, setShowcaseDraft] = useState({ title: '', summary_text: '' });
  const [showcaseSaving, setShowcaseSaving] = useState(false);
  const [showcaseGenerating, setShowcaseGenerating] = useState(false);
  const [showcaseError, setShowcaseError] = useState('');
  const [dashboardMode, setDashboardMode] = useState('private');
  const [dashboardPublicSlug, setDashboardPublicSlug] = useState('');
  const [dashboardVisibilityConfig, setDashboardVisibilityConfig] = useState({
    projects: true,
    skills_timeline: true,
    top_projects: true,
    activity_heatmap: true,
    showcases: true,
  });
  const [dashboardVisibilitySaving, setDashboardVisibilitySaving] = useState(false);
  const [dashboardModeLoading, setDashboardModeLoading] = useState(false);
  const [dashboardModeActionBusy, setDashboardModeActionBusy] = useState(false);
  const [dashboardModeError, setDashboardModeError] = useState('');

  useEffect(() => {
    localStorage.setItem('artifactMiner.themeMode', themeMode);
  }, [themeMode]);

  const isAuthenticated = Boolean(token && currentUser);
  const currentUserId = currentUser?.user_id || null;

  const renderAnalysisProgress = useCallback((progressText) => {
    const parsed = parseFractionProgress(progressText);
    if (!parsed) {
      return <p className="muted">{progressText}</p>;
    }

    return (
      <div className="analysis-progress-wrap" aria-label={`Analysis progress ${parsed.completed} of ${parsed.total}`}>
        <div className="analysis-progress-track">
          <motion.div
            className="analysis-progress-fill"
            initial={{ width: 0 }}
            animate={{ width: `${parsed.percent}%` }}
            transition={{ duration: 0.35, ease: 'easeOut' }}
          />
        </div>
        <p className="analysis-progress-label muted">
          {parsed.completed}/{parsed.total} complete
        </p>
      </div>
    );
  }, []);

  const clearDashboardState = useCallback(() => {
    setPortfolioId(null);
    setProjects([]);
    setTopProjects([]);
    setChronologicalSkills([]);
    setSelectedProject(null);
    setProjectReport(null);
    setProjectSkills(null);
    setContributors([]);
    setFile(null);
    setUploadProjectName('');
    setUploadMode('new');
    setUploadTargetProjectId('');
    setSnapshotLabel('');
    setUploadTargetReport(null);
    setUploadHistoryLoading(false);
    setUploadHistoryError('');
    setSnapshotAnalyses({});
    setProjectRoleDraft('');
    setSavingProjectRole(false);
    setProjectMetricsDraft([]);
    setProjectFeedbackDraft([]);
    setProjectEvaluationDraft([]);
    setProjectEvidenceError('');
    setSavingProjectEvidence(false);
    setUserConfig(null);
    setConfigLoading(false);
    setConfigSaving(false);
    setRankingMode('auto');
    setRankingAllowNoUserScore(false);
    setRankingUserWeight('1');
    setRankingOtherWeight('0.1');
    setRankingContributorWeight('0');
    setRankingManualRanks({});
    setChronologyProjectDates({});
    setComparisonAttributes([]);
    setHighlightSkillsInput('');
    setShowcaseProjectIds([]);
    setCompareSelectedProjectIds([]);
    setCompareResults(null);
    setCompareLoading(false);
    setProjectThumbnails({});
    setThumbnailUploadFile(null);
    setThumbnailActionProjectId(null);
    setThumbnailActionError('');
    setSelectedShowcase(null);
    setShowcaseDraft({ title: '', summary_text: '' });
    setShowcaseSaving(false);
    setShowcaseGenerating(false);
    setShowcaseError('');
    setDashboardMode('private');
    setDashboardPublicSlug('');
    setDashboardVisibilityConfig({
      projects: true,
      skills_timeline: true,
      top_projects: true,
      activity_heatmap: true,
      showcases: true,
    });
    setDashboardVisibilitySaving(false);
    setDashboardModeLoading(false);
    setDashboardModeActionBusy(false);
    setDashboardModeError('');
    setView('projects');
  }, []);

  const clearSession = useCallback(() => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken('');
    setCurrentUser(null);
    setDashboardError('');
    setFlashMessage('');
    clearDashboardState();
  }, [clearDashboardState]);

  const hydrateEvidenceDrafts = useCallback((evidenceJson) => {
    const normalized = normalizeEvidenceSections(evidenceJson);
    setProjectMetricsDraft(buildObjectEvidenceDraftRows(normalized.metrics));
    setProjectFeedbackDraft(buildFeedbackDraftRows(normalized.feedback));
    setProjectEvaluationDraft(buildObjectEvidenceDraftRows(normalized.evaluation));
    setProjectEvidenceError('');
  }, []);

  useEffect(() => {
    let cancelled = false;
    const bootstrapSession = async () => {
      if (!token) {
        setSessionLoading(false);
        return;
      }
      try {
        const me = await authApi.me(token);
        if (!cancelled) {
          setCurrentUser(me.user || null);
        }
      } catch (error) {
        if (!cancelled) {
          clearSession();
          setAuthError('Your session expired. Please sign in again.');
        }
      } finally {
        if (!cancelled) {
          setSessionLoading(false);
        }
      }
    };
    bootstrapSession();
    return () => {
      cancelled = true;
    };
  }, [token, clearSession]);

  const fetchProjects = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setDashboardError('');
    try {
      const data = await projectApi.listProjects(token);
      setProjects(data.projects || []);
      setPortfolioId(data.portfolio_id || null);
    } catch (error) {
      setDashboardError(error.message || 'Unable to load projects.');
    } finally {
      setLoading(false);
    }
  }, [token]);

  const applyRepresentationConfig = useCallback((config) => {
    const ranking = config?.ranking || {};
    const rankingWeights = ranking?.weights || {};
    const chronology = config?.chronology || {};
    const comparison = config?.comparison || {};
    const highlights = config?.highlights || {};
    const showcase = config?.showcase || {};

    setRankingMode(typeof ranking.mode === 'string' ? ranking.mode : 'auto');
    setRankingAllowNoUserScore(Boolean(ranking.allow_no_user_score));
    setRankingUserWeight(String(rankingWeights.user_commits ?? 1));
    setRankingOtherWeight(String(rankingWeights.other_commits ?? 0.1));
    setRankingContributorWeight(String(rankingWeights.contributor_count ?? 0));
    setRankingManualRanks(
      Object.entries(ranking.manual_ranks || {}).reduce((acc, [projectId, rank]) => {
        const parsed = Number(rank);
        if (Number.isFinite(parsed)) {
          acc[projectId] = String(parsed);
        }
        return acc;
      }, {})
    );
    setChronologyProjectDates(
      Object.entries(chronology.project_dates || {}).reduce((acc, [projectId, value]) => {
        const text = String(value || '').trim();
        if (text) {
          acc[projectId] = text;
        }
        return acc;
      }, {})
    );
    setComparisonAttributes(
      Array.isArray(comparison.attributes)
        ? comparison.attributes.map((entry) => String(entry).trim()).filter((entry) => Boolean(entry))
        : []
    );
    setHighlightSkillsInput(
      Array.isArray(highlights.skills)
        ? highlights.skills.map((entry) => String(entry).trim()).filter((entry) => Boolean(entry)).join(', ')
        : ''
    );
    setShowcaseProjectIds(
      Array.isArray(showcase.selected_project_ids)
        ? showcase.selected_project_ids.map((entry) => String(entry).trim()).filter((entry) => Boolean(entry))
        : []
    );
  }, []);

  const fetchUserConfig = useCallback(async () => {
    if (!token || !currentUserId) return;
    setConfigLoading(true);
    try {
      const response = await userConfigApi.getConfig(token, currentUserId);
      const config = response?.config || {};
      setUserConfig(config);
      applyRepresentationConfig(config);
    } catch (error) {
      setDashboardError(error.message || 'Unable to load representation settings.');
    } finally {
      setConfigLoading(false);
    }
  }, [token, currentUserId, applyRepresentationConfig]);

  const fetchDashboardMode = useCallback(async () => {
    if (!token || !portfolioId) return;
    setDashboardModeLoading(true);
    setDashboardModeError('');
    try {
      const response = await dashboardApi.getMode(token, portfolioId);
      setDashboardMode(response?.mode || 'private');
      setDashboardPublicSlug(response?.public_slug || '');
      setDashboardVisibilityConfig({
        projects: Boolean(response?.visibility_config?.projects ?? true),
        skills_timeline: Boolean(response?.visibility_config?.skills_timeline ?? true),
        top_projects: Boolean(response?.visibility_config?.top_projects ?? true),
        activity_heatmap: Boolean(response?.visibility_config?.activity_heatmap ?? true),
        showcases: Boolean(response?.visibility_config?.showcases ?? true),
      });
    } catch (error) {
      setDashboardModeError(error.message || 'Unable to load dashboard mode.');
    } finally {
      setDashboardModeLoading(false);
    }
  }, [token, portfolioId]);

  const fetchTopProjects = useCallback(async () => {
    if (!token || !portfolioId) return;
    setLoading(true);
    setDashboardError('');
    try {
      const data = await projectApi.getPortfolioTopProjects(token, portfolioId, 5);
      setTopProjects(data.top_projects || []);
    } catch (error) {
      setDashboardError(error.message || 'Unable to load top projects.');
    } finally {
      setLoading(false);
    }
  }, [token, portfolioId]);

  const fetchChronologicalSkills = useCallback(async () => {
    if (!token || !portfolioId) return;
    setLoading(true);
    setDashboardError('');
    try {
      const data = await projectApi.getPortfolioSkillTimeline(token, portfolioId, 50);
      setChronologicalSkills(data.skill_events || []);
    } catch (error) {
      setDashboardError(error.message || 'Unable to load skills timeline.');
    } finally {
      setLoading(false);
    }
  }, [token, portfolioId]);

  const fetchUploadProjectHistory = useCallback(
    async (projectId) => {
      if (!token || !projectId) return null;
      return projectApi.getProjectReport(token, projectId);
    },
    [token]
  );

  useEffect(() => {
    if (!isAuthenticated) return;
    fetchProjects();
  }, [isAuthenticated, fetchProjects]);

  useEffect(() => {
    if (!isAuthenticated) return;
    fetchUserConfig();
  }, [isAuthenticated, fetchUserConfig]);

  useEffect(() => {
    if (!isAuthenticated || !portfolioId) return;
    fetchDashboardMode();
  }, [isAuthenticated, portfolioId, fetchDashboardMode]);

  useEffect(() => {
    if (!isAuthenticated) return;
    if (view === 'top') fetchTopProjects();
    if (view === 'skills') fetchChronologicalSkills();
  }, [view, isAuthenticated, fetchTopProjects, fetchChronologicalSkills]);

  useEffect(() => {
    if (uploadMode !== 'incremental') return;
    if (projects.length === 0) {
      setUploadTargetProjectId('');
      return;
    }
    if (!projects.some((project) => project.id === uploadTargetProjectId)) {
      setUploadTargetProjectId(projects[0].id);
    }
  }, [uploadMode, projects, uploadTargetProjectId]);

  useEffect(() => {
    if (projects.length === 0) {
      setCompareSelectedProjectIds([]);
      setCompareResults(null);
      return;
    }

    const projectIds = new Set(projects.map((project) => project.id));
    setCompareSelectedProjectIds((current) => current.filter((projectId) => projectIds.has(projectId)));
  }, [projects]);

  useEffect(() => {
    if (!token || view !== 'upload' || uploadMode !== 'incremental') {
      setUploadHistoryLoading(false);
      setUploadHistoryError('');
      if (uploadMode !== 'incremental') {
        setUploadTargetReport(null);
      }
      return;
    }
    if (!uploadTargetProjectId) {
      setUploadTargetReport(null);
      setUploadHistoryLoading(false);
      return;
    }

    let cancelled = false;

    const loadUploadHistory = async () => {
      setUploadHistoryLoading(true);
      setUploadHistoryError('');
      try {
        const report = await fetchUploadProjectHistory(uploadTargetProjectId);
        if (!cancelled) {
          setUploadTargetReport(report);
        }
      } catch (error) {
        if (!cancelled) {
          setUploadTargetReport(null);
          setUploadHistoryError(error.message || 'Unable to load snapshot history.');
        }
      } finally {
        if (!cancelled) {
          setUploadHistoryLoading(false);
        }
      }
    };

    loadUploadHistory();

    return () => {
      cancelled = true;
    };
  }, [token, view, uploadMode, uploadTargetProjectId, fetchUploadProjectHistory]);

  useEffect(() => {
    if (!token) {
      setSnapshotAnalyses({});
      return;
    }

    const snapshotIds = projects
      .map((project) => project.latest_snapshot?.id)
      .filter((snapshotId) => Boolean(snapshotId));

    if (snapshotIds.length === 0) {
      setSnapshotAnalyses({});
      return;
    }

    let cancelled = false;
    let timerId = null;

    const refreshAnalyses = async () => {
      const results = await Promise.allSettled(
        snapshotIds.map((snapshotId) => projectApi.getSnapshotAnalyses(token, snapshotId))
      );

      if (cancelled) return;

      let hasRunningAnalysis = false;
      const next = {};

      snapshotIds.forEach((snapshotId, index) => {
        const result = results[index];
        if (result.status === 'fulfilled') {
          const analyses = Array.isArray(result.value?.analyses) ? result.value.analyses : [];
          next[snapshotId] = analyses;
          if (analyses.some((entry) => ACTIVE_ANALYSIS_STATUSES.has(normalizeAnalysisStatus(entry?.status)))) {
            hasRunningAnalysis = true;
          }
        } else {
          next[snapshotId] = null;
        }
      });

      setSnapshotAnalyses(next);

      if (hasRunningAnalysis && !cancelled) {
        timerId = window.setTimeout(refreshAnalyses, ANALYSIS_POLL_INTERVAL_MS);
      }
    };

    refreshAnalyses();

    return () => {
      cancelled = true;
      if (timerId) {
        window.clearTimeout(timerId);
      }
    };
  }, [token, projects]);

  useEffect(() => {
    if (!token) {
      setProjectThumbnails({});
      return;
    }

    if (projects.length === 0) {
      setProjectThumbnails({});
      return;
    }

    let cancelled = false;
    const projectIds = new Set(projects.map((project) => project.id));

    setProjectThumbnails((previous) => {
      const next = {};
      projects.forEach((project) => {
        next[project.id] = {
          ...(previous[project.id] || {}),
          loading: true,
          error: '',
        };
      });
      return next;
    });

    const loadThumbnails = async () => {
      const results = await Promise.allSettled(
        projects.map((project) => projectApi.getProjectImage(token, project.id))
      );

      if (cancelled) return;

      setProjectThumbnails((previous) => {
        const next = {};

        projects.forEach((project, index) => {
          const result = results[index];
          if (result.status === 'fulfilled') {
            const payload = result.value || {};
            next[project.id] = {
              loading: false,
              hasImage: Boolean(payload.data_base64),
              imageUrl: formatProjectImageDataUrl(payload.mime_type, payload.data_base64),
              mimeType: payload.mime_type || 'image/png',
              thumbnailBlobSha256: payload.thumbnail_blob_sha256 || null,
              error: '',
            };
            return;
          }

          const reason = result.reason;
          if (reason?.status === 404) {
            next[project.id] = {
              loading: false,
              hasImage: false,
              imageUrl: '',
              mimeType: '',
              thumbnailBlobSha256: null,
              error: '',
            };
            return;
          }

          next[project.id] = {
            loading: false,
            hasImage: false,
            imageUrl: '',
            mimeType: '',
            thumbnailBlobSha256: null,
            error: reason?.message || 'Unable to load thumbnail.',
          };
        });

        Object.entries(previous).forEach(([projectId, value]) => {
          if (!projectIds.has(projectId)) return;
          if (!next[projectId]) {
            next[projectId] = value;
          }
        });

        return next;
      });
    };

    loadThumbnails();

    return () => {
      cancelled = true;
    };
  }, [token, projects]);

  const handleAuthSuccess = useCallback(
    (response) => {
      localStorage.setItem(TOKEN_STORAGE_KEY, response.token);
      setToken(response.token);
      setCurrentUser(response.user || null);
      setAuthError('');
      setFlashMessage('Signed in successfully.');
      clearDashboardState();
    },
    [clearDashboardState]
  );

  const handleLogin = async (event) => {
    event.preventDefault();
    setAuthBusy(true);
    setAuthError('');
    try {
      const response = await authApi.login({
        email: loginEmail,
        password: loginPassword,
      });
      handleAuthSuccess(response);
      setLoginPassword('');
    } catch (error) {
      setAuthError(error.message || 'Login failed.');
    } finally {
      setAuthBusy(false);
    }
  };

  const handleRegister = async (event) => {
    event.preventDefault();
    setAuthBusy(true);
    setAuthError('');
    if (registerPassword !== registerConfirmPassword) {
      setAuthBusy(false);
      setAuthError('Passwords do not match.');
      return;
    }
    try {
      const response = await authApi.register({
        email: registerEmail,
        password: registerPassword,
        displayName: registerDisplayName,
      });
      handleAuthSuccess(response);
      setRegisterPassword('');
      setRegisterConfirmPassword('');
    } catch (error) {
      setAuthError(error.message || 'Registration failed.');
    } finally {
      setAuthBusy(false);
    }
  };

  const handleLogout = async () => {
    if (!token) return;
    try {
      await authApi.logout(token);
    } catch (error) {
      // Ignore logout API failures and clear local session anyway.
    } finally {
      clearSession();
    }
  };

  const makeDashboardPublic = async () => {
    if (!token || !portfolioId) return;
    setDashboardModeActionBusy(true);
    setDashboardModeError('');
    try {
      const response = await dashboardApi.publish(token, portfolioId);
      setDashboardMode(response?.mode || 'private');
      setDashboardPublicSlug(response?.public_slug || '');
      setFlashMessage('Portfolio is now public.');
    } catch (error) {
      setDashboardModeError(error.message || 'Unable to make portfolio public.');
    } finally {
      setDashboardModeActionBusy(false);
    }
  };

  const makeDashboardPrivate = async () => {
    if (!token || !portfolioId) return;
    setDashboardModeActionBusy(true);
    setDashboardModeError('');
    try {
      const response = await dashboardApi.unpublish(token, portfolioId);
      setDashboardMode(response?.mode || 'private');
      setDashboardPublicSlug(response?.public_slug || '');
      setFlashMessage('Portfolio is now private.');
    } catch (error) {
      setDashboardModeError(error.message || 'Unable to make portfolio private.');
    } finally {
      setDashboardModeActionBusy(false);
    }
  };

  const regenerateDashboardLink = async () => {
    if (!token || !portfolioId) return;
    setDashboardModeActionBusy(true);
    setDashboardModeError('');
    try {
      const response = await dashboardApi.regeneratePublicLink(token, portfolioId);
      setDashboardMode(response?.mode || 'private');
      setDashboardPublicSlug(response?.public_slug || '');
      setFlashMessage('Public link regenerated.');
    } catch (error) {
      setDashboardModeError(error.message || 'Unable to regenerate public link.');
    } finally {
      setDashboardModeActionBusy(false);
    }
  };

  const copyLastGeneratedLink = async () => {
    if (!dashboardPublicSlug) return;
    const url = `${window.location.origin}/portfolio/${dashboardPublicSlug}`;
    try {
      await navigator.clipboard.writeText(url);
      setFlashMessage('Public URL copied to clipboard.');
    } catch (error) {
      setDashboardModeError('Unable to copy link. Copy it manually from the URL shown below.');
    }
  };

  const handleDashboardVisibilityToggle = (key) => {
    setDashboardVisibilityConfig((current) => ({
      ...current,
      [key]: !Boolean(current[key]),
    }));
  };

  const saveDashboardVisibility = async () => {
    if (!token || !portfolioId) return;
    setDashboardVisibilitySaving(true);
    setDashboardModeError('');
    try {
      const response = await dashboardApi.setVisibility(token, portfolioId, dashboardVisibilityConfig);
      setDashboardVisibilityConfig({
        projects: Boolean(response?.visibility_config?.projects ?? true),
        skills_timeline: Boolean(response?.visibility_config?.skills_timeline ?? true),
        top_projects: Boolean(response?.visibility_config?.top_projects ?? true),
        activity_heatmap: Boolean(response?.visibility_config?.activity_heatmap ?? true),
        showcases: Boolean(response?.visibility_config?.showcases ?? true),
      });
      setFlashMessage('Public section visibility saved.');
    } catch (error) {
      setDashboardModeError(error.message || 'Unable to save public section visibility.');
    } finally {
      setDashboardVisibilitySaving(false);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    if (uploadMode === 'incremental' && !uploadTargetProjectId) {
      setDashboardError('Select an existing project for incremental upload.');
      return;
    }

    const selectedUploadProject = projects.find((project) => project.id === uploadTargetProjectId) || null;
    const normalizedUploadName = uploadProjectName.trim() || normalizeProjectName(file.name);
    const targetProjectName = uploadMode === 'incremental' ? selectedUploadProject?.name || '' : normalizedUploadName;

    if (!targetProjectName) {
      setDashboardError('Provide a project name before uploading.');
      return;
    }

    if (uploadMode === 'new') {
      const duplicateProject = projects.find(
        (project) => (project.name || '').trim().toLowerCase() === targetProjectName.trim().toLowerCase()
      );
      if (duplicateProject) {
        setDashboardError(
          `Project "${duplicateProject.name}" already exists. Switch to Incremental update to add another snapshot.`
        );
        return;
      }
    }

    setUploading(true);
    setDashboardError('');
    setFlashMessage('');
    try {
      const consentAccepted = window.confirm(
        'Privacy notice: external analysis sends project data to an external language model service. Click OK to consent (uses both local and external analysis), or Cancel to continue with local-only analysis.'
      );

      await authApi.submitPrivacyConsent(token, {
        userId: currentUser?.user_id,
        consentType: 'external_services',
        granted: consentAccepted,
      });

      const uploadResponse = await projectApi.uploadProject(token, {
        file,
        projectName: targetProjectName,
        snapshotLabel: snapshotLabel.trim() || undefined,
        analysisMode: consentAccepted ? 'both' : 'local',
      });
      setFile(null);
      if (uploadMode === 'new') {
        setUploadProjectName('');
      }
      setSnapshotLabel('');
      await fetchProjects();

      const createdCount = Array.isArray(uploadResponse?.created) ? uploadResponse.created.length : 0;
      const skippedCount = Array.isArray(uploadResponse?.skipped) ? uploadResponse.skipped.length : 0;

      if (uploadMode === 'incremental') {
        let refreshedReport = null;
        try {
          refreshedReport = await fetchUploadProjectHistory(uploadTargetProjectId);
          setUploadTargetReport(refreshedReport);
          setUploadHistoryError('');
        } catch (historyError) {
          setUploadHistoryError(historyError.message || 'Unable to refresh snapshot history.');
        }

        const snapshotTotal = Array.isArray(refreshedReport?.snapshots) ? refreshedReport.snapshots.length : null;
        if (createdCount > 0) {
          const snapshotSuffix =
            snapshotTotal == null ? '' : ` ${snapshotTotal} snapshot${snapshotTotal === 1 ? '' : 's'} now recorded.`;
          setFlashMessage(
            `Incremental upload complete for "${targetProjectName}". Files were merged into the existing project.${snapshotSuffix}`
          );
        } else if (skippedCount > 0) {
          setFlashMessage(
            `No new snapshot was created for "${targetProjectName}" because this ZIP already exists in that project's history.`
          );
        } else {
          setFlashMessage(`Upload finished for "${targetProjectName}".`);
        }
        setView('upload');
      } else {
        setFlashMessage('Project uploaded. Analysis has started and status will update in Your Projects.');
        setView('projects');
      }
    } catch (error) {
      setDashboardError(error.message || 'Upload failed.');
    } finally {
      setUploading(false);
    }
  };

  const fetchShowcaseForProject = async (projectId) => {
    if (!token || !portfolioId) return;
    setShowcaseError('');
    try {
      const data = await projectApi.listPortfolioShowcases(token, portfolioId);
      const items = data.items || [];
      const match = items.find((item) => item.project_id === projectId) || null;
      setSelectedShowcase(match);
      setShowcaseDraft({
        title: match?.content?.title ?? '',
        summary_text: match?.content?.summary_text ?? '',
      });
    } catch (error) {
      setShowcaseError(error.message || 'Unable to load showcase.');
    }
  };

  const viewProjectDetails = async (project) => {
    setActiveResumeId(null);
    setResumeWording({ summary_text: '', resume_bullets: [] });
    setResumeSaveStatus('');
    if (!token) return;
    setSelectedProject(project);
    setView('report');
    setProjectReport(null);
    setProjectSkills(null);
    setContributors([]);
    setProjectRoleDraft(project?.user_role || '');
    setThumbnailUploadFile(null);
    setThumbnailActionError('');
    setThumbnailActionProjectId(null);
    setSavingProjectRole(false);
    setProjectEvidenceError('');
    setSavingProjectEvidence(false);
    hydrateEvidenceDrafts(project?.evidence_json || {});
    setSelectedShowcase(null);
    setShowcaseDraft({ title: '', summary_text: '' });
    setShowcaseError('');
    setLoading(true);
    setDashboardError('');
    try {
      const [reportResponse, contributorsResponse] = await Promise.all([
        projectApi.getProjectReport(token, project.id),
        projectApi.getProjectContributors(token, project.id),
      ]);
      setProjectReport(reportResponse);
      setProjectRoleDraft(reportResponse?.project?.user_role || '');
      hydrateEvidenceDrafts(reportResponse?.project?.evidence_json || {});
      setContributors(contributorsResponse.contributors || []);

      const snapshotId = project.latest_snapshot?.id;
      if (snapshotId) {
        const skillsResponse = await projectApi.getSnapshotSkills(token, snapshotId, 20);
        setProjectSkills(skillsResponse);
      }
      fetchShowcaseForProject(project.id);

      // Load existing resume if one has been generated for this project
      try {
        const resumeResponse = await projectApi.getLatestResume(token, project.id);
        if (resumeResponse.resume_id) {
          setActiveResumeId(resumeResponse.resume_id);
          setResumeWording({
            summary_text: resumeResponse.content?.summary_text || '',
            resume_bullets: resumeResponse.content?.resume_bullets || [],
          });
        }
      } catch (resumeError) {
        if (resumeError.status !== 404) {
          console.error('Unexpected error fetching latest resume:', resumeError);
        }
      }
    } catch (error) {
      setDashboardError(error.message || 'Unable to load project details.');
    } finally {
      setLoading(false);
    }
  };

  const generateShowcase = async () => {
    if (!token || !selectedProject) return;
    setShowcaseGenerating(true);
    setShowcaseError('');
    try {
      const result = await projectApi.generateProjectShowcase(token, selectedProject.id);
      const newShowcase = {
        id: result.showcase_id,
        project_id: result.project_id,
        project_name: result.project_name,
        content: result.content,
      };
      setSelectedShowcase(newShowcase);
      setShowcaseDraft({
        title: result.content?.title ?? '',
        summary_text: result.content?.summary_text ?? '',
      });
      setFlashMessage('Portfolio showcase generated.');
    } catch (error) {
      setShowcaseError(error.message || 'Failed to generate showcase.');
    } finally {
      setShowcaseGenerating(false);
    }
  };

  const saveShowcase = async () => {
    if (!token || !selectedShowcase) return;
    setShowcaseSaving(true);
    setShowcaseError('');
    try {
      const updated = await projectApi.editPortfolioShowcase(token, selectedShowcase.id, {
        title: showcaseDraft.title,
        summary_text: showcaseDraft.summary_text,
      });
      setSelectedShowcase((prev) => ({ ...prev, content: updated.content }));
      setFlashMessage('Showcase wording saved.');
    } catch (error) {
      setShowcaseError(error.message || 'Failed to save showcase.');
    } finally {
      setShowcaseSaving(false);
    }
  };
  const handleGenerateResume = async () => {
    if (!selectedProject || !token) return;
    setLoading(true);
    try {
      // 1. Call the generate endpoint
      const response = await projectApi.generateResume(token, selectedProject.id);
      
      // 2. Capture the resume_id from the backend response
      if (response.resume_id) {
        setActiveResumeId(response.resume_id); 
        setResumeWording({
          summary_text: response.content?.summary_text || '',
          resume_bullets: response.content?.resume_bullets || []
        });
        setResumeSaveStatus("Resume generated!");
      }
    } catch (err) {
      console.error("Generation failed:", err);
      setDashboardError("Generation failed: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const saveResumeWording = async () => {
    if (!activeResumeId || !token) {
      setDashboardError("Cannot save: No active resume ID found.");
      return;
    }

    setSavingResume(true);
    setResumeSaveStatus(''); 
    try {
      // 3. Send the updated wording to the specific captured ID
      await projectApi.updateResumeItems(token, activeResumeId, {
        summary_text: resumeWording.summary_text,
        resume_bullets: resumeWording.resume_bullets,
      });
      setResumeSaveStatus('Saved successfully!');
    } catch (error) {
      console.error("Save failed:", error);
      setDashboardError('Save failed: ' + error.message);
    } finally {
      setSavingResume(false);
    }
  };

  const saveProjectRole = async () => {
    if (!token || !selectedProject) return;

    const projectId = selectedProject.id;
    const nextRole = projectRoleDraft.trim();
    const currentRole = (projectReport?.project?.user_role || '').trim();

    if (nextRole === currentRole) return;

    setSavingProjectRole(true);
    setDashboardError('');
    setFlashMessage('');

    try {
      const response = await projectApi.updateProject(token, projectId, {
        userRole: nextRole || null,
      });
      const persistedRole = response?.user_role || '';

      setProjectRoleDraft(persistedRole);
      setSelectedProject((previous) =>
        previous ? { ...previous, user_role: persistedRole || null } : previous
      );
      setProjects((previous) =>
        previous.map((project) =>
          project.id === projectId ? { ...project, user_role: persistedRole || null } : project
        )
      );
      setProjectReport((previous) => {
        if (!previous) return previous;
        return {
          ...previous,
          project: {
            ...(previous.project || {}),
            user_role: persistedRole || null,
          },
        };
      });
      setFlashMessage(persistedRole ? 'Project role saved.' : 'Project role cleared.');
    } catch (error) {
      setDashboardError(error.message || 'Unable to save project role.');
    } finally {
      setSavingProjectRole(false);
    }
  };

  const addProjectMetricRow = () => {
    setProjectEvidenceError('');
    setProjectMetricsDraft((previous) => [...previous, { id: createDraftId(), key: '', value: '' }]);
  };

  const addProjectFeedbackRow = () => {
    setProjectEvidenceError('');
    setProjectFeedbackDraft((previous) => [...previous, { id: createDraftId(), source: '', note: '' }]);
  };

  const addProjectEvaluationRow = () => {
    setProjectEvidenceError('');
    setProjectEvaluationDraft((previous) => [...previous, { id: createDraftId(), key: '', value: '' }]);
  };

  const saveProjectEvidence = async () => {
    if (!token || !selectedProject) return;

    const metricsPayload = buildObjectEvidencePayload(projectMetricsDraft, 'Metrics');
    if (!metricsPayload.ok) {
      setProjectEvidenceError(metricsPayload.error);
      return;
    }

    const feedbackPayload = buildFeedbackEvidencePayload(projectFeedbackDraft);
    if (!feedbackPayload.ok) {
      setProjectEvidenceError(feedbackPayload.error);
      return;
    }

    const evaluationPayload = buildObjectEvidencePayload(projectEvaluationDraft, 'Evaluation');
    if (!evaluationPayload.ok) {
      setProjectEvidenceError(evaluationPayload.error);
      return;
    }

    const projectId = selectedProject.id;

    setSavingProjectEvidence(true);
    setProjectEvidenceError('');
    setDashboardError('');
    setFlashMessage('');

    try {
      const response = await projectApi.updateProject(token, projectId, {
        metrics: metricsPayload.value,
        feedback: feedbackPayload.value,
        evaluation: evaluationPayload.value,
      });

      const persistedEvidence = normalizeEvidenceSections(response?.evidence_json || {});

      setSelectedProject((previous) =>
        previous
          ? {
              ...previous,
              evidence_json: {
                metrics: persistedEvidence.metrics,
                feedback: persistedEvidence.feedback,
                evaluation: persistedEvidence.evaluation,
              },
            }
          : previous
      );
      setProjects((previous) =>
        previous.map((project) =>
          project.id === projectId
            ? {
                ...project,
                evidence_json: {
                  metrics: persistedEvidence.metrics,
                  feedback: persistedEvidence.feedback,
                  evaluation: persistedEvidence.evaluation,
                },
              }
            : project
        )
      );
      setProjectReport((previous) => {
        if (!previous) return previous;
        return {
          ...previous,
          project: {
            ...(previous.project || {}),
            evidence_json: {
              metrics: persistedEvidence.metrics,
              feedback: persistedEvidence.feedback,
              evaluation: persistedEvidence.evaluation,
            },
          },
        };
      });

      hydrateEvidenceDrafts({
        metrics: persistedEvidence.metrics,
        feedback: persistedEvidence.feedback,
        evaluation: persistedEvidence.evaluation,
      });
      setFlashMessage('Evidence of success saved.');
    } catch (error) {
      setProjectEvidenceError(error.message || 'Unable to save evidence of success.');
    } finally {
      setSavingProjectEvidence(false);
    }
  };

  const generateResume = async (projectId) => {
    if (!token) return;
    setLoading(true);
    setDashboardError('');
    try {
      const response = await projectApi.generateResume(token, projectId);
      setFlashMessage(`Resume generated: ${response.resume_id}`);
      window.open(`${API_BASE_URL}/resume/${response.resume_id}/pdf`, '_blank', 'noopener,noreferrer');
    } catch (error) {
      setDashboardError(error.message || 'Resume generation failed.');
    } finally {
      setLoading(false);
    }
  };

  const saveRepresentationPreferences = async () => {
    if (!token || !currentUser?.user_id) return;

    const projectIds = new Set(projects.map((project) => project.id));
    const parsedManualRanks = Object.entries(rankingManualRanks).reduce((acc, [projectId, rankValue]) => {
      if (!projectIds.has(projectId)) return acc;
      const parsed = Number(rankValue);
      if (Number.isFinite(parsed)) {
        acc[projectId] = parsed;
      }
      return acc;
    }, {});

    const parsedProjectDates = Object.entries(chronologyProjectDates).reduce((acc, [projectId, dateValue]) => {
      if (!projectIds.has(projectId)) return acc;
      const normalized = String(dateValue || '').trim();
      if (normalized) {
        acc[projectId] = normalized;
      }
      return acc;
    }, {});

    const normalizedComparisonAttributes = comparisonAttributes
      .map((entry) => String(entry).trim())
      .filter((entry) => Boolean(entry));

    const normalizedShowcase = showcaseProjectIds.filter((projectId) => projectIds.has(projectId));
    const normalizedHighlights = toCsvList(highlightSkillsInput);
    const parsedUserWeight = Number(rankingUserWeight);
    const parsedOtherWeight = Number(rankingOtherWeight);
    const parsedContributorWeight = Number(rankingContributorWeight);

    const patch = {
      ranking: {
        mode: rankingMode,
        allow_no_user_score: Boolean(rankingAllowNoUserScore),
        weights: {
          user_commits: Number.isFinite(parsedUserWeight) ? parsedUserWeight : 1,
          other_commits: Number.isFinite(parsedOtherWeight) ? parsedOtherWeight : 0.1,
          contributor_count: Number.isFinite(parsedContributorWeight) ? parsedContributorWeight : 0,
        },
        manual_ranks: parsedManualRanks,
      },
      chronology: {
        project_dates: parsedProjectDates,
      },
      comparison: {
        attributes: normalizedComparisonAttributes,
      },
      highlights: {
        skills: normalizedHighlights,
      },
      showcase: {
        selected_project_ids: normalizedShowcase,
      },
    };

    setConfigSaving(true);
    setDashboardError('');
    setFlashMessage('');

    try {
      const response = await userConfigApi.patchConfig(token, currentUser.user_id, patch);
      const config = response?.config || {};
      setUserConfig(config);
      applyRepresentationConfig(config);
      setFlashMessage('Representation preferences saved. New generations will use these selections.');
      await fetchProjects();
      if (view === 'top') {
        await fetchTopProjects();
      }
      if (view === 'skills') {
        await fetchChronologicalSkills();
      }
    } catch (error) {
      setDashboardError(error.message || 'Unable to save representation preferences.');
    } finally {
      setConfigSaving(false);
    }
  };

  const runProjectComparison = async () => {
    if (!token) return;
    if (compareSelectedProjectIds.length === 0) {
      setDashboardError('Select at least one project to compare.');
      return;
    }

    setCompareLoading(true);
    setDashboardError('');
    setFlashMessage('');

    try {
      const response = await projectApi.compareProjects(token, {
        projectIds: compareSelectedProjectIds,
        attributes: [],
      });
      setCompareResults(response);
      setFlashMessage('Comparison updated using your saved comparison attributes.');
    } catch (error) {
      setDashboardError(error.message || 'Unable to compare projects.');
    } finally {
      setCompareLoading(false);
    }
  };

  const deleteProject = async (project) => {
    if (!token) return;

    const confirmed = window.confirm(
      `Delete project "${project.name}"? This will permanently remove it from your account.`
    );
    if (!confirmed) return;

    setDeletingProjectId(project.id);
    setDashboardError('');
    setFlashMessage('');

    try {
      await projectApi.deleteProject(token, project.id);
      setFlashMessage('Project deleted successfully.');
      await fetchProjects();
    } catch (error) {
      setDashboardError(error.message || 'Project deletion failed.');
    } finally {
      setDeletingProjectId(null);
    }
  };

  const refreshProjectThumbnail = useCallback(
    async (projectId) => {
      if (!token || !projectId) return;

      setProjectThumbnails((previous) => ({
        ...previous,
        [projectId]: {
          ...(previous[projectId] || {}),
          loading: true,
          error: '',
        },
      }));

      try {
        const payload = await projectApi.getProjectImage(token, projectId);
        setProjectThumbnails((previous) => ({
          ...previous,
          [projectId]: {
            loading: false,
            hasImage: Boolean(payload?.data_base64),
            imageUrl: formatProjectImageDataUrl(payload?.mime_type, payload?.data_base64),
            mimeType: payload?.mime_type || 'image/png',
            thumbnailBlobSha256: payload?.thumbnail_blob_sha256 || null,
            error: '',
          },
        }));
      } catch (error) {
        if (error?.status === 404) {
          setProjectThumbnails((previous) => ({
            ...previous,
            [projectId]: {
              loading: false,
              hasImage: false,
              imageUrl: '',
              mimeType: '',
              thumbnailBlobSha256: null,
              error: '',
            },
          }));
          return;
        }

        setProjectThumbnails((previous) => ({
          ...previous,
          [projectId]: {
            loading: false,
            hasImage: false,
            imageUrl: '',
            mimeType: '',
            thumbnailBlobSha256: null,
            error: error?.message || 'Unable to load thumbnail.',
          },
        }));
      }
    },
    [token]
  );

  const saveProjectThumbnail = async () => {
    if (!token || !selectedProject) return;
    if (!thumbnailUploadFile) {
      setThumbnailActionError('Choose an image file before uploading.');
      return;
    }

    const projectId = selectedProject.id;
    setThumbnailActionProjectId(projectId);
    setThumbnailActionError('');
    setDashboardError('');
    setFlashMessage('');

    try {
      await projectApi.uploadProjectImage(token, projectId, thumbnailUploadFile);
      await refreshProjectThumbnail(projectId);
      setThumbnailUploadFile(null);
      setFlashMessage('Project thumbnail saved.');
    } catch (error) {
      setThumbnailActionError(error.message || 'Unable to save project thumbnail.');
    } finally {
      setThumbnailActionProjectId(null);
    }
  };

  const removeProjectThumbnail = async () => {
    if (!token || !selectedProject) return;
    const projectId = selectedProject.id;

    const confirmed = window.confirm('Remove this project thumbnail?');
    if (!confirmed) return;

    setThumbnailActionProjectId(projectId);
    setThumbnailActionError('');
    setDashboardError('');
    setFlashMessage('');

    try {
      await projectApi.deleteProjectImage(token, projectId);
      await refreshProjectThumbnail(projectId);
      setThumbnailUploadFile(null);
      setFlashMessage('Project thumbnail removed.');
    } catch (error) {
      setThumbnailActionError(error.message || 'Unable to remove project thumbnail.');
    } finally {
      setThumbnailActionProjectId(null);
    }
  };

  // ---------------------------------------------------------------------------
  // Resume tab state
  // ---------------------------------------------------------------------------
  const [resumeEducation, setResumeEducation] = useState([]);
  const [resumeAwards, setResumeAwards] = useState([]);
  const [resumeProjects, setResumeProjects] = useState([]);
  const [resumeLoading, setResumeLoading] = useState(false);
  const [resumeSaving, setResumeSaving] = useState(false);
  const [editingEduId, setEditingEduId] = useState(null);
  const [editingAwardId, setEditingAwardId] = useState(null);
  const [eduForm, setEduForm] = useState({});
  const [awardForm, setAwardForm] = useState({});
  const [eduTouched, setEduTouched] = useState({ start_year: false, end_year: false });
  const [awardTouched, setAwardTouched] = useState({ year: false });

  const EMPTY_EDU = { institution: '', degree: '', field_of_study: '', start_year: '', end_year: '', is_current: false, description: '' };
  const EMPTY_AWARD = { title: '', issuer: '', awarded_year: '', description: '' };

  const fetchResumePayload = useCallback(async () => {
    if (!token || !currentUser?.user_id) return;
    setResumeLoading(true);
    try {
      const data = await resumeApi.getResumePayload(token, currentUser.user_id);
      setResumeEducation(data.education || []);
      setResumeAwards(data.awards || []);
      setResumeProjects(data.projects || []);
    } catch (err) {
      setDashboardError(err.message || 'Unable to load resume data.');
    } finally {
      setResumeLoading(false);
    }
  }, [token, currentUser]);

  useEffect(() => {
    if (view === 'resume') fetchResumePayload();
  }, [view, fetchResumePayload]);

  const startAddEdu = () => { setEduForm(EMPTY_EDU); setEditingEduId('new'); setEduTouched({}); };
  const startEditEdu = (entry) => { setEduForm({ ...entry, start_year: entry.start_year || '', end_year: entry.end_year || '' }); setEditingEduId(entry.id); setEduTouched({}); };
  const cancelEdu = () => {setEditingEduId(null); setEduTouched({});};

  const saveEdu = async () => {
    setResumeSaving(true);
    try {
      const body = {
        institution: eduForm.institution,
        degree: eduForm.degree || null,
        field_of_study: eduForm.field_of_study || null,
        start_year: eduForm.start_year ? parseInt(eduForm.start_year, 10) : null,
        end_year: eduForm.is_current ? null : (eduForm.end_year ? parseInt(eduForm.end_year, 10) : null),
        is_current: eduForm.is_current || false,
        description: eduForm.description || null,
      };
      if (editingEduId === 'new') {
        await resumeApi.createEducation(token, currentUser.user_id, body);
      } else {
        await resumeApi.updateEducation(token, currentUser.user_id, editingEduId, body);
      }
      setEditingEduId(null);
      await fetchResumePayload();
      setEduTouched({});
    } catch (err) {
      setDashboardError(err.message || 'Failed to save education entry.');
    } finally {
      setResumeSaving(false);
    }
  };

  const deleteEdu = async (id) => {
    if (!window.confirm('Delete this education entry?')) return;
    setResumeSaving(true);
    try {
      await resumeApi.deleteEducation(token, currentUser.user_id, id);
      await fetchResumePayload();
    } catch (err) {
      setDashboardError(err.message || 'Failed to delete.');
    } finally {
      setResumeSaving(false);
    }
  };

  const startAddAward = () => { setAwardForm(EMPTY_AWARD); setEditingAwardId('new'); setAwardTouched({}); };
  const startEditAward = (entry) => { setAwardForm({ ...entry, awarded_year: entry.awarded_year || '' }); setEditingAwardId(entry.id); setAwardTouched({}); };
  const cancelAward = () => {setEditingAwardId(null); setAwardTouched({})};

  const saveAward = async () => {
    setResumeSaving(true);
    try {
      const body = {
        title: awardForm.title,
        issuer: awardForm.issuer || null,
        awarded_year: awardForm.awarded_year ? parseInt(awardForm.awarded_year, 10) : null,
        description: awardForm.description || null,
      };
      if (editingAwardId === 'new') {
        await resumeApi.createAward(token, currentUser.user_id, body);
      } else {
        await resumeApi.updateAward(token, currentUser.user_id, editingAwardId, body);
      }
      setEditingAwardId(null);
      await fetchResumePayload();
      setAwardTouched({});
    } catch (err) {
      setDashboardError(err.message || 'Failed to save award.');
    } finally {
      setResumeSaving(false);
    }
  };

  const deleteAward = async (id) => {
    if (!window.confirm('Delete this award?')) return;
    setResumeSaving(true);
    try {
      await resumeApi.deleteAward(token, currentUser.user_id, id);
      await fetchResumePayload();
    } catch (err) {
      setDashboardError(err.message || 'Failed to delete.');
    } finally {
      setResumeSaving(false);
    }
  };

  const navButtons = useMemo(
    () => [
      { id: 'projects', label: 'Projects' },
      { id: 'dashboardMode', label: 'Dashboard Mode' },
      { id: 'preferences', label: 'Preferences' },
      { id: 'compare', label: 'Compare' },
      { id: 'upload', label: 'Upload' },
      { id: 'skills', label: 'Skills Timeline' },
      { id: 'top', label: 'Top Projects' },
      { id: 'resume', label: 'Resume' },
    ],
    []
  );

  const reportStats = useMemo(() => {
    const toNumber = (value) => {
      if (value === null || value === undefined) return null;
      if (typeof value === 'number' && Number.isFinite(value)) return value;
      if (typeof value === 'string') {
        const normalized = value.replace(/[^0-9.-]/g, '');
        if (!normalized) return null;
        const parsed = Number(normalized);
        return Number.isFinite(parsed) ? parsed : null;
      }
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : null;
    };

    if (!projectReport) {
      return {
        totalFiles: 0,
        totalLines: 0,
        languageCount: 0,
        topLanguages: [],
      };
    }

    const snapshots = Array.isArray(projectReport.snapshots) ? projectReport.snapshots : [];
    const latestSnapshot = snapshots[snapshots.length - 1] || null;
    const parser = latestSnapshot?.analyses?.parser || {};
    const parserTotals = parser?.totals || {};
    const summary = projectReport.summary || {};

    const totalFilesRaw =
      summary.total_files ??
      summary.files ??
      parserTotals.total_files ??
      parserTotals.files ??
      0;

    const totalLinesRaw =
      summary.total_lines ??
      summary.totalLines ??
      summary.lines ??
      summary.line_count ??
      summary.lineCount ??
      summary.loc ??
      summary.sloc ??
      parserTotals.total_lines ??
      parserTotals.totalLines ??
      parserTotals.lines ??
      parserTotals.line_count ??
      parserTotals.lineCount ??
      parserTotals.loc ??
      parserTotals.sloc ??
      0;

    const inferredLanguageCountRaw =
      summary.language_count ??
      summary.languages ??
      summary.total_languages ??
      parserTotals.language_count ??
      (parser?.language_counts ? Object.keys(parser.language_counts).length : undefined) ??
      0;

    const topLanguages =
      (Array.isArray(projectReport.top_languages) && projectReport.top_languages) ||
      (Array.isArray(parser?.top_languages) && parser.top_languages) ||
      [];

    return {
      totalFiles: toNumber(totalFilesRaw) ?? 0,
      totalLines: toNumber(totalLinesRaw) ?? 0,
      languageCount: toNumber(inferredLanguageCountRaw) ?? 0,
      topLanguages,
    };
  }, [projectReport]);

  const selectedProjectStatus = useMemo(() => {
    if (!selectedProject) return null;
    return getSnapshotStatus(selectedProject.latest_snapshot?.id, snapshotAnalyses);
  }, [selectedProject, snapshotAnalyses]);

  const selectedProjectThumbnail = useMemo(() => {
    if (!selectedProject) return null;
    return projectThumbnails[selectedProject.id] || null;
  }, [selectedProject, projectThumbnails]);

  const savedProjectRole = (projectReport?.project?.user_role || '').trim();
  const projectRoleChanged = projectRoleDraft.trim() !== savedProjectRole;

  const showcaseChanged =
    showcaseDraft.title !== (selectedShowcase?.content?.title ?? '') ||
    showcaseDraft.summary_text !== (selectedShowcase?.content?.summary_text ?? '');

  const selectedUploadProject = useMemo(
    () => projects.find((project) => project.id === uploadTargetProjectId) || null,
    [projects, uploadTargetProjectId]
  );

  const publicPortfolioUrl = useMemo(() => {
    if (!dashboardPublicSlug) return '';
    return `${window.location.origin}/portfolio/${dashboardPublicSlug}`;
  }, [dashboardPublicSlug]);

  const uploadSnapshotHistory = useMemo(() => {
    const snapshots = Array.isArray(uploadTargetReport?.snapshots) ? uploadTargetReport.snapshots : [];
    const getTimestamp = (value) => {
      const parsed = new Date(value);
      const timestamp = parsed.getTime();
      return Number.isFinite(timestamp) ? timestamp : 0;
    };

    return snapshots
      .map((entry) => entry?.snapshot)
      .filter((snapshot) => Boolean(snapshot?.id))
      .sort((left, right) => getTimestamp(right.ingested_at) - getTimestamp(left.ingested_at));
  }, [uploadTargetReport]);

  const projectDateInputValue = useCallback((value) => {
    if (!value) return '';
    const asText = String(value).trim();
    if (!asText) return '';
    return asText.length >= 10 ? asText.slice(0, 10) : asText;
  }, []);

  if (sessionLoading) {
    return (
      <div className="screen-shell">
        <div className="loading-card">Restoring your session...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="screen-shell">
        <div className="auth-layout">
          <section className="auth-hero">
            <p className="eyebrow">Artifact Miner</p>
            <h1>Project portfolio intelligence built around real ownership.</h1>
            <p>
              Sign in to manage your own project snapshots, timelines, and generated resume artifacts without relying on
              hardcoded test identities.
            </p>
          </section>
          <section className="auth-panel">
            <div className="auth-toggle">
              <button
                className={authMode === 'login' ? 'tab active' : 'tab'}
                type="button"
                onClick={() => setAuthMode('login')}
              >
                Log In
              </button>
              <button
                className={authMode === 'register' ? 'tab active' : 'tab'}
                type="button"
                onClick={() => setAuthMode('register')}
              >
                Create Account
              </button>
            </div>

            {authMode === 'login' ? (
              <form className="auth-form" onSubmit={handleLogin}>
                <label>
                  Email
                  <input
                    type="email"
                    value={loginEmail}
                    onChange={(e) => setLoginEmail(e.target.value)}
                    required
                  />
                </label>
                <label>
                  Password
                  <input
                    type="password"
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    required
                  />
                </label>
                <button className="primary-btn" type="submit" disabled={authBusy}>
                  {authBusy ? 'Signing in...' : 'Sign In'}
                </button>
              </form>
            ) : (
              <form className="auth-form" onSubmit={handleRegister}>
                <label>
                  Display Name (optional)
                  <input
                    type="text"
                    value={registerDisplayName}
                    onChange={(e) => setRegisterDisplayName(e.target.value)}
                  />
                </label>
                <label>
                  Email
                  <input
                    type="email"
                    value={registerEmail}
                    onChange={(e) => setRegisterEmail(e.target.value)}
                    required
                  />
                </label>
                <label>
                  Password
                  <input
                    type="password"
                    value={registerPassword}
                    onChange={(e) => setRegisterPassword(e.target.value)}
                    minLength={8}
                    required
                  />
                </label>
                <label>
                  Confirm Password
                  <input
                    type="password"
                    value={registerConfirmPassword}
                    onChange={(e) => setRegisterConfirmPassword(e.target.value)}
                    minLength={8}
                    required
                  />
                </label>
                <button className="primary-btn" type="submit" disabled={authBusy}>
                  {authBusy ? 'Creating account...' : 'Create Account'}
                </button>
              </form>
            )}

            {authError && <p className="error-banner">{authError}</p>}
          </section>
        </div>
      </div>
    );
  }

  return (
    <div className={`app-layout ${themeMode === 'dark' ? 'theme-dark' : 'theme-light'}`}>
      <aside className="sidebar">
        <div className="sidebar-top">
          <div className="sidebar-avatar">{(currentUser.display_name || currentUser.email || '?')[0].toUpperCase()}</div>
          <div>
            <p className="sidebar-name">{currentUser.display_name || currentUser.email}</p>
            <p className="sidebar-role">Student Portfolio</p>
          </div>
        </div>

        <nav className="sidebar-nav">
          <p className="sidebar-section-label">Main</p>
          {navButtons.slice(0, 4).map((item) => (
            <button
              key={item.id}
              type="button"
              className={view === item.id ? 'sidebar-btn active' : 'sidebar-btn'}
              onClick={() => setView(item.id)}
            >
              <span className="sidebar-dot" />
              {item.label}
            </button>
          ))}
          <p className="sidebar-section-label" style={{ marginTop: '1.25rem' }}>Output</p>
          {navButtons.slice(4).map((item) => (
            <button
              key={item.id}
              type="button"
              className={view === item.id ? 'sidebar-btn active' : 'sidebar-btn'}
              onClick={() => setView(item.id)}
            >
              <span className="sidebar-dot" />
              {item.label}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="theme-toggle" role="group" aria-label="Theme mode">
            <button
              type="button"
              className={themeMode === 'light' ? 'theme-toggle-btn active' : 'theme-toggle-btn'}
              onClick={() => setThemeMode('light')}
              aria-label="Switch to light mode"
              title="Light mode"
            >
              <Sun size={14} strokeWidth={2} />
            </button>
            <button
              type="button"
              className={themeMode === 'dark' ? 'theme-toggle-btn active' : 'theme-toggle-btn'}
              onClick={() => setThemeMode('dark')}
              aria-label="Switch to dark mode"
              title="Dark mode"
            >
              <Moon size={14} strokeWidth={2} />
            </button>
          </div>
          <button className="sidebar-logout" type="button" onClick={handleLogout}>
            ↩ Log out
          </button>
        </div>
      </aside>

      <div className="main-content">
        {flashMessage && <p className="success-banner">{flashMessage}</p>}
        {dashboardError && <p className="error-banner">{dashboardError}</p>}

        <main className="dashboard-main">
          {view === 'projects' && (
            <AnimatePresence mode="wait">
              <motion.section
                key={view}
                className="panel"
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -16 }}
                transition={{ duration: 0.25 }}
              >
              <h2>Your Projects</h2>
              {loading ? (
                <p>Loading projects...</p>
              ) : (
                <div className="project-grid">
                  <article className="project-card add-project-card">
                    <button className="add-project-btn" type="button" onClick={() => setView('upload')}>
                      <span className="add-project-plus" aria-hidden="true">+</span>
                      <span className="add-project-title">Add Project</span>
                      <span className="add-project-subtitle">Upload a ZIP snapshot</span>
                    </button>
                  </article>
                  {projects.map((project, index) => {
                    const totalCommits = normalizeMetricCount(project.metrics?.total_commits);
                    const userCommits = normalizeMetricCount(project.metrics?.user_commits);
                    const contributorCount = normalizeMetricCount(project.metrics?.contributor_count);
                    const showContributionStats = totalCommits > 0 || userCommits > 0 || contributorCount > 0;
                    const analysisStatus = getSnapshotStatus(project.latest_snapshot?.id, snapshotAnalyses);

                    return (
                      <motion.article
                        key={project.id}
                        className="project-card"
                        initial={{ opacity: 0, y: 24 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.35, delay: index * 0.07 }}
                        whileHover={{ y: -4, boxShadow: '0 16px 32px rgba(46,108,244,0.13)' }}
                      >
                        {projectThumbnails[project.id]?.loading ? (
                          <p className="muted">Loading thumbnail...</p>
                        ) : projectThumbnails[project.id]?.hasImage ? (
                          <img
                            className="project-thumbnail"
                            src={projectThumbnails[project.id].imageUrl}
                            alt={`${project.name} thumbnail`}
                          />
                        ) : (
                          <div className="project-thumbnail project-thumbnail-placeholder">No thumbnail</div>
                        )}
                        {projectThumbnails[project.id]?.error && (
                          <p className="muted">Thumbnail unavailable: {projectThumbnails[project.id].error}</p>
                        )}
                        <h3>{project.name}</h3>
                        <p>Type: {project.project_type || 'Unknown'}</p>
                        <p>Added: {formatDate(project.created_at)}</p>
                        {showContributionStats && (
                          <>
                            <p>Commits: {totalCommits}</p>
                            <p>Your commits: {userCommits}</p>
                            <p>Contributors: {contributorCount}</p>
                          </>
                        )}
                        <p className={analysisStatus.isRunning ? 'analysis-pill analysis-pill-running' : 'analysis-pill'}>
                          {analysisStatus.badge}
                        </p>
                        {analysisStatus.progress && renderAnalysisProgress(analysisStatus.progress)}
                        {analysisStatus.detail && <p className="muted">{analysisStatus.detail}</p>}
                        {project.metrics?.rank_score != null && (
                          <p className="rank-pill">Rank score {project.metrics.rank_score.toFixed(2)}</p>
                        )}
                        <div className="card-actions">
                          <button className="primary-btn" type="button" onClick={() => viewProjectDetails(project)}>
                            View Details
                          </button>
                          <button className="secondary-btn" type="button" onClick={() => generateResume(project.id)}>
                            Generate Resume
                          </button>
                          <button
                            className="secondary-btn"
                            type="button"
                            onClick={() => deleteProject(project)}
                            disabled={deletingProjectId === project.id}
                          >
                            {deletingProjectId === project.id ? 'Deleting...' : 'Delete Project'}
                          </button>
                        </div>
                      </motion.article>
                    );
                  })}
                </div>
              )}
              </motion.section>
            </AnimatePresence>
          )}

          {view === 'dashboardMode' && (
            <AnimatePresence mode="wait">
              <motion.section
                key={view}
                className="panel"
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -16 }}
                transition={{ duration: 0.25 }}
              >
              <h2>Dashboard Mode</h2>
              <div className="stack-block">
                <div className="panel-title-row">
                  <div>
                    <p className="muted">
                      Current mode:{' '}
                      <strong>{dashboardModeLoading ? 'Loading...' : dashboardMode === 'public' ? 'Public' : 'Private'}</strong>
                    </p>
                    {publicPortfolioUrl && <p className="muted">Public URL: {publicPortfolioUrl}</p>}
                  </div>
                  <div className="card-actions">
                    <button
                      className={dashboardMode === 'public' ? 'ghost-btn' : 'primary-btn'}
                      type="button"
                      onClick={makeDashboardPublic}
                      disabled={dashboardModeActionBusy || dashboardModeLoading}
                    >
                      {dashboardModeActionBusy && dashboardMode !== 'public' ? 'Working...' : 'Make Public'}
                    </button>
                    <button
                      className={dashboardMode === 'public' ? 'secondary-btn' : 'ghost-btn'}
                      type="button"
                      onClick={makeDashboardPrivate}
                      disabled={dashboardModeActionBusy || dashboardModeLoading}
                    >
                      {dashboardModeActionBusy && dashboardMode === 'public' ? 'Working...' : 'Make Private'}
                    </button>
                    <button
                      className="secondary-btn"
                      type="button"
                      onClick={regenerateDashboardLink}
                      disabled={dashboardModeActionBusy || dashboardModeLoading || !publicPortfolioUrl}
                    >
                      Regenerate Link
                    </button>
                    <button
                      className="ghost-btn"
                      type="button"
                      onClick={copyLastGeneratedLink}
                      disabled={!publicPortfolioUrl || dashboardModeLoading}
                    >
                      Copy URL
                    </button>
                  </div>
                </div>
                <div className="summary-grid">
                  <label className="field">
                    <span>
                      <input
                        type="checkbox"
                        checked={dashboardVisibilityConfig.projects}
                        onChange={() => handleDashboardVisibilityToggle('projects')}
                        disabled={dashboardVisibilitySaving || dashboardModeLoading}
                      />{' '}
                      Projects
                    </span>
                  </label>
                  <label className="field">
                    <span>
                      <input
                        type="checkbox"
                        checked={dashboardVisibilityConfig.skills_timeline}
                        onChange={() => handleDashboardVisibilityToggle('skills_timeline')}
                        disabled={dashboardVisibilitySaving || dashboardModeLoading}
                      />{' '}
                      Skills Timeline
                    </span>
                  </label>
                  <label className="field">
                    <span>
                      <input
                        type="checkbox"
                        checked={dashboardVisibilityConfig.top_projects}
                        onChange={() => handleDashboardVisibilityToggle('top_projects')}
                        disabled={dashboardVisibilitySaving || dashboardModeLoading}
                      />{' '}
                      Top Projects
                    </span>
                  </label>
                  <label className="field">
                    <span>
                      <input
                        type="checkbox"
                        checked={dashboardVisibilityConfig.activity_heatmap}
                        onChange={() => handleDashboardVisibilityToggle('activity_heatmap')}
                        disabled={dashboardVisibilitySaving || dashboardModeLoading}
                      />{' '}
                      Activity Heatmap
                    </span>
                  </label>
                  <label className="field">
                    <span>
                      <input
                        type="checkbox"
                        checked={dashboardVisibilityConfig.showcases}
                        onChange={() => handleDashboardVisibilityToggle('showcases')}
                        disabled={dashboardVisibilitySaving || dashboardModeLoading}
                      />{' '}
                      Showcases
                    </span>
                  </label>
                </div>
                <div className="card-actions">
                  <button
                    className="secondary-btn"
                    type="button"
                    onClick={saveDashboardVisibility}
                    disabled={dashboardVisibilitySaving || dashboardModeLoading}
                  >
                    {dashboardVisibilitySaving ? 'Saving...' : 'Save Visibility'}
                  </button>
                </div>
                {dashboardModeError && <p className="error-banner inline-error">{dashboardModeError}</p>}
              </div>
              </motion.section>
            </AnimatePresence>
          )}

          {view === 'preferences' && (
            <AnimatePresence mode="wait">
              <motion.section
                key={view}
                className="panel"
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -16 }}
                transition={{ duration: 0.25 }}
              >
              <h2>Preferences</h2>
              <div className="stack-block">
                <h3>Representation Preferences</h3>
                <p className="muted">
                  Configure ranking, chronology, comparison attributes, skill highlights, and showcase selection before
                  generating or editing resume and portfolio artifacts.
                </p>

                {configLoading ? (
                  <p>Loading representation preferences...</p>
                ) : (
                  <>
                    <label className="field">
                      Re-ranking mode
                      <select value={rankingMode} onChange={(event) => setRankingMode(event.target.value)}>
                        <option value="auto">Auto</option>
                        <option value="weighted">Weighted</option>
                        <option value="manual">Manual</option>
                      </select>
                    </label>

                    {rankingMode === 'weighted' && (
                      <div className="summary-grid">
                        <label className="field">
                          User commits weight
                          <input
                            type="number"
                            step="0.1"
                            value={rankingUserWeight}
                            onChange={(event) => setRankingUserWeight(event.target.value)}
                          />
                        </label>
                        <label className="field">
                          Other commits weight
                          <input
                            type="number"
                            step="0.1"
                            value={rankingOtherWeight}
                            onChange={(event) => setRankingOtherWeight(event.target.value)}
                          />
                        </label>
                        <label className="field">
                          Contributor count weight
                          <input
                            type="number"
                            step="0.1"
                            value={rankingContributorWeight}
                            onChange={(event) => setRankingContributorWeight(event.target.value)}
                          />
                        </label>
                      </div>
                    )}

                    <label className="mode-option">
                      <input
                        type="checkbox"
                        checked={rankingAllowNoUserScore}
                        onChange={(event) => setRankingAllowNoUserScore(event.target.checked)}
                      />
                      Include projects with zero user commits in ranking scores
                    </label>

                    <div className="stack-block">
                      <h4>Manual ranking overrides</h4>
                      {projects.length === 0 ? (
                        <p className="muted">Upload projects to set manual rank values.</p>
                      ) : (
                        <div className="table-wrap">
                          <table>
                            <thead>
                              <tr>
                                <th>Project</th>
                                <th>Manual rank (lower is better)</th>
                              </tr>
                            </thead>
                            <tbody>
                              {projects.map((project) => (
                                <tr key={`manual-rank-${project.id}`}>
                                  <td>{project.name}</td>
                                  <td>
                                    <input
                                      type="number"
                                      step="1"
                                      min="1"
                                      value={rankingManualRanks[project.id] || ''}
                                      onChange={(event) => {
                                        const nextValue = event.target.value;
                                        setRankingManualRanks((current) => {
                                          const next = { ...current };
                                          if (!nextValue.trim()) {
                                            delete next[project.id];
                                          } else {
                                            next[project.id] = nextValue;
                                          }
                                          return next;
                                        });
                                      }}
                                    />
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>

                    <div className="stack-block">
                      <h4>Chronology corrections</h4>
                      {projects.length === 0 ? (
                        <p className="muted">Upload projects to set chronology corrections.</p>
                      ) : (
                        <div className="table-wrap">
                          <table>
                            <thead>
                              <tr>
                                <th>Project</th>
                                <th>Corrected date</th>
                              </tr>
                            </thead>
                            <tbody>
                              {projects.map((project) => (
                                <tr key={`project-date-${project.id}`}>
                                  <td>{project.name}</td>
                                  <td>
                                    <input
                                      type="date"
                                      value={projectDateInputValue(chronologyProjectDates[project.id])}
                                      onChange={(event) => {
                                        const nextValue = event.target.value;
                                        setChronologyProjectDates((current) => {
                                          const next = { ...current };
                                          if (!nextValue) {
                                            delete next[project.id];
                                          } else {
                                            next[project.id] = nextValue;
                                          }
                                          return next;
                                        });
                                      }}
                                    />
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>

                    <div className="stack-block">
                      <h4>Comparison attributes</h4>
                      <div className="badge-row">
                        {COMPARISON_ATTRIBUTE_OPTIONS.map((option) => {
                          const selected = comparisonAttributes.includes(option.value);
                          return (
                            <label key={option.value} className="mode-option">
                              <input
                                type="checkbox"
                                checked={selected}
                                onChange={() => {
                                  setComparisonAttributes((current) => {
                                    if (current.includes(option.value)) {
                                      return current.filter((entry) => entry !== option.value);
                                    }
                                    return [...current, option.value];
                                  });
                                }}
                              />
                              {option.label}
                            </label>
                          );
                        })}
                      </div>
                    </div>

                    <label className="field">
                      Skills/highlights (comma-separated)
                      <input
                        type="text"
                        value={highlightSkillsInput}
                        placeholder="e.g. React, Python, PostgreSQL"
                        onChange={(event) => setHighlightSkillsInput(event.target.value)}
                      />
                    </label>

                    <div className="stack-block">
                      <h4>Showcase projects</h4>
                      {projects.length === 0 ? (
                        <p className="muted">Upload projects to choose showcase selections.</p>
                      ) : (
                        <div className="badge-row">
                          {projects.map((project) => {
                            const selected = showcaseProjectIds.includes(project.id);
                            return (
                              <label key={`showcase-${project.id}`} className="mode-option">
                                <input
                                  type="checkbox"
                                  checked={selected}
                                  onChange={() => {
                                    setShowcaseProjectIds((current) => {
                                      if (current.includes(project.id)) {
                                        return current.filter((entry) => entry !== project.id);
                                      }
                                      return [...current, project.id];
                                    });
                                  }}
                                />
                                {project.name}
                              </label>
                            );
                          })}
                        </div>
                      )}
                    </div>

                    <button
                      className="primary-btn"
                      type="button"
                      onClick={saveRepresentationPreferences}
                      disabled={configSaving}
                    >
                      {configSaving ? 'Saving preferences...' : 'Save Representation Preferences'}
                    </button>
                    {userConfig && <p className="muted">Preferences are saved to your profile-level user configuration.</p>}
                  </>
                )}
              </div>
              </motion.section>
            </AnimatePresence>
          )}

          {view === 'compare' && (
            <AnimatePresence mode="wait">
              <motion.section
                key={view}
                className="panel"
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -16 }}
                transition={{ duration: 0.25 }}
              >
              <h2>Compare Projects</h2>
              <p className="muted">
                Choose projects and run compare. Returned fields follow your saved Comparison Attributes from
                Preferences.
              </p>

              {projects.length === 0 ? (
                <p>No projects available to compare yet.</p>
              ) : (
                <>
                  <div className="stack-block">
                    <h3>Select projects</h3>
                    <div className="badge-row">
                      {projects.map((project) => {
                        const selected = compareSelectedProjectIds.includes(project.id);
                        return (
                          <label key={`compare-project-${project.id}`} className="mode-option">
                            <input
                              type="checkbox"
                              checked={selected}
                              onChange={() => {
                                setCompareSelectedProjectIds((current) => {
                                  if (current.includes(project.id)) {
                                    return current.filter((entry) => entry !== project.id);
                                  }
                                  return [...current, project.id];
                                });
                              }}
                            />
                            {project.name}
                          </label>
                        );
                      })}
                    </div>
                    <button
                      className="primary-btn"
                      type="button"
                      onClick={runProjectComparison}
                      disabled={compareLoading || compareSelectedProjectIds.length === 0}
                    >
                      {compareLoading ? 'Comparing...' : 'Run Compare'}
                    </button>
                  </div>

                  {compareResults && (
                    <div className="stack-block">
                      <h3>Comparison Results</h3>
                      <p className="muted">
                        Attributes returned: {(compareResults.attributes || []).join(', ') || 'None'}
                      </p>
                      {(compareResults.projects || []).length === 0 ? (
                        <p className="muted">No comparison rows returned.</p>
                      ) : (
                        (compareResults.projects || []).map((projectResult) => {
                          const projectId = projectResult.project_id;
                          const projectName =
                            projects.find((project) => project.id === projectId)?.name ||
                            projectResult.meta?.name ||
                            projectId;
                          const sections = Object.entries(projectResult).filter(([key]) => key !== 'project_id');

                          return (
                            <article key={`compare-result-${projectId}`} className="project-card">
                              <h3>{projectName}</h3>
                              {sections.length === 0 ? (
                                <p className="muted">No selected attributes returned for this project.</p>
                              ) : (
                                sections.map(([key, value]) => (
                                  <div key={`${projectId}-${key}`} className="stack-block">
                                    <h4>{key}</h4>
                                    <pre>{JSON.stringify(value, null, 2)}</pre>
                                  </div>
                                ))
                              )}
                            </article>
                          );
                        })
                      )}
                    </div>
                  )}
                </>
              )}
              </motion.section>
            </AnimatePresence>
          )}

          {view === 'upload' && (
            <AnimatePresence mode="wait">
              <motion.section
                key={view}
                className="panel"
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -16 }}
                transition={{ duration: 0.25 }}
              >
              <h2>Upload Project ZIP</h2>
              <p className="muted">Active portfolio: {portfolioId || 'default'}</p>
              <div className="upload-mode-toggle">
                <label className="mode-option">
                  <input
                    type="radio"
                    name="uploadMode"
                    value="new"
                    checked={uploadMode === 'new'}
                    onChange={() => setUploadMode('new')}
                  />
                  New project upload
                </label>
                <label className="mode-option">
                  <input
                    type="radio"
                    name="uploadMode"
                    value="incremental"
                    checked={uploadMode === 'incremental'}
                    onChange={() => setUploadMode('incremental')}
                  />
                  Incremental update for existing project
                </label>
              </div>

              {uploadMode === 'new' ? (
                <>
                  <p className="muted">
                    New project mode creates a separate project record. To add another snapshot to an existing project,
                    choose Incremental update.
                  </p>
                  <label className="field">
                    Project name override (optional)
                    <input
                      type="text"
                      value={uploadProjectName}
                      placeholder="Defaults to filename"
                      onChange={(e) => setUploadProjectName(e.target.value)}
                    />
                  </label>
                </>
              ) : (
                <>
                  <p className="muted">
                    Incremental uploads append a new snapshot and merge data into the selected project. Existing
                    snapshots are preserved, and duplicate files are deduplicated by the backend.
                  </p>
                  {projects.length === 0 ? (
                    <p>No existing projects available yet. Upload a new project first.</p>
                  ) : (
                    <>
                      <label className="field">
                        Project to update
                        <select
                          value={uploadTargetProjectId}
                          onChange={(e) => setUploadTargetProjectId(e.target.value)}
                        >
                          <option value="" disabled>
                            Select a project
                          </option>
                          {projects.map((project) => (
                            <option key={project.id} value={project.id}>
                              {project.name}
                            </option>
                          ))}
                        </select>
                      </label>
                      {selectedUploadProject && (
                        <p className="muted">ZIP contents will be added to: {selectedUploadProject.name}</p>
                      )}
                      <div className="stack-block">
                        <h3>Snapshot history</h3>
                        {uploadHistoryLoading ? (
                          <p>Loading snapshot history...</p>
                        ) : uploadHistoryError ? (
                          <p className="muted">{uploadHistoryError}</p>
                        ) : uploadSnapshotHistory.length === 0 ? (
                          <p className="muted">No snapshots have been recorded for this project yet.</p>
                        ) : (
                          <ul className="simple-list">
                            {uploadSnapshotHistory.map((snapshot, index) => (
                              <li key={snapshot.id}>
                                <span>{snapshot.snapshot_label || `Snapshot ${uploadSnapshotHistory.length - index}`}</span>
                                <span className="muted">
                                  Uploaded {formatDateTime(snapshot.ingested_at)} from{' '}
                                  {snapshot.source_zip_name || 'Unnamed ZIP'}
                                </span>
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    </>
                  )}
                </>
              )}

              <label className="field">
                Snapshot label (optional)
                <input
                  type="text"
                  value={snapshotLabel}
                  placeholder={uploadMode === 'incremental' ? 'e.g. sprint-3 update' : 'e.g. initial import'}
                  onChange={(e) => setSnapshotLabel(e.target.value)}
                />
              </label>
              <label className="field">
                ZIP file
                <input
                  type="file"
                  accept=".zip"
                  onChange={(e) => {
                    const selected = e.target.files?.[0] || null;
                    setFile(selected);
                    if (selected && uploadMode === 'new' && !uploadProjectName.trim()) {
                      setUploadProjectName(normalizeProjectName(selected.name));
                    }
                  }}
                />
              </label>
              {file && <p className="muted">Selected file: {file.name}</p>}
              <button
                className="primary-btn"
                type="button"
                disabled={!file || uploading || (uploadMode === 'incremental' && !uploadTargetProjectId)}
                onClick={handleUpload}
              >
                {uploading ? 'Uploading...' : uploadMode === 'incremental' ? 'Upload Incremental Snapshot' : 'Upload Project'}
              </button>
              </motion.section>
            </AnimatePresence>
          )}

          {view === 'report' && selectedProject && (
            <AnimatePresence mode="wait">
              <motion.section
                key={view}
                className="panel"
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -16 }}
                transition={{ duration: 0.25 }}
              >
              <div className="panel-title-row">
                <button className="ghost-btn" type="button" onClick={() => setView('projects')}>
                  Back to Projects
                </button>
                <h2>{selectedProject.name}</h2>
              </div>
              {loading ? (
                <p>Loading project details...</p>
              ) : (
                <>
                  <div className="stack-block">
                    <h3>Analysis Status</h3>
                    {selectedProjectStatus && (
                      <>
                        <p
                          className={
                            selectedProjectStatus.isRunning ? 'analysis-pill analysis-pill-running' : 'analysis-pill'
                          }
                        >
                          {selectedProjectStatus.badge}
                        </p>
                        {selectedProjectStatus.progress && renderAnalysisProgress(selectedProjectStatus.progress)}
                        {selectedProjectStatus.detail && <p className="muted">{selectedProjectStatus.detail}</p>}
                      </>
                    )}
                  </div>

                  <>
                      <div className="stack-block">
                        <h3>Project Thumbnail</h3>
                        {selectedProjectThumbnail?.loading ? (
                          <p>Loading thumbnail...</p>
                        ) : selectedProjectThumbnail?.hasImage ? (
                          <img
                            className="project-thumbnail project-thumbnail-detail"
                            src={selectedProjectThumbnail.imageUrl}
                            alt={`${selectedProject.name} thumbnail`}
                          />
                        ) : (
                          <div className="project-thumbnail project-thumbnail-placeholder project-thumbnail-detail">
                            No thumbnail uploaded yet.
                          </div>
                        )}
                        {selectedProjectThumbnail?.error && (
                          <p className="error-banner inline-error">{selectedProjectThumbnail.error}</p>
                        )}
                        <label className="field">
                          Upload or replace thumbnail
                          <input
                            type="file"
                            accept="image/*"
                            onChange={(event) => {
                              setThumbnailActionError('');
                              setThumbnailUploadFile(event.target.files?.[0] || null);
                            }}
                          />
                        </label>
                        {thumbnailUploadFile && <p className="muted">Selected image: {thumbnailUploadFile.name}</p>}
                        <div className="card-actions">
                          <button
                            className="primary-btn"
                            type="button"
                            onClick={saveProjectThumbnail}
                            disabled={!thumbnailUploadFile || thumbnailActionProjectId === selectedProject.id}
                          >
                            {thumbnailActionProjectId === selectedProject.id ? 'Saving thumbnail...' : 'Save Thumbnail'}
                          </button>
                          <button
                            className="secondary-btn"
                            type="button"
                            onClick={removeProjectThumbnail}
                            disabled={!selectedProjectThumbnail?.hasImage || thumbnailActionProjectId === selectedProject.id}
                          >
                            {thumbnailActionProjectId === selectedProject.id ? 'Removing thumbnail...' : 'Remove Thumbnail'}
                          </button>
                        </div>
                        {thumbnailActionError && <p className="error-banner inline-error">{thumbnailActionError}</p>}
                      </div>

                      <div className="stack-block">
                        <h3>Key Role</h3>
                        <label className="field">
                          Your role in this project
                          <textarea
                            value={projectRoleDraft}
                            maxLength={128}
                            rows={3}
                            placeholder="e.g. Technical Lead, Full-Stack Developer"
                            onChange={(event) => setProjectRoleDraft(event.target.value)}
                          />
                        </label>
                        <p className="muted">
                          Saved role text is included in resume and portfolio generation for this project.
                        </p>
                        <button
                          className="primary-btn"
                          type="button"
                          onClick={saveProjectRole}
                          disabled={loading || savingProjectRole || !projectRoleChanged}
                        >
                          {savingProjectRole ? 'Saving role...' : 'Save Role'}
                        </button>
                      </div>

                      <div className="stack-block">
                        <h3>Portfolio Showcase</h3>
                        <p className="muted">
                          The title and summary shown for this project in your portfolio. Generate to create AI-drafted
                          wording, then edit and save your changes.
                        </p>
                        {showcaseError && <p className="error-banner inline-error">{showcaseError}</p>}
                        {!selectedShowcase ? (
                          <button
                            className="secondary-btn"
                            type="button"
                            onClick={generateShowcase}
                            disabled={showcaseGenerating}
                          >
                            {showcaseGenerating ? 'Generating...' : 'Generate Showcase Text'}
                          </button>
                        ) : (
                          <>
                            <label className="field">
                              Title
                              <input
                                type="text"
                                value={showcaseDraft.title}
                                maxLength={200}
                                placeholder="Showcase title"
                                onChange={(e) => setShowcaseDraft((prev) => ({ ...prev, title: e.target.value }))}
                              />
                            </label>
                            <label className="field">
                              Summary
                              <textarea
                                value={showcaseDraft.summary_text}
                                rows={5}
                                placeholder="Portfolio showcase summary"
                                onChange={(e) => setShowcaseDraft((prev) => ({ ...prev, summary_text: e.target.value }))}
                              />
                            </label>
                            <div className="card-actions">
                              <button
                                className="primary-btn"
                                type="button"
                                onClick={saveShowcase}
                                disabled={showcaseSaving || !showcaseChanged}
                              >
                                {showcaseSaving ? 'Saving...' : 'Save Showcase'}
                              </button>
                              <button
                                className="secondary-btn"
                                type="button"
                                onClick={generateShowcase}
                                disabled={showcaseGenerating}
                              >
                                {showcaseGenerating ? 'Regenerating...' : 'Regenerate'}
                              </button>
                            </div>
                          </>
                        )}
                      </div>

                      <div className="stack-block">
                        <h3>Evidence of Success</h3>
                        <p className="muted">
                          Add metrics, feedback, and evaluation notes for this project. Numeric values (for example
                          <code> 42 </code>) and JSON values (for example <code>{'{"grade":"A"}'}</code>) are saved as
                          structured evidence.
                        </p>

                    <div className="evidence-section">
                      <div className="panel-title-row">
                        <h4>Metrics</h4>
                        <button className="secondary-btn" type="button" onClick={addProjectMetricRow}>
                          Add Metric
                        </button>
                      </div>
                      {projectMetricsDraft.length === 0 ? (
                        <p className="muted">No metric entries added yet.</p>
                      ) : (
                        <div className="evidence-row-list">
                          {projectMetricsDraft.map((entry) => (
                            <div className="evidence-row" key={entry.id}>
                              <input
                                type="text"
                                value={entry.key}
                                placeholder="Metric name (e.g. downloads)"
                                onChange={(event) => {
                                  const nextValue = event.target.value;
                                  setProjectEvidenceError('');
                                  setProjectMetricsDraft((previous) =>
                                    previous.map((row) => (row.id === entry.id ? { ...row, key: nextValue } : row))
                                  );
                                }}
                              />
                              <input
                                type="text"
                                value={entry.value}
                                placeholder='Metric value (e.g. 1200 or "strong")'
                                onChange={(event) => {
                                  const nextValue = event.target.value;
                                  setProjectEvidenceError('');
                                  setProjectMetricsDraft((previous) =>
                                    previous.map((row) => (row.id === entry.id ? { ...row, value: nextValue } : row))
                                  );
                                }}
                              />
                              <button
                                className="secondary-btn"
                                type="button"
                                onClick={() => {
                                  setProjectEvidenceError('');
                                  setProjectMetricsDraft((previous) =>
                                    previous.filter((row) => row.id !== entry.id)
                                  );
                                }}
                              >
                                Remove
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="evidence-section">
                      <div className="panel-title-row">
                        <h4>Feedback</h4>
                        <button className="secondary-btn" type="button" onClick={addProjectFeedbackRow}>
                          Add Feedback
                        </button>
                      </div>
                      {projectFeedbackDraft.length === 0 ? (
                        <p className="muted">No feedback entries added yet.</p>
                      ) : (
                        <div className="evidence-row-list">
                          {projectFeedbackDraft.map((entry) => (
                            <div className="evidence-row evidence-row-feedback" key={entry.id}>
                              <input
                                type="text"
                                value={entry.source}
                                placeholder="Source (optional)"
                                onChange={(event) => {
                                  const nextValue = event.target.value;
                                  setProjectEvidenceError('');
                                  setProjectFeedbackDraft((previous) =>
                                    previous.map((row) =>
                                      row.id === entry.id ? { ...row, source: nextValue } : row
                                    )
                                  );
                                }}
                              />
                              <textarea
                                rows={3}
                                value={entry.note}
                                placeholder="Feedback text"
                                onChange={(event) => {
                                  const nextValue = event.target.value;
                                  setProjectEvidenceError('');
                                  setProjectFeedbackDraft((previous) =>
                                    previous.map((row) => (row.id === entry.id ? { ...row, note: nextValue } : row))
                                  );
                                }}
                              />
                              <button
                                className="secondary-btn"
                                type="button"
                                onClick={() => {
                                  setProjectEvidenceError('');
                                  setProjectFeedbackDraft((previous) =>
                                    previous.filter((row) => row.id !== entry.id)
                                  );
                                }}
                              >
                                Remove
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="evidence-section">
                      <div className="panel-title-row">
                        <h4>Evaluation Notes</h4>
                        <button className="secondary-btn" type="button" onClick={addProjectEvaluationRow}>
                          Add Note
                        </button>
                      </div>
                      {projectEvaluationDraft.length === 0 ? (
                        <p className="muted">No evaluation entries added yet.</p>
                      ) : (
                        <div className="evidence-row-list">
                          {projectEvaluationDraft.map((entry) => (
                            <div className="evidence-row" key={entry.id}>
                              <input
                                type="text"
                                value={entry.key}
                                placeholder="Label (e.g. overall)"
                                onChange={(event) => {
                                  const nextValue = event.target.value;
                                  setProjectEvidenceError('');
                                  setProjectEvaluationDraft((previous) =>
                                    previous.map((row) => (row.id === entry.id ? { ...row, key: nextValue } : row))
                                  );
                                }}
                              />
                              <input
                                type="text"
                                value={entry.value}
                                placeholder='Note value (e.g. "Excellent delivery")'
                                onChange={(event) => {
                                  const nextValue = event.target.value;
                                  setProjectEvidenceError('');
                                  setProjectEvaluationDraft((previous) =>
                                    previous.map((row) => (row.id === entry.id ? { ...row, value: nextValue } : row))
                                  );
                                }}
                              />
                              <button
                                className="secondary-btn"
                                type="button"
                                onClick={() => {
                                  setProjectEvidenceError('');
                                  setProjectEvaluationDraft((previous) =>
                                    previous.filter((row) => row.id !== entry.id)
                                  );
                                }}
                              >
                                Remove
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                        {projectEvidenceError && <p className="error-banner inline-error">{projectEvidenceError}</p>}

                        <button
                          className="primary-btn"
                          type="button"
                          onClick={saveProjectEvidence}
                          disabled={loading || savingProjectEvidence}
                        >
                          {savingProjectEvidence ? 'Saving evidence...' : 'Save Evidence'}
                        </button>
                      </div>
                    </>

                  {projectReport && (
                    <div className="stack-block">
                      <h3>Summary</h3>
                      <div className="summary-grid">
                        <p>Total files: {reportStats.totalFiles}</p>
                        <p>Total lines: {reportStats.totalLines}</p>
                        <p>Languages: {reportStats.languageCount}</p>
                      </div>
                      {reportStats.topLanguages.length > 0 && (
                        <>
                          <h4>Top languages</h4>
                          <ul className="simple-list">
                            {reportStats.topLanguages.map((language, index) => (
                              <li key={`${language.language || language.name || 'unknown'}-${index}`}>
                                <span>{language.language || language.name || 'Unknown'}</span>
                                <span>
                                  {typeof language.percentage === 'number'
                                    ? `${language.percentage.toFixed(1)}%`
                                    : `${Number(language.files || 0)} files`}
                                </span>
                              </li>
                            ))}
                          </ul>
                        </>
                      )}
                    </div>
                  )}

                  {projectSkills?.skills?.length > 0 && (
                    <div className="stack-block">
                      <h3>Detected Skills</h3>
                      <div className="badge-row">
                        {projectSkills.skills.map((skill, index) => (
                          <span key={`${skill.skill_name}-${index}`} className="skill-badge">
                            {skill.skill_name}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {contributors.length > 0 && (
                    <div className="stack-block">
                      <h3>Contributors</h3>
                      <div className="table-wrap">
                        <table>
                          <thead>
                            <tr>
                              <th>Name</th>
                              <th>Email</th>
                              <th>Commits</th>
                              <th>Marked as You</th>
                            </tr>
                          </thead>
                          <tbody>
                            {contributors.map((contributor) => (
                              <tr key={contributor.contributor_id}>
                                <td>{contributor.canonical_name}</td>
                                <td>{contributor.email || '-'}</td>
                                <td>{contributor.commits}</td>
                                <td>{contributor.is_user ? 'Yes' : 'No'}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  <div className="stack-block">
                      <h3>Resume Editing</h3>
                      {!activeResumeId ? (
                        <>
                          <p className="muted">No resume generated yet. Generate one from the projects list, or:</p>
                          <button
                            className="primary-btn"
                            type="button"
                            disabled={loading}
                            onClick={handleGenerateResume}
                          >
                            {loading ? 'Generating...' : 'Generate Resume'}
                          </button>
                        </>
                      ) : (
                        <>
                          <label className="field">
                            Summary
                            <textarea
                              rows={4}
                              value={resumeWording.summary_text}
                              onChange={(e) => setResumeWording((prev) => ({ ...prev, summary_text: e.target.value }))}
                            />
                          </label>

                          {resumeWording.resume_bullets.length > 0 && (
                            <>
                              <h4>Bullet Points</h4>
                              {resumeWording.resume_bullets.map((bullet, index) => (
                                <label className="field" key={index}>
                                  Bullet {index + 1}
                                  <textarea
                                    rows={2}
                                    value={bullet}
                                    onChange={(e) => {
                                      const updated = [...resumeWording.resume_bullets];
                                      updated[index] = e.target.value;
                                      setResumeWording((prev) => ({ ...prev, resume_bullets: updated }));
                                    }}
                                  />
                                </label>
                              ))}
                            </>
                          )}

                          <button
                            className="primary-btn"
                            type="button"
                            onClick={saveResumeWording}
                            disabled={savingResume}
                          >
                            {savingResume ? 'Saving...' : 'Save Resume Edits'}
                          </button>

                          <button
                            className="secondary-btn"
                            type="button"
                            onClick={() => window.open(`${API_BASE_URL}/resume/${activeResumeId}/pdf`, '_blank', 'noopener,noreferrer')}
                          >
                            Download Resume PDF
                          </button>

                          {resumeSaveStatus && <p className="muted">{resumeSaveStatus}</p>}
                        </>
                      )}
                    </div>
                </>
              )}
              </motion.section>
            </AnimatePresence>
          )}

          {view === 'top' && (
            <AnimatePresence mode="wait">
              <motion.section
                key={view}
                className="panel"
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -16 }}
                transition={{ duration: 0.25 }}
              >
              <h2>Top Ranked Projects</h2>
              {loading ? (
                <p>Loading top projects...</p>
              ) : topProjects.length === 0 ? (
                <p>No ranked projects yet.</p>
              ) : (
                <div className="top-list">
                  {topProjects.map((project, index) => (
                    <article key={project.project_id} className="top-card">
                      <p className="top-rank">#{index + 1}</p>
                      <div>
                        <h3>{project.name}</h3>
                        <p>Score: {project.rank_score?.toFixed(2) || 'N/A'}</p>
                        <p>Your commits: {project.features?.user_commits || 0}</p>
                        <p>Total commits: {project.features?.total_commits || 0}</p>
                        {project.summary?.top_languages && <p>Languages: {project.summary.top_languages}</p>}
                        {project.summary?.top_skills && <p>Skills: {project.summary.top_skills}</p>}
                      </div>
                    </article>
                  ))}
                </div>
              )}
              </motion.section>
            </AnimatePresence>
          )}

          {view === 'skills' && (
            <AnimatePresence mode="wait">
              <motion.section
                key={view}
                className="panel"
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -16 }}
                transition={{ duration: 0.25 }}
              >
              <h2>Skills Timeline</h2>
              {loading ? (
                <p>Loading skills timeline...</p>
              ) : chronologicalSkills.length === 0 ? (
                <p>No skill events available yet.</p>
              ) : (
                <div className="timeline">
                  {chronologicalSkills.map((event, index) => (
                    <article key={`${event.skill}-${event.snapshot_id}-${index}`} className="timeline-item">
                      <p className="timeline-date">{formatDate(event.first_seen_ts)}</p>
                      <div>
                        <h3>{event.skill}</h3>
                        <p className="muted">Project: {event.project_name}</p>
                        {event.max_prob != null && <p>Confidence: {(event.max_prob * 100).toFixed(0)}%</p>}
                      </div>
                    </article>
                  ))}
                </div>
              )}
              </motion.section>
            </AnimatePresence>
          )}
          {view === 'resume' && (
            <AnimatePresence mode="wait">
              <motion.div
                key={view}
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -16 }}
                transition={{ duration: 0.25 }}
              >
              {resumeLoading ? <section className="panel"><p>Loading resume data...</p></section> : (
                <>
                  <section className="panel">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <h2>Education</h2>
                      {editingEduId !== 'new' && <button className="primary-btn" onClick={startAddEdu}>+ Add</button>}
                    </div>
                    {editingEduId === 'new' && (
                      <div className="stack-block">
                        <div className="summary-grid">
                          <label className="field">Institution *<input value={eduForm.institution || ''} onChange={(e) => setEduForm((f) => ({ ...f, institution: e.target.value }))} placeholder="e.g. University of Waterloo" /></label>
                          <label className="field">Degree<input value={eduForm.degree || ''} onChange={(e) => setEduForm((f) => ({ ...f, degree: e.target.value }))} placeholder="e.g. B.Sc." /></label>
                          <label className="field">Field of Study<input value={eduForm.field_of_study || ''} onChange={(e) => setEduForm((f) => ({ ...f, field_of_study: e.target.value }))} placeholder="e.g. Computer Science" /></label>
                          <div style={{position: 'relative'}}><label className="field">Start Year<input type="number" value={eduForm.start_year || ''} onChange={(e) => setEduForm((f) => ({ ...f, start_year: e.target.value }))} onBlur={() => setEduTouched({ ...eduTouched, start_year: true })} placeholder="2018" min={1900} max={new Date().getFullYear()} /></label>{eduTouched.start_year && getEduYearErrors(eduForm.start_year, eduForm.end_year, eduForm.is_current).start_year && <span style={{ color: 'red', fontSize: '0.78em', position: 'absolute' }}>{getEduYearErrors(eduForm.start_year, eduForm.end_year, eduForm.is_current).start_year}</span>}</div>
                          <div style={{position: 'relative'}}><label className="field">End Year<input type="number" value={eduForm.end_year || ''} onChange={(e) => setEduForm((f) => ({ ...f, end_year: e.target.value }))} onBlur={() => setEduTouched({ ...eduTouched, end_year: true })} placeholder="2022" disabled={eduForm.is_current} min={eduForm.start_year || 1900} max={new Date().getFullYear() + YEAR_MAX_OFFSET_EDU} /></label>{eduTouched.end_year && !eduForm.is_current && getEduYearErrors(eduForm.start_year, eduForm.end_year, eduForm.is_current).end_year && <span style={{ color: 'red', fontSize: '0.78em', position: 'absolute' }}>{getEduYearErrors(eduForm.start_year, eduForm.end_year, eduForm.is_current).end_year}</span>}</div>
                        </div>
                        <label className="field" style={{ flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'flex-start', gap: '8px' }}>
                          Currently enrolled
                          <input type="checkbox" checked={eduForm.is_current || false} onChange={(e) => setEduForm((f) => ({ ...f, is_current: e.target.checked }))} />
                        </label>
                        <label className="field">Notes<textarea value={eduForm.description || ''} onChange={(e) => setEduForm((f) => ({ ...f, description: e.target.value }))} rows={2} /></label>
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <button className="primary-btn" disabled={!eduForm.institution?.trim() || resumeSaving || getEduYearErrors(eduForm.start_year, eduForm.end_year, eduForm.is_current).start_year ||
    getEduYearErrors(eduForm.start_year, eduForm.end_year, eduForm.is_current).end_year} onClick={saveEdu}>{resumeSaving ? 'Saving...' : 'Save'}</button>
                          <button className="ghost-btn" onClick={cancelEdu}>Cancel</button>
                        </div>
                      </div>
                    )}
                    {resumeEducation.length === 0 && editingEduId !== 'new' && <p className="muted">No education entries yet.</p>}
                    {resumeEducation.map((entry) => (
                      editingEduId === entry.id ? (
                        <div key={entry.id} className="stack-block">
                          <div className="summary-grid">
                            <label className="field">Institution *<input value={eduForm.institution || ''} onChange={(e) => setEduForm((f) => ({ ...f, institution: e.target.value }))} /></label>
                            <label className="field">Degree<input value={eduForm.degree || ''} onChange={(e) => setEduForm((f) => ({ ...f, degree: e.target.value }))} /></label>
                            <label className="field">Field of Study<input value={eduForm.field_of_study || ''} onChange={(e) => setEduForm((f) => ({ ...f, field_of_study: e.target.value }))} /></label>
                            <div style={{position: 'relative'}}><label className="field">Start Year<input type="number" value={eduForm.start_year || ''} onChange={(e) => setEduForm((f) => ({ ...f, start_year: e.target.value }))} onBlur={() => setEduTouched({ ...eduTouched, start_year: true })} min={1900} max={new Date().getFullYear()} /></label>{eduTouched.start_year && getEduYearErrors(eduForm.start_year, eduForm.end_year, eduForm.is_current).start_year && <span style={{ color: 'red', fontSize: '0.78em', position: 'absolute' }}>{getEduYearErrors(eduForm.start_year, eduForm.end_year, eduForm.is_current).start_year}</span>}</div>
                            <div style={{position: 'relative'}}><label className="field">End Year<input type="number" value={eduForm.end_year || ''} onChange={(e) => setEduForm((f) => ({ ...f, end_year: e.target.value }))} onBlur={() => setEduTouched({ ...eduTouched, end_year: true })} disabled={eduForm.is_current} min={eduForm.start_year || 1900} max={new Date().getFullYear() + YEAR_MAX_OFFSET_EDU} /></label>{eduTouched.end_year && !eduForm.is_current && getEduYearErrors(eduForm.start_year, eduForm.end_year, eduForm.is_current).end_year && <span style={{ color: 'red', fontSize: '0.78em', position: 'absolute' }}>{getEduYearErrors(eduForm.start_year, eduForm.end_year, eduForm.is_current).end_year}</span>}</div>
                          </div>
                          <label className="field" style={{ flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'flex-start', gap: '8px' }}>
                            Currently enrolled
                            <input type="checkbox" checked={eduForm.is_current || false} onChange={(e) => setEduForm((f) => ({ ...f, is_current: e.target.checked }))} />
                          </label>
                          <label className="field">Notes<textarea value={eduForm.description || ''} onChange={(e) => setEduForm((f) => ({ ...f, description: e.target.value }))} rows={2} /></label>
                          <div style={{ display: 'flex', gap: '8px' }}>
                            <button className="primary-btn" disabled={!eduForm.institution?.trim() || resumeSaving || getEduYearErrors(eduForm.start_year, eduForm.end_year, eduForm.is_current).start_year ||
    getEduYearErrors(eduForm.start_year, eduForm.end_year, eduForm.is_current).end_year} onClick={saveEdu}>{resumeSaving ? 'Saving...' : 'Save'}</button>
                            <button className="ghost-btn" onClick={cancelEdu}>Cancel</button>
                          </div>
                        </div>
                      ) : (
                        <div key={entry.id} className="resume-entry">
                          <div className="resume-entry-main">
                            <strong>{entry.institution}</strong>
                            {entry.degree && <span> · {entry.degree}</span>}
                            {entry.field_of_study && <span> in {entry.field_of_study}</span>}
                            <p className="muted">{entry.start_year || '?'} – {entry.is_current ? 'Present' : (entry.end_year || '?')}</p>
                            {entry.description && <p>{entry.description}</p>}
                          </div>
                          <div className="card-actions">
                            <button className="ghost-btn" onClick={() => startEditEdu(entry)}>Edit</button>
                            <button className="ghost-btn" onClick={() => deleteEdu(entry.id)}>Delete</button>
                          </div>
                        </div>
                      )
                    ))}
                  </section>

                  <section className="panel">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <h2>Awards &amp; Honours</h2>
                      {editingAwardId !== 'new' && <button className="primary-btn" onClick={startAddAward}>+ Add</button>}
                    </div>
                    {editingAwardId === 'new' && (
                      <div className="stack-block">
                        <div className="summary-grid">
                          <label className="field">Title *<input value={awardForm.title || ''} onChange={(e) => setAwardForm((f) => ({ ...f, title: e.target.value }))} placeholder="e.g. Dean's List" /></label>
                          <label className="field">Issuer<input value={awardForm.issuer || ''} onChange={(e) => setAwardForm((f) => ({ ...f, issuer: e.target.value }))} placeholder="e.g. MIT" /></label>
                          <div style={{position: 'relative'}}><label className="field">Year<input type="number" value={awardForm.awarded_year || ''} onChange={(e) => setAwardForm((f) => ({ ...f, awarded_year: e.target.value }))} onBlur={() => setAwardTouched({ ...awardTouched, year: true })} placeholder="2022" min={1900} max={new Date().getFullYear()} /></label>{awardTouched.year && getAwardYearError(awardForm.awarded_year) && <span style={{ color: 'red', fontSize: '0.78em', position: 'absolute' }}>{getAwardYearError(awardForm.awarded_year)}</span>}</div>
                        </div>
                        <label className="field">Description<textarea value={awardForm.description || ''} onChange={(e) => setAwardForm((f) => ({ ...f, description: e.target.value }))} rows={2} /></label>
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <button className="primary-btn" disabled={!awardForm.title?.trim() || resumeSaving || getAwardYearError(awardForm.awarded_year)} onClick={saveAward}>{resumeSaving ? 'Saving...' : 'Save'}</button>
                          <button className="ghost-btn" onClick={cancelAward}>Cancel</button>
                        </div>
                      </div>
                    )}
                    {resumeAwards.length === 0 && editingAwardId !== 'new' && <p className="muted">No awards yet.</p>}
                    {resumeAwards.map((entry) => (
                      editingAwardId === entry.id ? (
                        <div key={entry.id} className="stack-block">
                          <div className="summary-grid">
                            <label className="field">Title *<input value={awardForm.title || ''} onChange={(e) => setAwardForm((f) => ({ ...f, title: e.target.value }))} /></label>
                            <label className="field">Issuer<input value={awardForm.issuer || ''} onChange={(e) => setAwardForm((f) => ({ ...f, issuer: e.target.value }))} /></label>
                            <div style={{position: 'relative'}}><label className="field">Year<input type="number" value={awardForm.awarded_year || ''} onChange={(e) => setAwardForm((f) => ({ ...f, awarded_year: e.target.value }))} onBlur={() => setAwardTouched({ ...awardTouched, year: true })} min={1900} max={new Date().getFullYear()} /></label>{awardTouched.year && getAwardYearError(awardForm.awarded_year) && <span style={{ color: 'red', fontSize: '0.78em', position: 'absolute' }}>{getAwardYearError(awardForm.awarded_year)}</span>}</div>
                          </div>
                          <label className="field">Description<textarea value={awardForm.description || ''} onChange={(e) => setAwardForm((f) => ({ ...f, description: e.target.value }))} rows={2} /></label>
                          <div style={{ display: 'flex', gap: '8px' }}>
                            <button className="primary-btn" disabled={!awardForm.title?.trim() || resumeSaving || getAwardYearError(awardForm.awarded_year)} onClick={saveAward}>{resumeSaving ? 'Saving...' : 'Save'}</button>
                            <button className="ghost-btn" onClick={cancelAward}>Cancel</button>
                          </div>
                        </div>
                      ) : (
                        <div key={entry.id} className="resume-entry">
                          <div className="resume-entry-main">
                            <strong>{entry.title}</strong>
                            {entry.issuer && <span> · {entry.issuer}</span>}
                            {entry.awarded_year && <span className="muted"> ({entry.awarded_year})</span>}
                            {entry.description && <p>{entry.description}</p>}
                          </div>
                          <div className="card-actions">
                            <button className="ghost-btn" onClick={() => startEditAward(entry)}>Edit</button>
                            <button className="ghost-btn" onClick={() => deleteAward(entry.id)}>Delete</button>
                          </div>
                        </div>
                      )
                    ))}
                  </section>

                  {resumeProjects.some((p) => p.skills.length > 0) && (
                    <section className="panel">
                      <h2>Skills by Project</h2>
                      <p className="muted">Derived from your project analyses. Included when generating your resume PDF.</p>
                      <div className="stack-block">
                        {resumeProjects.map((p) => (
                          p.skills.length > 0 && (
                            <div key={p.project_id}>
                              <h3>{p.project_name || p.project_id}</h3>
                              <div className="badge-row">
                                {p.skills.map((s, i) => (
                                  <span key={i} className="skill-badge">{s.name} <span className="muted">· {s.expertise}</span></span>
                                ))}
                              </div>
                            </div>
                          )
                        ))}
                      </div>
                    </section>
                  )}
                </>
              )}
              </motion.div>
            </AnimatePresence>
          )}
        </main>
      </div>
    </div>
  );
}

export default Homepage;
