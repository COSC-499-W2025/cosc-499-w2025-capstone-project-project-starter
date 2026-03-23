export const SKILL_EXPERTISE_ORDER = ['expert', 'proficient', 'familiar', 'exposure'];

export const SKILL_EXPERTISE_LABELS = {
  expert: 'Expert',
  proficient: 'Proficient',
  familiar: 'Familiar',
  exposure: 'Exposure',
};

function normalizeSkillName(entry) {
  if (entry && typeof entry === 'object') {
    const name = String(entry.name || entry.skill || '').trim();
    if (!name) return '';
    return name;
  }
  return String(entry || '').trim();
}

export function normalizeSkillsByExpertise(raw) {
  const source = raw && typeof raw === 'object' ? raw : {};
  const out = {};

  SKILL_EXPERTISE_ORDER.forEach((level) => {
    const rows = Array.isArray(source[level]) ? source[level] : [];
    out[level] = rows
      .map((entry) => {
        const name = normalizeSkillName(entry);
        if (!name) return null;
        const probability =
          entry && typeof entry === 'object' && Number.isFinite(Number(entry.probability))
            ? Number(entry.probability)
            : null;
        return { name, expertise: level, probability };
      })
      .filter(Boolean);
  });

  return out;
}

export function deriveSkillsByExpertiseFromProjects(projects) {
  const bestByName = new Map();
  const projectList = Array.isArray(projects) ? projects : [];

  projectList.forEach((project) => {
    const skills = Array.isArray(project?.skills) ? project.skills : [];
    skills.forEach((skill) => {
      const name = normalizeSkillName(skill);
      if (!name) return;
      const key = name.toLowerCase();
      const probability = Number.isFinite(Number(skill?.probability)) ? Number(skill.probability) : 0;
      const expertise = SKILL_EXPERTISE_ORDER.includes(skill?.expertise) ? skill.expertise : 'exposure';
      const candidate = { name, expertise, probability };
      const existing = bestByName.get(key);
      if (!existing || candidate.probability > existing.probability) {
        bestByName.set(key, candidate);
      } else if (
        candidate.probability === existing.probability &&
        candidate.name.localeCompare(existing.name, undefined, { sensitivity: 'base' }) < 0
      ) {
        bestByName.set(key, candidate);
      }
    });
  });

  const grouped = normalizeSkillsByExpertise({});
  bestByName.forEach((skill) => {
    grouped[skill.expertise].push(skill);
  });
  SKILL_EXPERTISE_ORDER.forEach((level) => {
    grouped[level].sort((a, b) => {
      const diff = (b.probability || 0) - (a.probability || 0);
      if (diff !== 0) return diff;
      return a.name.localeCompare(b.name, undefined, { sensitivity: 'base' });
    });
  });

  return grouped;
}

export function resolveSkillsByExpertise(skillsByExpertise, projects) {
  const normalized = normalizeSkillsByExpertise(skillsByExpertise);
  const hasAny = SKILL_EXPERTISE_ORDER.some((level) => normalized[level].length > 0);
  if (hasAny) return normalized;
  return deriveSkillsByExpertiseFromProjects(projects);
}
