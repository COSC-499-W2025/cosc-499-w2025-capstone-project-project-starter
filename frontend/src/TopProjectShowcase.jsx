import React, { useMemo, useState } from 'react';

function formatTs(value) {
  if (!value) return 'N/A';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? 'N/A' : parsed.toLocaleDateString();
}

function formatMilestoneType(value) {
  if (!value) return 'Milestone';
  if (value === 'project_started') return 'Project Started';
  if (value === 'snapshot_update') return 'Incremental Upload';
  if (value === 'latest_state') return 'Latest State';
  return String(value)
    .split('_')
    .map((part) => (part ? part[0].toUpperCase() + part.slice(1) : part))
    .join(' ');
}

function TopProjectShowcase({
  projects = [],
  loading = false,
  emptyText = 'No ranked projects yet.',
  title = 'Top 3 Project Showcase',
}) {
  const [layout, setLayout] = useState('progression');
  const [expandedMilestones, setExpandedMilestones] = useState({});
  const topThree = useMemo(() => (Array.isArray(projects) ? projects.slice(0, 3) : []), [projects]);

  const toggleMilestone = (projectId, milestoneIndex) => {
    const key = `${projectId || 'project'}-${milestoneIndex}`;
    setExpandedMilestones((current) => ({
      ...current,
      [key]: !current[key],
    }));
  };

  if (loading) {
    return <p>Loading top projects...</p>;
  }

  if (topThree.length === 0) {
    return <p>{emptyText}</p>;
  }

  return (
    <div className="top-showcase-shell">
      <div className="top-showcase-header">
        <h3>{title}</h3>
        <div className="top-showcase-layout-toggle">
          <button
            type="button"
            className={layout === 'progression' ? 'active' : ''}
            onClick={() => setLayout('progression')}
          >
            Progression
          </button>
          <button
            type="button"
            className={layout === 'comparison' ? 'active' : ''}
            onClick={() => setLayout('comparison')}
          >
            Comparison
          </button>
        </div>
      </div>

      <div className={layout === 'comparison' ? 'top-showcase-grid comparison' : 'top-showcase-grid progression'}>
        {topThree.map((project, index) => {
          const features = project.selection_features || {};
          const milestones = Array.isArray(project.milestones) ? project.milestones : [];
          return (
            <article key={project.project_id || `${project.project_name}-${index}`} className="top-showcase-card">
              <div className="top-showcase-rank">#{index + 1}</div>
              <div className="top-showcase-main">
                <h4>{project.project_name || project.project_id}</h4>
                <p className="top-showcase-score">Rank score: {project.rank_score?.toFixed?.(2) ?? 'N/A'}</p>
                <div className="top-showcase-metrics">
                  <span>User commits: {features.user_commits ?? 0}</span>
                  <span>Total commits: {features.total_commits ?? 0}</span>
                  <span>Contributors: {features.contributor_count ?? 0}</span>
                </div>
                <p className="top-showcase-narrative">{project.process_narrative || 'No process narrative available.'}</p>

                <div className="top-showcase-timeline">
                  <p className="top-showcase-timeline-title">Evolution Timeline</p>
                  {milestones.length === 0 ? (
                    <p className="muted">No milestones available.</p>
                  ) : (
                    <ul>
                      {milestones.map((milestone, milestoneIndex) => (
                        <li key={`${project.project_id}-ms-${milestoneIndex}`}>
                          <span className="milestone-dot" aria-hidden="true" />
                          <div className="milestone-content">
                            <button
                              type="button"
                              className="milestone-toggle"
                              onClick={() => toggleMilestone(project.project_id, milestoneIndex)}
                            >
                              <span className="milestone-date">{formatTs(milestone.timestamp)}</span>
                              <span className="milestone-type">{formatMilestoneType(milestone.type)}</span>
                              {milestone.snapshot_label && (
                                <span className="milestone-label">{milestone.snapshot_label}</span>
                              )}
                              <span className="milestone-summary">{milestone.summary || milestone.type || 'Milestone'}</span>
                              <span className="milestone-expand-hint">
                                {expandedMilestones[`${project.project_id || 'project'}-${milestoneIndex}`]
                                  ? 'Hide details'
                                  : 'Show details'}
                              </span>
                            </button>
                            {expandedMilestones[`${project.project_id || 'project'}-${milestoneIndex}`] && (
                              <div className="milestone-details">
                                {milestone.snapshot_label && (
                                  <p>
                                    <strong>Snapshot:</strong> {milestone.snapshot_label}
                                  </p>
                                )}
                                {milestone.snapshot_id && (
                                  <p>
                                    <strong>Snapshot ID:</strong> {milestone.snapshot_id}
                                  </p>
                                )}
                                {milestone.metrics && (
                                  <div className="milestone-metrics">
                                    {milestone.metrics.commit_count !== undefined && (
                                      <span>Commits: {milestone.metrics.commit_count}</span>
                                    )}
                                    {milestone.metrics.total_files !== undefined && (
                                      <span>Files: {milestone.metrics.total_files}</span>
                                    )}
                                    {milestone.metrics.total_lines !== undefined && (
                                      <span>Lines: {milestone.metrics.total_lines}</span>
                                    )}
                                    {milestone.metrics.skills_detected !== undefined && (
                                      <span>Skills: {milestone.metrics.skills_detected}</span>
                                    )}
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}

export default TopProjectShowcase;
