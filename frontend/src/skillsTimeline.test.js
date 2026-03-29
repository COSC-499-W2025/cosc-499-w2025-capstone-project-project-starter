import {
  buildSkillProgressionTimeline,
  formatConfidencePercent,
  formatSignedPercent,
} from './skillsTimeline';

describe('buildSkillProgressionTimeline', () => {
  test('groups events by skill and computes progression metadata', () => {
    const output = buildSkillProgressionTimeline([
      {
        project_id: 'p1',
        project_name: 'Project One',
        snapshot_id: 's1',
        skill: 'React',
        observed_at: '2024-01-10T00:00:00Z',
        signal: {
          stage: 'emerging',
          confidence: 0.42,
          confidence_delta: null,
          hits: 3,
          cumulative_hits: 3,
          observation_index: 1,
        },
      },
      {
        project_id: 'p1',
        project_name: 'Project One',
        snapshot_id: 's2',
        skill: 'React',
        observed_at: '2024-04-10T00:00:00Z',
        signal: {
          stage: 'developing',
          confidence: 0.71,
          confidence_delta: 0.29,
          hits: 8,
          cumulative_hits: 11,
          observation_index: 2,
        },
      },
      {
        project_id: 'p2',
        project_name: 'Project Two',
        snapshot_id: 's3',
        skill: 'Node',
        observed_at: '2024-02-10T00:00:00Z',
        signal: {
          stage: 'developing',
          confidence: 0.62,
          confidence_delta: null,
          hits: 5,
          cumulative_hits: 5,
          observation_index: 1,
        },
      },
      {
        project_id: 'p2',
        project_name: 'Project Two',
        snapshot_id: 's4',
        skill: 'React',
        observed_at: '2024-07-20T00:00:00Z',
        signal: {
          stage: 'advanced',
          confidence: 0.87,
          confidence_delta: 0.16,
          hits: 18,
          cumulative_hits: 29,
          observation_index: 3,
        },
      },
    ]);

    expect(output.summary).toEqual({
      total_skills: 2,
      total_events: 4,
      progressing_skills: 1,
    });

    expect(output.tracks[0].skill).toBe('React');
    expect(output.tracks[0].stage_path).toEqual(['emerging', 'developing', 'advanced']);
    expect(output.tracks[0].confidence_change).toBe(0.45);
    expect(output.tracks[0].progressed).toBe(true);

    expect(output.tracks[1].skill).toBe('Node');
    expect(output.tracks[1].stage_path).toEqual(['developing']);
    expect(output.tracks[1].progressed).toBe(false);
  });

  test('falls back gracefully when timeline signals are missing', () => {
    const output = buildSkillProgressionTimeline([
      {
        project_id: 'p1',
        project_name: 'Project One',
        snapshot_id: 's1',
        skill: 'Python',
        first_seen_ts: '2024-01-02T00:00:00Z',
        max_prob: 0.56,
        hits: 12,
      },
      {
        project_id: 'p1',
        project_name: 'Project One',
        snapshot_id: 's2',
        skill: 'Python',
        first_seen_ts: '2024-02-02T00:00:00Z',
        max_prob: 0.71,
        hits: 9,
      },
      {
        project_id: 'p2',
        project_name: 'Project Two',
        snapshot_id: 's3',
        skill: '',
        first_seen_ts: '2024-03-02T00:00:00Z',
      },
    ]);

    expect(output.tracks).toHaveLength(1);
    expect(output.tracks[0].events).toHaveLength(2);
    expect(output.tracks[0].latest_stage).toBe('developing');
    expect(output.tracks[0].events[1].cumulative_hits).toBe(21);
    expect(output.tracks[0].events[1].confidence_delta).toBe(0.15);
  });
});

describe('timeline formatting helpers', () => {
  test('formats confidence percentages', () => {
    expect(formatConfidencePercent(0.87)).toBe('87%');
    expect(formatConfidencePercent(null)).toBe('N/A');
  });

  test('formats signed deltas', () => {
    expect(formatSignedPercent(0.16)).toBe('+16%');
    expect(formatSignedPercent(-0.07)).toBe('-7%');
    expect(formatSignedPercent(0)).toBe('0%');
  });
});
