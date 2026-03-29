import { fireEvent, render, screen } from '@testing-library/react';
import TopProjectShowcase from './TopProjectShowcase';

describe('TopProjectShowcase', () => {
  const projects = [
    {
      project_id: 'p1',
      project_name: 'Alpha',
      rank_score: 9.8,
      selection_features: { user_commits: 10, total_commits: 15, contributor_count: 2 },
      process_narrative: 'Project evolved from prototype to production.',
      milestones: [
        {
          timestamp: '2024-01-01T00:00:00Z',
          summary: 'Initial snapshot',
          type: 'project_started',
          snapshot_label: 'v1-initial',
          snapshot_id: 'snap-001',
          metrics: { commit_count: 3, total_files: 12, total_lines: 420, skills_detected: 4 },
        },
        {
          timestamp: '2024-01-15T00:00:00Z',
          summary: 'Incremental upload milestone',
          type: 'snapshot_update',
          snapshot_label: 'v2-incremental',
        },
        { timestamp: '2024-02-01T00:00:00Z', summary: 'Latest stable release', type: 'latest_state' },
      ],
    },
    {
      project_id: 'p2',
      project_name: 'Beta',
      rank_score: 8.2,
      selection_features: { user_commits: 8, total_commits: 11, contributor_count: 1 },
      process_narrative: 'Consistent iterative improvements.',
      milestones: [{ timestamp: '2024-03-01T00:00:00Z', summary: 'Versioned milestone' }],
    },
    {
      project_id: 'p3',
      project_name: 'Gamma',
      rank_score: 7.1,
      selection_features: { user_commits: 6, total_commits: 8, contributor_count: 1 },
      process_narrative: 'Focused on refactoring and test hardening.',
      milestones: [],
    },
    {
      project_id: 'p4',
      project_name: 'Delta',
      rank_score: 6.4,
      selection_features: { user_commits: 4, total_commits: 6, contributor_count: 1 },
      process_narrative: 'Should not render because showcase is top 3.',
      milestones: [],
    },
  ];

  test('renders exactly top 3 projects', () => {
    render(<TopProjectShowcase projects={projects} loading={false} />);

    expect(screen.getByText('Alpha')).toBeInTheDocument();
    expect(screen.getByText('Beta')).toBeInTheDocument();
    expect(screen.getByText('Gamma')).toBeInTheDocument();
    expect(screen.queryByText('Delta')).not.toBeInTheDocument();
  });

  test('renders process narrative and timeline evidence', () => {
    render(<TopProjectShowcase projects={projects} loading={false} />);

    expect(screen.getByText('Project evolved from prototype to production.')).toBeInTheDocument();
    expect(screen.getByText('Initial snapshot')).toBeInTheDocument();
    expect(screen.getByText('Latest stable release')).toBeInTheDocument();
    expect(screen.getByText('v2-incremental')).toBeInTheDocument();
    expect(screen.getByText('Incremental Upload')).toBeInTheDocument();
  });

  test('supports comparison and progression view toggle', () => {
    render(<TopProjectShowcase projects={projects} loading={false} />);

    expect(screen.getByRole('button', { name: /progression/i })).toBeInTheDocument();
    const comparisonBtn = screen.getByRole('button', { name: /comparison/i });
    fireEvent.click(comparisonBtn);
    expect(comparisonBtn).toHaveClass('active');
  });

  test('reveals milestone details when clicked', () => {
    render(<TopProjectShowcase projects={projects} loading={false} />);

    expect(screen.queryByText(/Snapshot ID:/i)).not.toBeInTheDocument();
    fireEvent.click(screen.getByText('Initial snapshot'));

    expect(screen.getByText(/Snapshot ID:/i)).toBeInTheDocument();
    expect(screen.getAllByText(/v1-initial/i).length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText(/Commits: 3/i)).toBeInTheDocument();
  });
});
