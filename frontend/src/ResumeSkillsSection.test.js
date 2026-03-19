import { render, screen } from '@testing-library/react';
import ResumeSkillsSection from './ResumeSkillsSection';

test('renders expertise headings in fixed order', () => {
  render(
    <ResumeSkillsSection
      skillsByExpertise={{
        expert: [{ name: 'Rust', expertise: 'expert', probability: 0.9 }],
        proficient: [{ name: 'Python', expertise: 'proficient', probability: 0.7 }],
        familiar: [{ name: 'Go', expertise: 'familiar', probability: 0.5 }],
        exposure: [{ name: 'HTML', expertise: 'exposure', probability: 0.2 }],
      }}
      projects={[]}
    />
  );

  const headings = screen.getAllByRole('heading', { level: 3 }).map((node) => node.textContent);
  expect(headings).toEqual(['Expert', 'Proficient', 'Familiar', 'Exposure']);
});

test('falls back to projects skills when grouped payload is absent', () => {
  render(
    <ResumeSkillsSection
      skillsByExpertise={null}
      projects={[
        {
          project_id: 'p1',
          skills: [
            { name: 'Python', expertise: 'proficient', probability: 0.7 },
            { name: 'React', expertise: 'familiar', probability: 0.45 },
          ],
        },
        {
          project_id: 'p2',
          skills: [
            { name: 'python', expertise: 'expert', probability: 0.92 },
          ],
        },
      ]}
    />
  );

  expect(screen.getByRole('heading', { name: 'Expert' })).toBeInTheDocument();
  expect(screen.getByText('python')).toBeInTheDocument();
  expect(screen.getAllByText(/python/i)).toHaveLength(1);
  expect(screen.getByRole('heading', { name: 'Familiar' })).toBeInTheDocument();
  expect(screen.getByText('React')).toBeInTheDocument();
});

test('shows empty state when no skills exist', () => {
  render(<ResumeSkillsSection skillsByExpertise={null} projects={[]} />);
  expect(
    screen.getByText('No skills detected yet. Analyze projects to populate expertise groups.')
  ).toBeInTheDocument();
});
