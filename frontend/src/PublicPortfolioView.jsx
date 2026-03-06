import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { dashboardApi } from './api';

function toCsvList(value) {
  return String(value || '')
    .split(',')
    .map((entry) => entry.trim())
    .filter(Boolean);
}

function readFiltersFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return {
    q: params.get('q') || '',
    date_from: params.get('date_from') || '',
    date_to: params.get('date_to') || '',
    sort: params.get('sort') || 'rank_desc',
    project_ids: params.getAll('project_ids'),
    skills: params.getAll('skills'),
  };
}

function writeFiltersToUrl(filters) {
  const params = new URLSearchParams();
  if (filters.q) params.set('q', filters.q);
  if (filters.date_from) params.set('date_from', filters.date_from);
  if (filters.date_to) params.set('date_to', filters.date_to);
  if (filters.sort) params.set('sort', filters.sort);
  (filters.project_ids || []).forEach((v) => v && params.append('project_ids', v));
  (filters.skills || []).forEach((v) => v && params.append('skills', v));
  const query = params.toString();
  window.history.replaceState({}, '', `${window.location.pathname}${query ? `?${query}` : ''}`);
}

function formatDateOnly(value) {
  if (!value) return 'N/A';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? 'N/A' : parsed.toLocaleDateString();
}

function Section({ title, empty, children }) {
  return (
    <section className="panel">
      <h2>{title}</h2>
      {empty ? <p className="muted">{empty}</p> : children}
    </section>
  );
}

function PublicPortfolioView({ publicSlug }) {
  const urlFilters = useMemo(() => readFiltersFromUrl(), []);
  const [q, setQ] = useState(urlFilters.q);
  const [dateFrom, setDateFrom] = useState(urlFilters.date_from);
  const [dateTo, setDateTo] = useState(urlFilters.date_to);
  const [skillsInput, setSkillsInput] = useState((urlFilters.skills || []).join(', '));
  const [projectIdsInput, setProjectIdsInput] = useState((urlFilters.project_ids || []).join(', '));
  const [sort, setSort] = useState(urlFilters.sort || 'rank_desc');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [payload, setPayload] = useState(null);

  const loadDashboard = useCallback(
    async (filters) => {
      setLoading(true);
      setError('');
      try {
        setPayload(await dashboardApi.getPublicDashboard(publicSlug, filters));
      } catch (err) {
        setError(err.message || 'Unable to load public portfolio.');
        setPayload(null);
      } finally {
        setLoading(false);
      }
    },
    [publicSlug]
  );

  useEffect(() => {
    loadDashboard({
      q: urlFilters.q || undefined,
      date_from: urlFilters.date_from || undefined,
      date_to: urlFilters.date_to || undefined,
      sort: urlFilters.sort || 'rank_desc',
      project_ids: urlFilters.project_ids || [],
      skills: urlFilters.skills || [],
    });
  }, [loadDashboard, urlFilters]);

  const applyFilters = async (event) => {
    event.preventDefault();
    const filters = {
      q: q.trim() || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      sort,
      project_ids: toCsvList(projectIdsInput),
      skills: toCsvList(skillsInput),
    };
    writeFiltersToUrl(filters);
    await loadDashboard(filters);
  };

  const dashboard = payload?.dashboard || {};
  const projects = dashboard.projects || [];
  const topProjects = dashboard.top_projects || [];
  const skillsTimeline = dashboard.skills_timeline || [];
  const heatmap = dashboard.activity_heatmap || [];
  const showcases = dashboard.showcases || [];
  const ownerUsername = payload?.owner?.username || payload?.owner?.display_name || 'User';

  return (
    <div className="screen-shell">
      <div className="dashboard-shell">
        <header className="dashboard-header">
          <div>
            <p className="eyebrow">Public Portfolio</p>
            <h1>{ownerUsername}</h1>
          </div>
        </header>

        {error && <p className="error-banner">{error}</p>}

        <section className="panel">
          <details className="stack-block">
            <summary>Search and Filters</summary>
            <form className="stack-block" onSubmit={applyFilters}>
              <label className="field">Search<input type="text" value={q} onChange={(event) => setQ(event.target.value)} placeholder="Project or skill" /></label>
              <div className="summary-grid">
                <label className="field">Date from<input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} /></label>
                <label className="field">Date to<input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} /></label>
              </div>
              <label className="field">Skills (comma-separated)<input type="text" value={skillsInput} onChange={(event) => setSkillsInput(event.target.value)} /></label>
              <label className="field">Project IDs (comma-separated)<input type="text" value={projectIdsInput} onChange={(event) => setProjectIdsInput(event.target.value)} /></label>
              <label className="field">
                Sort
                <select value={sort} onChange={(event) => setSort(event.target.value)}>
                  <option value="rank_desc">Rank (high to low)</option>
                  <option value="rank_asc">Rank (low to high)</option>
                  <option value="name_asc">Name (A-Z)</option>
                  <option value="name_desc">Name (Z-A)</option>
                  <option value="date_desc">Date (newest first)</option>
                  <option value="date_asc">Date (oldest first)</option>
                </select>
              </label>
              <button className="primary-btn" type="submit" disabled={loading}>{loading ? 'Applying...' : 'Apply Filters'}</button>
            </form>
          </details>
        </section>

        {loading ? (
          <Section title="Loading" empty="Loading public dashboard..." />
        ) : (
          <>
            <Section title="Projects" empty={projects.length === 0 ? 'No projects match current filters.' : ''}>
              <div className="project-grid">{projects.map((project) => <article key={project.id} className="project-card"><h3>{project.name}</h3><p>Created: {project.created_at || 'N/A'}</p><p>Rank score: {project.metrics?.rank_score ?? 'N/A'}</p></article>)}</div>
            </Section>

            <Section title="Top Projects" empty={topProjects.length === 0 ? 'No top projects available.' : ''}>
              <div className="top-list">{topProjects.map((project) => <article key={project.project_id} className="top-card"><h3>{project.project_name || project.name || project.project_id}</h3><p>Rank score: {project.rank_score ?? 'N/A'}</p></article>)}</div>
            </Section>

            <Section title="Skills Timeline" empty={skillsTimeline.length === 0 ? 'No timeline events for current filters.' : ''}>
              <div className="timeline">{skillsTimeline.map((event, index) => <article key={`${event.project_id}-${event.skill}-${index}`} className="timeline-item"><p className="timeline-date">{formatDateOnly(event.first_seen_ts)}</p><div><h3>{event.skill}</h3><p className="muted">{event.project_name || event.project_id}</p></div></article>)}</div>
            </Section>

            <Section title="Activity Heatmap Buckets" empty={heatmap.length === 0 ? 'No activity buckets for current filters.' : ''}>
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Date</th><th>Activity Count</th></tr></thead>
                  <tbody>{heatmap.map((bucket, index) => <tr key={`${bucket.bucket_date}-${index}`}><td>{formatDateOnly(bucket.bucket_date)}</td><td>{bucket.activity_count ?? 0}</td></tr>)}</tbody>
                </table>
              </div>
            </Section>

            <Section title="Showcase Items" empty={showcases.length === 0 ? 'No showcase items available.' : ''}>
              <div className="project-grid">{showcases.map((showcase) => <article key={showcase.id} className="project-card"><h3>{showcase.content?.title || showcase.project_name || showcase.project_id}</h3><p className="muted">{showcase.content?.summary_text || 'No summary saved.'}</p></article>)}</div>
            </Section>
          </>
        )}
      </div>
    </div>
  );
}

export default PublicPortfolioView;
