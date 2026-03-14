import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import PublicPortfolioView from './PublicPortfolioView.jsx';
import { dashboardApi } from './api';

jest.mock('./api', () => ({
  dashboardApi: {
    getPublicDashboard: jest.fn(),
  },
}));

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
      skills_timeline: [{ project_id: 'p1', project_name: 'Project One', skill: 'react', first_seen_ts: '2024-01-02' }],
      activity_heatmap: [],
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

    expect(screen.queryByText(/preferences/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/upload/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/compare/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/dashboard mode/i)).not.toBeInTheDocument();
  });

  test('search and filter apply in public mode', async () => {
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
  });
});
