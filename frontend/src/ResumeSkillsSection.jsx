import React, { useMemo } from 'react';
import {
  SKILL_EXPERTISE_LABELS,
  SKILL_EXPERTISE_ORDER,
  resolveSkillsByExpertise,
} from './resumeSkills';

function ResumeSkillsSection({ skillsByExpertise, projects }) {
  const grouped = useMemo(
    () => resolveSkillsByExpertise(skillsByExpertise, projects),
    [skillsByExpertise, projects]
  );
  const hasAnySkills = SKILL_EXPERTISE_ORDER.some((level) => grouped[level].length > 0);

  return (
    <section className="panel">
      <h2>Skills by Expertise</h2>
      <p className="muted">Derived from your project analyses. Included when generating your resume PDF.</p>
      {!hasAnySkills && (
        <p className="muted">No skills detected yet. Analyze projects to populate expertise groups.</p>
      )}
      {hasAnySkills && (
        <div className="stack-block">
          {SKILL_EXPERTISE_ORDER.map((level) => {
            const rows = grouped[level];
            if (!rows.length) return null;
            return (
              <div key={level}>
                <h3>{SKILL_EXPERTISE_LABELS[level]}</h3>
                <div className="badge-row">
                  {rows.map((skill) => (
                    <span key={`${level}-${skill.name.toLowerCase()}`} className="skill-badge">
                      {skill.name}
                    </span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

export default ResumeSkillsSection;
