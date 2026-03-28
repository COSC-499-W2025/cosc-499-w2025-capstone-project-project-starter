import { fireEvent, render, screen } from '@testing-library/react';
import ActivityHeatmap from './ActivityHeatmap';

describe('ActivityHeatmap', () => {
  test('renders intensity-mapped cells and updates details context on hover', () => {
    const buckets = [
      {
        bucket_start: '2024-01-01T00:00:00Z',
        bucket_date: '2024-01-01',
        activity_count: 1,
        snapshot_count: 1,
        commit_count: 0,
        project_names: ['Alpha'],
      },
      {
        bucket_start: '2024-01-02T00:00:00Z',
        bucket_date: '2024-01-02',
        activity_count: 12,
        snapshot_count: 2,
        commit_count: 10,
        project_names: ['Alpha', 'Beta'],
      },
    ];

    render(<ActivityHeatmap buckets={buckets} />);

    const cells = screen.getAllByRole('button', { name: /heatmap bucket/i });
    expect(cells).toHaveLength(2);

    expect(cells[0]).toHaveClass('intensity-1');
    expect(cells[1]).toHaveClass('intensity-4');

    fireEvent.mouseEnter(cells[1]);
    const details = screen.getByRole('status');
    expect(details).toHaveTextContent('Activity:');
    expect(details).toHaveTextContent('12');
    expect(details).toHaveTextContent('Commits:');
    expect(details).toHaveTextContent('10');
    expect(details).toHaveTextContent('Projects:');
    expect(details).toHaveTextContent('Alpha, Beta');
  });

  test('renders empty state when no buckets are present', () => {
    render(<ActivityHeatmap buckets={[]} emptyText="Nothing to plot." />);
    expect(screen.getByText('Nothing to plot.')).toBeInTheDocument();
  });
});
