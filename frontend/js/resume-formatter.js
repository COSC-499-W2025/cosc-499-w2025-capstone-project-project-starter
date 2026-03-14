/**
 * Resume Formatter - Resume formatting utility
 * Formats resume data into HTML presentation
 */

/**
 * Format resume data into HTML
 * @param {Object} resume - Resume data object
 * @returns {string} Formatted HTML string
 */
function formatResumeHTML(resume) {
    let html = '<div style="background: var(--bg-secondary); padding: 2rem; border-radius: 8px; line-height: 1.6;">';
    
    // Header
    html += `<div style="text-align: center; border-bottom: 3px double var(--border-color); padding-bottom: 1rem; margin-bottom: 2rem;">`;
    html += `<h2 style="margin: 0.5rem 0; font-size: 2rem;">${escapeHtml(resume.display_name || resume.user_name)}</h2>`;
    html += `</div>`;
    
    // Technical Skills Section
    html += `<div style="margin-bottom: 2rem;">`;
    html += `<h3 style="border-bottom: 2px solid var(--border-color); padding-bottom: 0.5rem; margin-bottom: 1rem;">TECHNICAL SKILLS</h3>`;
    
    const categorizedSkills = resume.categorized_skills || {};
    if (Object.keys(categorizedSkills).length > 0) {
        for (const [category, skills] of Object.entries(categorizedSkills)) {
            if (skills && skills.length > 0) {
                html += `<div style="margin-bottom: 0.5rem;">`;
                html += `<strong>${escapeHtml(category)}:</strong> ${skills.map(s => escapeHtml(s)).join(', ')}`;
                html += `</div>`;
            }
        }
    } else if (resume.all_skills && resume.all_skills.length > 0) {
        html += `<div>${resume.all_skills.map(s => escapeHtml(s)).join(', ')}</div>`;
    }
    html += `</div>`;
    
    // Projects Section
    html += `<div>`;
    html += `<h3 style="border-bottom: 2px solid var(--border-color); padding-bottom: 0.5rem; margin-bottom: 1rem;">PROJECTS</h3>`;
    
    const projects = resume.top_projects || [];
    if (projects.length > 0) {
        projects.forEach((project, idx) => {
            html += `<div style="margin-bottom: 2rem; padding-bottom: 1.5rem; ${idx < projects.length - 1 ? 'border-bottom: 1px solid var(--border-color);' : ''}">`;
            
            // Project name and date
            html += `<h4 style="margin: 0 0 0.5rem 0; font-size: 1.2rem; text-transform: uppercase;">${escapeHtml(project.project_name)}</h4>`;
            
            // Date handling
            if (project.first_file) {
                const firstDate = project.first_file.split(' ')[0];
                const lastDate = project.last_file ? project.last_file.split(' ')[0] : firstDate;
                if (firstDate === lastDate || project.duration_days === 0) {
                    html += `<div style="margin-bottom: 0.5rem; color: var(--text-muted);">${firstDate}</div>`;
                } else {
                    html += `<div style="margin-bottom: 0.5rem; color: var(--text-muted);">${firstDate} - ${lastDate}</div>`;
                }
            }
            html += `<div style="margin-left: 1.5rem;">`;
            
            // Created date
            if (project.first_file) {
                html += `<div style="margin-bottom: 0.3rem;"><strong>Created:</strong> ${escapeHtml(project.first_file)}</div>`;
            }
            
            // Primary Language
            if (project.primary_language) {
                html += `<div style="margin-bottom: 0.3rem;"><strong>Primary Language:</strong> ${escapeHtml(project.primary_language)}</div>`;
            }
            
            // Other Languages
            if (project.languages && project.languages.length > 0) {
                const otherLangs = project.languages.filter(l => l !== project.primary_language);
                if (otherLangs.length > 0) {
                    html += `<div style="margin-bottom: 0.3rem;"><strong>Other Languages:</strong> ${otherLangs.map(l => escapeHtml(l)).join(', ')}</div>`;
                }
            }
            
            // Project info from project_info field
            if (project.project_info) {
                if (project.project_info.file_count !== undefined) {
                    const sizeInMB = project.project_info.size_bytes ? (project.project_info.size_bytes / (1024 * 1024)).toFixed(1) : '0.0';
                    html += `<div style="margin-bottom: 0.3rem;"><strong>Files:</strong> ${project.project_info.file_count} (${sizeInMB} MB)</div>`;
                }
            }
            
            // Duration
            if (project.duration_days !== undefined && project.duration_days !== null) {
                const dayText = project.duration_days === 0 ? 'Single day' : `${project.duration_days} days`;
                html += `<div style="margin-bottom: 0.3rem;"><strong>Duration:</strong> ${project.duration_days} days (${dayText})</div>`;
            }
            
            // Collaboration
            if (project.collaboration_level) {
                html += `<div style="margin-bottom: 0.3rem;"><strong>Collaboration:</strong> ${escapeHtml(project.collaboration_level)}</div>`;
            }
            
            // Summary from code analysis
            if (project.summary) {
                const summaryLines = project.summary.split('\n').filter(line => {
                    const trimmed = line.trim();
                    return trimmed && 
                           !trimmed.startsWith('=') && 
                           !trimmed.includes('PROJECT SUMMARY') &&
                           !trimmed.startsWith('Created:') &&
                           trimmed.length > 10;
                });
                
                if (summaryLines.length > 0) {
                    summaryLines.slice(0, 8).forEach(line => {
                        const trimmed = line.trim();
                        if (trimmed.includes(':') && !trimmed.startsWith('-')) {
                            html += `<div style="margin-bottom: 0.3rem;"><strong>${escapeHtml(trimmed)}</strong></div>`;
                        } else if (trimmed) {
                            html += `<div style="margin-bottom: 0.3rem;">${escapeHtml(trimmed)}</div>`;
                        }
                    });
                }
            }
            
            // Technologies
            if (project.skills && project.skills.length > 0) {
                html += `<div style="margin-bottom: 0.3rem;"><strong>Technologies:</strong> ${project.skills.map(s => escapeHtml(s)).join(', ')}</div>`;
            }
            
            // Evidence bullets
            if (project.evidence && project.evidence.length > 0) {
                html += `<div style="margin-top: 0.5rem;"><strong>Evidence:</strong></div>`;
                html += `<ul style="margin: 0.3rem 0 0 1.5rem; padding-left: 1rem;">`;
                project.evidence.forEach(ev => {
                    html += `<li style="margin-bottom: 0.2rem;">${escapeHtml(ev)}</li>`;
                });
                html += `</ul>`;
            }
            
            // Collaborative project note
            if (project.collaboration_level && 
                project.collaboration_level.toLowerCase().includes('collaborative')) {
                html += `<div style="margin-top: 0.5rem; font-style: italic;">Collaborative project</div>`;
            }
            
            html += `</div></div>`;
        });
    } else {
        html += `<div style="color: var(--text-muted);">No projects to display</div>`;
    }
    
    html += `</div>`;
    
    // Footer
    if (resume.generated_at) {
        const genDate = resume.generated_at.split('T')[0];
        html += `<div style="margin-top: 2rem; padding-top: 1rem; border-top: 3px double var(--border-color); text-align: center; color: var(--text-muted);">`;
        html += `Resume generated: ${genDate}`;
        html += `</div>`;
    }
    
    html += '</div>';
    return html;
}
