import React, { useEffect, useState } from 'react';

const API_BASE = 'http://localhost:5001';

function App() {
  const [userId, setUserId] = useState(null);
  const [portfolioId, setPortfolioId] = useState(null);
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [view, setView] = useState('projects');
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);
  
  const [projectReport, setProjectReport] = useState(null);
  const [projectSkills, setProjectSkills] = useState(null);
  const [contributors, setContributors] = useState([]);
  const [topProjects, setTopProjects] = useState([]);
  const [chronologicalSkills, setChronologicalSkills] = useState([]);

  useEffect(() => {
    let storedUserId = localStorage.getItem('userId');
    
    if (!storedUserId) {
      fetch(`${API_BASE}/privacy-consent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          consent_type: 'data_access',
          granted: true,
          version: 1
        })
      })
      .then(r => r.json())
      .then(data => {
        storedUserId = data.user_id;
        localStorage.setItem('userId', storedUserId);
        setUserId(storedUserId);
      })
      .catch(err => console.error("Error creating user:", err));
    } else {
      setUserId(storedUserId);
    }
  }, []);

  useEffect(() => {
    if (!userId) return;
    fetchProjects();
  }, [userId]);

  const fetchProjects = async () => {
    try {
      const res = await fetch(`${API_BASE}/projects?user_id=${userId}`);
      const data = await res.json();
      setProjects(data.projects || []);
      setPortfolioId(data.portfolio_id);
      
      if (data.projects?.length > 0) {
        fetchTopProjects(data.portfolio_id);
      }
    } catch (err) {
      console.error("Error fetching projects:", err);
    }
  };

  const fetchTopProjects = async (pId) => {
    try {
      const res = await fetch(`${API_BASE}/portfolio/${pId}/top-projects?limit=5`);
      const data = await res.json();
      setTopProjects(data.top_projects || []);
    } catch (err) {
      console.error("Error fetching top projects:", err);
    }
  };

  const fetchProjectReport = async (projectId) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/projects/${projectId}/report`);
      const data = await res.json();
      setProjectReport(data);
      
      const contribRes = await fetch(`${API_BASE}/projects/${projectId}/contributors`);
      const contribData = await contribRes.json();
      setContributors(contribData.contributors || []);
    } catch (err) {
      console.error("Error fetching report:", err);
    }
    setLoading(false);
  };

  const fetchProjectSkills = async (snapshotId) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/snapshots/${snapshotId}/skills?limit=20`);
      const data = await res.json();
      setProjectSkills(data);
    } catch (err) {
      console.error("Error fetching skills:", err);
    }
    setLoading(false);
  };

  const fetchChronologicalSkills = async () => {
    if (!portfolioId) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/portfolio/${portfolioId}/skills/chronological?limit=50`);
      const data = await res.json();
      setChronologicalSkills(data.skill_events || []);
    } catch (err) {
      console.error("Error fetching chronological skills:", err);
    }
    setLoading(false);
  };

  const handleUpload = async () => {
    if (!file) return alert("Please select a file first!");
    if (!userId) return alert("User not initialized yet!");
    
    const formData = new FormData();
    formData.append("file", file);
    formData.append("project_name", file.name.split(".")[0]);
    formData.append("user_id", userId);

    try {
      setUploading(true);
      const res = await fetch(`${API_BASE}/projects/upload`, {
        method: 'POST',
        body: formData
      });
      
      if (!res.ok) throw new Error('Upload failed');
      
      alert("Upload successful!");
      await fetchProjects();
      setFile(null);
      setView('projects');
    } catch (err) {
      console.error("Upload failed:", err);
      alert("Upload failed! " + err.message);
    } finally {
      setUploading(false);
    }
  };

  const generateResume = async (projectId) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/resume/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          prefer_external_bullets: true
        })
      });
      const data = await res.json();
      alert(`Resume generated! ID: ${data.resume_id}`);
      window.open(`${API_BASE}/resume/${data.resume_id}/pdf`, '_blank');
    } catch (err) {
      console.error("Resume generation failed:", err);
      alert("Resume generation failed!");
    }
    setLoading(false);
  };

  const viewProjectDetails = (project) => {
    setSelectedProject(project);
    fetchProjectReport(project.id);
    if (project.latest_snapshot?.id) {
      fetchProjectSkills(project.latest_snapshot.id);
    }
    setView('report');
  };

  if (!userId) {
    return <div style={s.container}>Loading user...</div>;
  }

  return (
    <div style={s.container}>
      <header style={s.header}>
        <h1>Project Portfolio Dashboard</h1>
        <p style={s.subtitle}>User ID: {userId?.slice(0, 8)}...</p>
      </header>

      <nav style={s.nav}>
        <button onClick={() => setView('projects')} style={{...s.navBtn, ...(view === 'projects' ? s.navBtnActive : {})}}>Projects</button>
        <button onClick={() => setView('upload')} style={{...s.navBtn, ...(view === 'upload' ? s.navBtnActive : {})}}>Upload</button>
        <button onClick={() => { setView('skills'); fetchChronologicalSkills(); }} style={{...s.navBtn, ...(view === 'skills' ? s.navBtnActive : {})}}>Skills Timeline</button>
        <button onClick={() => setView('top')} style={{...s.navBtn, ...(view === 'top' ? s.navBtnActive : {})}}>Top Projects</button>
      </nav>

      <main style={s.main}>
        {view === 'projects' && (
          <div>
            <h2>All Projects ({projects.length})</h2>
            {projects.length === 0 ? (
              <p>No projects yet. Upload one to get started!</p>
            ) : (
              <div style={s.projectGrid}>
                {projects.map(project => (
                  <div key={project.id} style={s.projectCard}>
                    <h3 style={s.projectTitle}>{project.name}</h3>
                    <div style={s.projectMeta}>
                      <span>Type: {project.project_type || 'Unknown'}</span>
                      <span>Commits: {project.metrics?.total_commits || 0}</span>
                      <span>Contributors: {project.metrics?.contributor_count || 0}</span>
                    </div>
                    {project.metrics?.rank_score && (
                      <div style={s.rankScore}>Rank Score: {project.metrics.rank_score.toFixed(2)}</div>
                    )}
                    <div style={s.cardActions}>
                      <button onClick={() => viewProjectDetails(project)} style={s.btn}>View Details</button>
                      <button onClick={() => generateResume(project.id)} style={s.btnSecondary}>Generate Resume</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {view === 'upload' && (
          <div>
            <h2>Upload New Project</h2>
            <div style={s.uploadBox}>
              <input type="file" accept=".zip" onChange={e => setFile(e.target.files[0])} style={s.fileInput} />
              {file && <p>Selected: {file.name}</p>}
              <button onClick={handleUpload} disabled={uploading || !file} style={{...s.btn, ...(uploading ? s.btnDisabled : {})}}>
                {uploading ? "Uploading..." : "Upload Project"}
              </button>
            </div>
          </div>
        )}

        {view === 'report' && selectedProject && (
          <div>
            <button onClick={() => setView('projects')} style={s.backBtn}>← Back to Projects</button>
            <h2>{selectedProject.name}</h2>
            
            {loading ? <p>Loading...</p> : (
              <>
                {projectReport && (
                  <div style={s.reportSection}>
                    <h3>Project Summary</h3>
                    <div style={s.summaryGrid}>
                      <div><strong>Total Files:</strong> {projectReport.summary?.total_files || 0}</div>
                      <div><strong>Total Lines:</strong> {projectReport.summary?.total_lines || 0}</div>
                      <div><strong>Languages:</strong> {projectReport.summary?.language_count || 0}</div>
                    </div>

                    {projectReport.top_languages && (
                      <div style={s.languagesSection}>
                        <h4>Top Languages</h4>
                        {projectReport.top_languages.map((lang, i) => (
                          <div key={i} style={s.languageBar}>
                            <span>{lang.language}</span>
                            <span>{lang.percentage.toFixed(1)}%</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {projectSkills && projectSkills.skills?.length > 0 && (
                  <div style={s.skillsSection}>
                    <h3>Detected Skills</h3>
                    <div style={s.skillsGrid}>
                      {projectSkills.skills.map((skill, i) => (
                        <div key={i} style={s.skillBadge}>
                          {skill.skill_name}
                          <span style={s.confidence}>{(skill.confidence * 100).toFixed(0)}%</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {contributors.length > 0 && (
                  <div style={s.contributorsSection}>
                    <h3>Contributors</h3>
                    <div style={s.tableWrap}>
                      <table style={s.table}>
                        <thead>
                          <tr>
                            <th style={s.th}>Name</th>
                            <th style={s.th}>Email</th>
                            <th style={s.th}>Commits</th>
                            <th style={s.th}>Is You</th>
                          </tr>
                        </thead>
                        <tbody>
                          {contributors.map(contrib => (
                            <tr key={contrib.contributor_id}>
                              <td style={s.td}>{contrib.canonical_name}</td>
                              <td style={s.td}>{contrib.email}</td>
                              <td style={s.td}>{contrib.commits}</td>
                              <td style={s.td}>{contrib.is_user ? '✓' : ''}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {view === 'top' && (
          <div>
            <h2>Top Ranked Projects</h2>
            {topProjects.length === 0 ? <p>No ranked projects available</p> : (
              <div style={s.topProjectsList}>
                {topProjects.map((proj, i) => (
                  <div key={proj.project_id} style={s.topProjectCard}>
                    <div style={s.rank}>#{i + 1}</div>
                    <div style={s.topProjectContent}>
                      <h3>{proj.name}</h3>
                      <div style={s.topProjectMeta}>
                        <span>Score: {proj.rank_score?.toFixed(2)}</span>
                        <span>Your Commits: {proj.features?.user_commits || 0}</span>
                        <span>Total Commits: {proj.features?.total_commits || 0}</span>
                      </div>
                      {proj.summary?.top_languages && <p><strong>Languages:</strong> {proj.summary.top_languages}</p>}
                      {proj.summary?.top_skills && <p><strong>Skills:</strong> {proj.summary.top_skills}</p>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {view === 'skills' && (
          <div>
            <h2>Skills Timeline</h2>
            {loading ? <p>Loading...</p> : chronologicalSkills.length === 0 ? <p>No skills data available</p> : (
              <div style={s.timeline}>
                {chronologicalSkills.map((event, i) => (
                  <div key={i} style={s.timelineItem}>
                    <div style={s.timelineDate}>
                      {event.first_seen_ts ? new Date(event.first_seen_ts).toLocaleDateString() : 'N/A'}
                    </div>
                    <div style={s.timelineContent}>
                      <strong>{event.skill}</strong>
                      <p style={s.timelineProject}>Project: {event.project_name}</p>
                      {event.max_prob && <span style={s.confidence}>Confidence: {(event.max_prob * 100).toFixed(0)}%</span>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

const s = {
  container: { minHeight: '100vh', backgroundColor: '#f5f5f5', fontFamily: 'Arial, sans-serif' },
  header: { backgroundColor: '#2c3e50', color: 'white', padding: '2rem', textAlign: 'center' },
  subtitle: { fontSize: '0.9rem', opacity: 0.8, margin: '0.5rem 0 0 0' },
  nav: { backgroundColor: 'white', padding: '1rem', display: 'flex', gap: '1rem', borderBottom: '1px solid #ddd', justifyContent: 'center' },
  navBtn: { padding: '0.75rem 1.5rem', border: 'none', backgroundColor: '#ecf0f1', cursor: 'pointer', borderRadius: '4px', fontSize: '1rem' },
  navBtnActive: { backgroundColor: '#3498db', color: 'white' },
  main: { maxWidth: '1200px', margin: '2rem auto', padding: '0 2rem' },
  projectGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1.5rem', marginTop: '1.5rem' },
  projectCard: { backgroundColor: 'white', padding: '1.5rem', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' },
  projectTitle: { margin: '0 0 1rem 0' },
  projectMeta: { display: 'flex', flexDirection: 'column', gap: '0.5rem', margin: '1rem 0', fontSize: '0.9rem', color: '#666' },
  rankScore: { backgroundColor: '#3498db', color: 'white', padding: '0.5rem', borderRadius: '4px', fontSize: '0.9rem', textAlign: 'center', marginBottom: '1rem' },
  cardActions: { display: 'flex', gap: '0.5rem' },
  btn: { padding: '0.75rem 1rem', backgroundColor: '#3498db', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '0.9rem', flex: 1 },
  btnSecondary: { padding: '0.75rem 1rem', backgroundColor: '#95a5a6', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '0.9rem', flex: 1 },
  btnDisabled: { backgroundColor: '#bdc3c7', cursor: 'not-allowed' },
  uploadBox: { backgroundColor: 'white', padding: '2rem', borderRadius: '8px', marginTop: '1.5rem', textAlign: 'center' },
  fileInput: { marginBottom: '1rem' },
  backBtn: { padding: '0.5rem 1rem', backgroundColor: '#95a5a6', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', marginBottom: '1rem' },
  reportSection: { backgroundColor: 'white', padding: '1.5rem', borderRadius: '8px', marginBottom: '1.5rem' },
  summaryGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginTop: '1rem' },
  languagesSection: { marginTop: '1.5rem' },
  languageBar: { display: 'flex', justifyContent: 'space-between', padding: '0.5rem', backgroundColor: '#ecf0f1', marginBottom: '0.5rem', borderRadius: '4px' },
  skillsSection: { backgroundColor: 'white', padding: '1.5rem', borderRadius: '8px', marginBottom: '1.5rem' },
  skillsGrid: { display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '1rem' },
  skillBadge: { backgroundColor: '#3498db', color: 'white', padding: '0.5rem 1rem', borderRadius: '20px', fontSize: '0.9rem', display: 'flex', gap: '0.5rem', alignItems: 'center' },
  confidence: { backgroundColor: 'rgba(255,255,255,0.3)', padding: '0.2rem 0.5rem', borderRadius: '10px', fontSize: '0.8rem' },
  contributorsSection: { backgroundColor: 'white', padding: '1.5rem', borderRadius: '8px', marginBottom: '1.5rem' },
  tableWrap: { overflowX: 'auto' },
  table: { width: '100%', borderCollapse: 'collapse', marginTop: '1rem' },
  th: { textAlign: 'left', padding: '0.75rem', borderBottom: '2px solid #ddd', backgroundColor: '#f8f9fa' },
  td: { padding: '0.75rem', borderBottom: '1px solid #eee' },
  topProjectsList: { marginTop: '1.5rem' },
  topProjectCard: { backgroundColor: 'white', padding: '1.5rem', borderRadius: '8px', marginBottom: '1rem', display: 'flex', gap: '1rem' },
  rank: { fontSize: '2rem', fontWeight: 'bold', color: '#3498db', minWidth: '60px' },
  topProjectContent: { flex: 1 },
  topProjectMeta: { display: 'flex', gap: '1rem', margin: '0.5rem 0', fontSize: '0.9rem', color: '#666', flexWrap: 'wrap' },
  timeline: { marginTop: '1.5rem' },
  timelineItem: { backgroundColor: 'white', padding: '1rem', borderRadius: '8px', marginBottom: '1rem', display: 'flex', gap: '1rem' },
  timelineDate: { fontWeight: 'bold', color: '#3498db', minWidth: '120px' },
  timelineContent: { flex: 1 },
  timelineProject: { fontSize: '0.9rem', color: '#666', margin: '0.25rem 0' },
};

export default App;