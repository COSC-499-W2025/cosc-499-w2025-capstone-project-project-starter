const STAGE_LABELS = {
  emerging: 'Emerging',
  developing: 'Developing',
  advanced: 'Advanced',
};

function toFiniteNumber(value, fallback = null) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function clampConfidence(value) {
  const parsed = toFiniteNumber(value, null);
  if (parsed === null) return null;
  if (parsed < 0) return 0;
  if (parsed > 1) return 1;
  return parsed;
}

function toNonNegativeInt(value, fallback = 0) {
  const parsed = Number.parseInt(String(value), 10);
  if (!Number.isFinite(parsed) || parsed < 0) return fallback;
  return parsed;
}

function toPositiveInt(value, fallback = 1) {
  const parsed = Number.parseInt(String(value), 10);
  if (!Number.isFinite(parsed) || parsed <= 0) return fallback;
  return parsed;
}

function isValidStage(value) {
  return value === 'emerging' || value === 'developing' || value === 'advanced';
}

function inferStage(confidence, cumulativeHits, observations) {
  const conf = confidence ?? 0;
  if (conf >= 0.8 && cumulativeHits >= 25) return 'advanced';
  if (conf >= 0.55 || cumulativeHits >= 10 || observations >= 3) return 'developing';
  return 'emerging';
}

function toTimelineTimestamp(event) {
  return String(event?.observed_at || event?.first_seen_ts || '').trim() || null;
}

function sortKey(timestamp) {
  if (!timestamp) return Number.MAX_SAFE_INTEGER;
  const parsed = new Date(timestamp);
  if (Number.isNaN(parsed.getTime())) return Number.MAX_SAFE_INTEGER;
  return parsed.getTime();
}

function round4(value) {
  return Math.round(value * 10000) / 10000;
}

function toTitleCaseStage(stage) {
  return STAGE_LABELS[stage] || STAGE_LABELS.emerging;
}

export function buildSkillProgressionTimeline(rawEvents) {
  const source = Array.isArray(rawEvents) ? rawEvents : [];
  const sorted = source
    .filter((event) => event && typeof event === 'object')
    .slice()
    .sort((left, right) => {
      const leftTs = toTimelineTimestamp(left);
      const rightTs = toTimelineTimestamp(right);
      return (
        sortKey(leftTs) - sortKey(rightTs) ||
        String(left.skill || '').localeCompare(String(right.skill || '')) ||
        String(left.project_id || '').localeCompare(String(right.project_id || ''))
      );
    });

  const tracksBySkill = new Map();

  sorted.forEach((row, index) => {
    const skill = String(row.skill || '').trim();
    if (!skill) return;

    const key = skill.toLocaleLowerCase();
    const existing = tracksBySkill.get(key) || {
      skill_key: key,
      skill,
      events: [],
    };

    const signal = row.signal && typeof row.signal === 'object' ? row.signal : {};
    const prevEvent = existing.events[existing.events.length - 1] || null;

    const confidence = clampConfidence(signal.confidence ?? row.max_prob ?? row.confidence);
    const hits = toNonNegativeInt(signal.hits ?? row.hits, 0);
    const cumulativeHits = toNonNegativeInt(
      signal.cumulative_hits,
      (prevEvent ? prevEvent.cumulative_hits : 0) + hits
    );
    const observationIndex = toPositiveInt(
      signal.observation_index,
      prevEvent ? prevEvent.observation_index + 1 : 1
    );

    const stage = isValidStage(signal.stage)
      ? signal.stage
      : inferStage(confidence, cumulativeHits, observationIndex);

    const explicitDelta = toFiniteNumber(signal.confidence_delta, null);
    const derivedDelta =
      confidence !== null && prevEvent && prevEvent.confidence !== null
        ? round4(confidence - prevEvent.confidence)
        : null;

    existing.events.push({
      id: `${row.project_id || 'project'}-${row.snapshot_id || 'snapshot'}-${index}`,
      skill,
      project_id: row.project_id || null,
      project_name: row.project_name || null,
      timestamp: toTimelineTimestamp(row),
      first_seen_ts: row.first_seen_ts || null,
      stage,
      stage_label: toTitleCaseStage(stage),
      confidence,
      confidence_delta: explicitDelta === null ? derivedDelta : round4(explicitDelta),
      hits,
      cumulative_hits: cumulativeHits,
      observation_index: observationIndex,
    });

    tracksBySkill.set(key, existing);
  });

  const tracks = Array.from(tracksBySkill.values())
    .map((track) => {
      const events = track.events;
      const firstEvent = events[0];
      const lastEvent = events[events.length - 1];
      const stagePath = [];

      events.forEach((event) => {
        if (stagePath[stagePath.length - 1] !== event.stage) {
          stagePath.push(event.stage);
        }
      });

      const confidenceChange =
        firstEvent.confidence !== null && lastEvent.confidence !== null
          ? round4(lastEvent.confidence - firstEvent.confidence)
          : null;

      return {
        ...track,
        first_seen_ts: firstEvent.timestamp || firstEvent.first_seen_ts,
        latest_ts: lastEvent.timestamp || lastEvent.first_seen_ts,
        latest_stage: lastEvent.stage,
        latest_stage_label: lastEvent.stage_label,
        stage_path: stagePath,
        stage_path_labels: stagePath.map(toTitleCaseStage),
        confidence_change: confidenceChange,
        progressed: stagePath.length > 1 || events.length > 1,
      };
    })
    .sort((left, right) => {
      return (
        sortKey(right.latest_ts) - sortKey(left.latest_ts) ||
        left.skill.localeCompare(right.skill)
      );
    });

  return {
    tracks,
    summary: {
      total_skills: tracks.length,
      total_events: tracks.reduce((total, track) => total + track.events.length, 0),
      progressing_skills: tracks.filter((track) => track.progressed).length,
    },
  };
}

export function formatConfidencePercent(value) {
  if (value === null || value === undefined) return 'N/A';
  const parsed = toFiniteNumber(value, null);
  if (parsed === null) return 'N/A';
  return `${Math.round(parsed * 100)}%`;
}

export function formatSignedPercent(value) {
  const parsed = toFiniteNumber(value, null);
  if (parsed === null) return 'N/A';
  const percent = Math.round(parsed * 100);
  if (percent > 0) return `+${percent}%`;
  if (percent < 0) return `${percent}%`;
  return '0%';
}
