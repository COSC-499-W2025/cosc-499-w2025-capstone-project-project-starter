import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import PublicPortfolioView from './PublicPortfolioView.jsx';
import { dashboardApi } from './api';

jest.mock('./api', () => ({
  dashboardApi: {
    getPublicDashboard: jest.fn(),
  },
}));

jest.mock(
  'lucide-react',
  () => ({
    Sun: () => null,
    Moon: () => null,
  }),
  { virtual: true }
);

function mockDashboardPayload() {
  return {
    visibility_config: {
      projects: true,
      skills_timeline: true,
      top_projects: true,
      activity_heatmap: true,
      showcases: true,
    },
    dashboard: {
      projects: [{ id: 'p1', name: 'Project One', created_at: '2024-01-01', metrics: { rank_score: 9.4 } }],
      top_projects: [{ project_id: 'p1', project_name: 'Project One', rank_score: 9.4 }],
      skills_timeline: [
        {
          project_id: 'p1',
          project_name: 'Project One',
          snapshot_id: 's1',
          skill: 'react',
          observed_at: '2024-01-02T00:00:00Z',
          first_seen_ts: '2024-01-02T00:00:00Z',
          signal: {
            stage: 'emerging',
            confidence: 0.45,
            hits: 3,
            cumulative_hits: 3,
            observation_index: 1,
          },
        },
        {
          project_id: 'p1',
          project_name: 'Project One',
          snapshot_id: 's2',
          skill: 'react',
          observed_at: '2024-05-02T00:00:00Z',
          first_seen_ts: '2024-01-02T00:00:00Z',
          signal: {
            stage: 'developing',
            confidence: 0.73,
            confidence_delta: 0.28,
            hits: 8,
            cumulative_hits: 11,
            observation_index: 2,
          },
        },
      ],
      activity_heatmap: [
        {
          bucket_start: '2024-01-02T00:00:00Z',
          bucket_date: '2024-01-02',
          activity_count: 5,
          snapshot_count: 2,
          commit_count: 3,
          project_names: ['Project One'],
        },
      ],
      showcases: [],
    },
  };
}

describe('PublicPortfolioView', () => {
  beforeEach(() => {
    dashboardApi.getPublicDashboard.mockResolvedValue(mockDashboardPayload());
    window.history.replaceState({}, '', '/portfolio/public-test-slug');
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  test('shows only public tabs', async () => {
    render(<PublicPortfolioView publicSlug="public-test-slug" />);

    await waitFor(() => {
      expect(dashboardApi.getPublicDashboard).toHaveBeenCalled();
    });

    expect(screen.getByRole('button', { name: /^projects$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /skills timeline/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /top projects/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /activity heatmap/i })).toBeInTheDocument();

    expect(screen.queryByText(/preferences/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/upload/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/compare/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/dashboard mode/i)).not.toBeInTheDocument();
  });

  test('search and filter apply in public mode', async () => {
    dashboardApi.getPublicDashboard
      .mockResolvedValueOnce(mockDashboardPayload())
      .mockResolvedValueOnce({
        ...mockDashboardPayload(),
        dashboard: {
          ...mockDashboardPayload().dashboard,
          activity_heatmap: [
            {
              bucket_start: '2024-01-03T00:00:00Z',
              bucket_date: '2024-01-03',
              activity_count: 2,
              snapshot_count: 1,
              commit_count: 1,
              project_names: ['Project One'],
            },
          ],
        },
      });

    render(<PublicPortfolioView publicSlug="public-test-slug" />);

    await waitFor(() => {
      expect(dashboardApi.getPublicDashboard).toHaveBeenCalledTimes(1);
    });

    fireEvent.change(screen.getByPlaceholderText(/project or skill/i), {
      target: { value: 'react' },
    });
    fireEvent.change(screen.getByLabelText(/skills \(comma-separated\)/i), {
      target: { value: 'react, node' },
    });

    fireEvent.click(screen.getByRole('button', { name: /apply filters/i }));

    await waitFor(() => {
      expect(dashboardApi.getPublicDashboard).toHaveBeenCalledTimes(2);
    });

    const secondCallArgs = dashboardApi.getPublicDashboard.mock.calls[1];
    expect(secondCallArgs[0]).toBe('public-test-slug');
    expect(secondCallArgs[1]).toMatchObject({
      q: 'react',
      skills: ['react', 'node'],
    });

    fireEvent.click(screen.getByRole('button', { name: /activity heatmap/i }));
    expect(screen.getAllByRole('button', { name: /heatmap bucket/i })).toHaveLength(1);
    expect(screen.getByRole('status')).toHaveTextContent('Activity:');
    expect(screen.getByRole('status')).toHaveTextContent('2');
  });

  test('hides disabled public sections', async () => {
    dashboardApi.getPublicDashboard.mockResolvedValue({
      visibility_config: {
        projects: true,
        skills_timeline: false,
        top_projects: false,
        activity_heatmap: false,
        showcases: false,
      },
      dashboard: {
        projects: [{ id: 'p1', name: 'Project One', created_at: '2024-01-01', metrics: { rank_score: 9.4 } }],
      },
    });

    render(<PublicPortfolioView publicSlug="public-test-slug" />);

    await waitFor(() => {
      expect(dashboardApi.getPublicDashboard).toHaveBeenCalled();
    });

    expect(screen.getByRole('button', { name: /^projects$/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /skills timeline/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /top projects/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /activity heatmap/i })).not.toBeInTheDocument();
  });

  test('renders progression details in skills timeline', async () => {
    render(<PublicPortfolioView publicSlug="public-test-slug" />);

    await waitFor(() => {
      expect(dashboardApi.getPublicDashboard).toHaveBeenCalled();
    });

    fireEvent.click(screen.getByRole('button', { name: /skills timeline/i }));

    expect(screen.getByText('Progression: Emerging -> Developing • Confidence +28%')).toBeInTheDocument();
    expect(screen.getByText('Observation #2')).toBeInTheDocument();
    expect(screen.getByText('Confidence: 73% (+28% vs previous) • Hits: 8 (total 11)')).toBeInTheDocument();
  });
});
