import React, { useMemo, useState } from 'react';

function formatBucketLabel(bucket) {
  const text = bucket?.bucket_start || bucket?.bucket_date;
  if (!text) return 'Unknown bucket';
  const parsed = new Date(text);
  if (Number.isNaN(parsed.getTime())) return String(text);
  return parsed.toLocaleString();
}

function toIntensityLevel(count, maxCount) {
  const safeCount = Number(count) || 0;
  if (safeCount <= 0 || maxCount <= 0) return 0;
  const ratio = safeCount / maxCount;
  if (ratio >= 0.75) return 4;
  if (ratio >= 0.5) return 3;
  if (ratio >= 0.25) return 2;
  return 1;
}

function ActivityHeatmap({ buckets = [], loading = false, emptyText = 'No activity data available.', title = 'Activity Heatmap' }) {
  const [activeBucketIndex, setActiveBucketIndex] = useState(null);

  const sortedBuckets = useMemo(() => {
    const source = Array.isArray(buckets) ? [...buckets] : [];
    source.sort((a, b) => {
      const left = String(a?.bucket_start || a?.bucket_date || '');
      const right = String(b?.bucket_start || b?.bucket_date || '');
      return left.localeCompare(right);
    });
    return source;
  }, [buckets]);

  const maxActivityCount = useMemo(
    () => sortedBuckets.reduce((max, bucket) => Math.max(max, Number(bucket?.activity_count) || 0), 0),
    [sortedBuckets]
  );

  const selectedBucket = useMemo(() => {
    if (sortedBuckets.length === 0) return null;
    if (typeof activeBucketIndex === 'number' && activeBucketIndex >= 0 && activeBucketIndex < sortedBuckets.length) {
      return sortedBuckets[activeBucketIndex];
    }
    return sortedBuckets[sortedBuckets.length - 1];
  }, [sortedBuckets, activeBucketIndex]);

  if (loading) {
    return <p>Loading activity heatmap...</p>;
  }

  if (sortedBuckets.length === 0) {
    return <p className="muted">{emptyText}</p>;
  }

  return (
    <div className="activity-heatmap-shell">
      <div className="activity-heatmap-header">
        <h3>{title}</h3>
        <p className="muted">Activity = snapshots + commits in each time bucket. Darker cells mean higher activity.</p>
      </div>

      <div className="activity-heatmap-legend" aria-label="Heatmap intensity legend">
        <span className="muted">Lower</span>
        {[0, 1, 2, 3, 4].map((level) => (
          <span key={level} className={`legend-cell intensity-${level}`} aria-hidden="true" />
        ))}
        <span className="muted">Higher</span>
      </div>

      <div className="activity-heatmap-grid" role="list" aria-label="Activity heatmap by bucket">
        {sortedBuckets.map((bucket, index) => {
          const activityCount = Number(bucket?.activity_count) || 0;
          const level = toIntensityLevel(activityCount, maxActivityCount);
          const bucketKey = bucket?.bucket_start || bucket?.bucket_date || `bucket-${index}`;

          return (
            <button
              key={bucketKey}
              type="button"
              className={`activity-heatmap-cell intensity-${level}`}
              onMouseEnter={() => setActiveBucketIndex(index)}
              onFocus={() => setActiveBucketIndex(index)}
              aria-label={`Heatmap bucket ${formatBucketLabel(bucket)} with ${activityCount} activity events`}
            >
              <span className="activity-heatmap-count">{activityCount}</span>
              <span className="activity-heatmap-date">{bucket?.bucket_date || 'N/A'}</span>
            </button>
          );
        })}
      </div>

      {selectedBucket && (
        <div className="activity-heatmap-details" role="status" aria-live="polite">
          <p>
            <strong>Bucket:</strong> {formatBucketLabel(selectedBucket)}
          </p>
          <p>
            <strong>Activity:</strong> {Number(selectedBucket?.activity_count) || 0}
          </p>
          <p>
            <strong>Snapshots:</strong> {Number(selectedBucket?.snapshot_count) || 0}
          </p>
          <p>
            <strong>Commits:</strong> {Number(selectedBucket?.commit_count) || 0}
          </p>
          <p>
            <strong>Projects:</strong>{' '}
            {Array.isArray(selectedBucket?.project_names) && selectedBucket.project_names.filter(Boolean).length > 0
              ? selectedBucket.project_names.filter(Boolean).join(', ')
              : 'N/A'}
          </p>
        </div>
      )}
    </div>
  );
}

export default ActivityHeatmap;
