export function formatAnalysisResults(analysis) {
    let html = '<div class="analysis-section">';
    html += '<h4>Analysis Overview</h4>';

    const projInfo = analysis.project_info || {};
    html += `<div class="analysis-item"><span class="analysis-label">Project:</span><span class="analysis-value">${projInfo.filename || 'Unknown'}</span></div>`;
    html += `<div class="analysis-item"><span class="analysis-label">Strategy:</span><span class="analysis-value">${analysis.analysis_strategy || 'local'}</span></div>`;

    const langs = analysis.languages || {};
    if (langs.primary_language) {
        html += '<div class="analysis-item">';
        html += `<span class="analysis-label">Primary Language:</span><span class="analysis-value">${langs.primary_language}</span>`;
        html += '</div>';
    }
    if (langs.detected_languages && langs.detected_languages.length > 0) {
        html += '<div class="analysis-item">';
        html += `<span class="analysis-label">All Languages (${langs.detected_languages.length}):</span>`;
        html += '<div style="margin-top: 5px;">';
        langs.detected_languages.forEach(lang => {
            const count = langs.file_counts?.[lang] || 0;
            const pct = langs.language_percentages?.[lang] || 0;
            html += `<span class="badge">${lang} (${count} files, ${pct}%)</span>`;
        });
        html += '</div></div>';
    }

    html += '</div>';

    const zipReport = analysis.zip_success_report || null;
    if (zipReport) {
        html += '<div class="analysis-section">';
        html += '<h4> - Evidence of Success (ZIP)</h4>';
        if (zipReport.error) {
            html += `<div class="analysis-item"><span class="analysis-label">Status:</span><span class="analysis-value">${zipReport.error}</span></div>`;
        } else {
            const success = zipReport.success || {};
            const status = (success.status || 'unknown').toUpperCase();
            const score = success.score !== undefined ? success.score : 0;
            const confidence = success.confidence !== undefined ? success.confidence : 0;
            const statusColor = status === 'SUCCESS' ? '#22c55e' : status === 'PARTIAL' ? '#d97706' : '#dc2626';
            html += `<div class="analysis-item"><span class="analysis-label">Status:</span><span class="analysis-value" style="color: ${statusColor}; font-weight: 600;">${status}</span></div>`;
            html += `<div class="analysis-item"><span class="analysis-label">Score:</span><span class="analysis-value">${score}/100 (confidence ${confidence})</span></div>`;
            html += `<div class="analysis-item"><span class="analysis-label">Result:</span><span class="analysis-value">${success.is_successful ? 'SUCCESS' : 'NOT SUCCESSFUL'}</span></div>`;

            const evidence = zipReport.evidence || {};
            const addEvidenceRow = (label, values, limit = 10) => {
                if (!values || (Array.isArray(values) && values.length === 0)) return;
                html += '<div class="analysis-item">';
                html += `<span class="analysis-label">${label}:</span>`;
                html += '<div style="margin-top: 5px;">';
                const list = Array.isArray(values) ? values.slice(0, limit) : [values];
                list.forEach(val => {
                    html += `<span class="badge">${val}</span>`;
                });
                html += '</div></div>';
            };

            addEvidenceRow('Entrypoints', evidence.entrypoints);
            addEvidenceRow('Dependencies', evidence.dependency_manifests);
            addEvidenceRow('Tests', evidence.test_files);
            addEvidenceRow('CI Files', evidence.ci_files);
            addEvidenceRow('README', evidence.readme_file, 1);
            addEvidenceRow('Docs', evidence.docs_files);
            addEvidenceRow('Usage Markers', evidence.usage_markers);
            addEvidenceRow('Incomplete Markers', evidence.incomplete_markers);
            addEvidenceRow('Build Artifacts', evidence.build_artifacts);
            addEvidenceRow('License', evidence.license_files);
        }
        html += '</div>';
    }

    const stats = analysis.file_statistics || {};
    if (stats.total_files !== undefined) {
        html += '<div class="analysis-section">';
        html += '<h4> - File Statistics</h4>';
        html += `<div class="analysis-item"><span class="analysis-label">Total Files:</span><span class="analysis-value">${stats.total_files}</span></div>`;
        html += `<div class="analysis-item"><span class="analysis-label">Total Size:</span><span class="analysis-value">${stats.total_size_mb || 0} MB</span></div>`;
        html += `<div class="analysis-item"><span class="analysis-label">Text Files:</span><span class="analysis-value">${stats.text_files || 0}</span></div>`;
        html += `<div class="analysis-item"><span class="analysis-label">Binary Files:</span><span class="analysis-value">${stats.binary_files || 0}</span></div>`;
        html += `<div class="analysis-item"><span class="analysis-label">Lines of Code:</span><span class="analysis-value">${stats.total_lines_of_code || 0}</span></div>`;
        html += '</div>';
    }

    const frameworks = analysis.frameworks || [];
    if (frameworks.length > 0) {
        html += '<div class="analysis-section">';
        html += '<h4> - Frameworks & Technologies</h4>';
        html += '<div class="analysis-item">';
        frameworks.forEach(fw => {
            html += `<span class="badge">${fw}</span>`;
        });
        html += '</div></div>';
    }

    const skills = analysis.skills || [];
    if (skills.length > 0) {
        html += '<div class="analysis-section">';
        html += '<h4> - Skills Detected</h4>';
        html += '<div class="analysis-item">';
        skills.forEach(skill => {
            html += `<span class="badge">${skill}</span>`;
        });
        html += '</div></div>';
    }

    const structure = analysis.project_structure || {};
    if (structure.total_folders !== undefined) {
        html += '<div class="analysis-section">';
        html += '<h4> - Project Structure</h4>';
        html += `<div class="analysis-item"><span class="analysis-label">Total Folders:</span><span class="analysis-value">${structure.total_folders}</span></div>`;
        html += `<div class="analysis-item"><span class="analysis-label">Max Depth:</span><span class="analysis-value">${structure.max_depth}</span></div>`;
        const features = [];
        if (structure.has_tests) features.push('Tests');
        if (structure.has_docs) features.push('Documentation');
        if (structure.has_config) features.push('Configuration');
        if (features.length > 0) {
            html += `<div class="analysis-item"><span class="analysis-label">Features:</span><span class="analysis-value">${features.join(', ')}</span></div>`;
        }
        html += '</div>';
    }

    const contrib = analysis.contribution_metrics || {};
    if (contrib.code_files !== undefined) {
        html += '<div class="analysis-section">';
        html += '<h4> - Contribution Metrics</h4>';
        html += `<div class="analysis-item"><span class="analysis-label">Code Files:</span><span class="analysis-value">${contrib.code_files}</span></div>`;
        html += `<div class="analysis-item"><span class="analysis-label">Test Files:</span><span class="analysis-value">${contrib.test_files || 0}</span></div>`;
        html += `<div class="analysis-item"><span class="analysis-label">Documentation Files:</span><span class="analysis-value">${contrib.documentation_files || 0}</span></div>`;
        html += `<div class="analysis-item"><span class="analysis-label">Configuration Files:</span><span class="analysis-value">${contrib.configuration_files || 0}</span></div>`;
        if (contrib.activity_distribution) {
            html += '<div class="analysis-item" style="margin-top: 10px;">';
            html += '<span class="analysis-label">Activity Distribution:</span>';
            html += '<div style="margin-top: 5px;">';
            const dist = contrib.activity_distribution;
            html += `<div>Code: ${dist.code || 0}% | Testing: ${dist.testing || 0}% | Documentation: ${dist.documentation || 0}% | Configuration: ${dist.configuration || 0}%</div>`;
            html += '</div></div>';
        }
        html += '</div>';
    }

    if (analysis.deep_analysis && Object.keys(analysis.deep_analysis).length > 0) {
        html += '<div class="analysis-section">';
        html += '<h4> - Deep Code Analysis</h4>';
        const deep = analysis.deep_analysis;

        if (deep.code_quality_summary) {
            const quality = deep.code_quality_summary;
            if (quality.average_quality_score) {
                html += `<div class="analysis-item"><span class="analysis-label">Code Quality Score:</span><span class="analysis-value">${quality.average_quality_score.toFixed(1)}/100</span></div>`;
            }
            if (quality.strengths && quality.strengths.length > 0) {
                html += '<div class="analysis-item">';
                html += '<span class="analysis-label">Strengths:</span>';
                html += '<div style="margin-top: 5px;">';
                quality.strengths.forEach(strength => {
                    html += `<span class="badge" style="background: #22c55e;">${strength}</span>`;
                });
                html += '</div></div>';
            }
        }

        if (deep.oop_principles_summary) {
            const oop = deep.oop_principles_summary;
            const oopTotal = ['abstraction', 'encapsulation', 'polymorphism', 'inheritance']
                .reduce((acc, key) => acc + (oop[key]?.count || 0), 0);
            if (oopTotal > 0) {
                html += '<div class="analysis-item">';
                html += '<span class="analysis-label">OOP Principles Detected:</span>';
                html += '<div style="margin-top: 5px;">';
                ['abstraction', 'encapsulation', 'polymorphism', 'inheritance'].forEach(key => {
                    if (oop[key]?.count) {
                        html += `<span class="badge">${key} (${oop[key].count})</span>`;
                    }
                });
                html += '</div></div>';
            }
        }

        if (deep.data_structure_summary) {
            const ds = deep.data_structure_summary;
            if (ds.total_structures_used) {
                html += '<div class="analysis-item">';
                html += '<span class="analysis-label">Data Structures Used:</span>';
                html += '<div style="margin-top: 5px;">';
                Object.entries(ds.structures || {}).forEach(([key, value]) => {
                    if (value.count > 0) {
                        html += `<span class="badge">${key} (${value.count})</span>`;
                    }
                });
                html += '</div></div>';
            }
        }

        if (deep.complexity_summary) {
            const complexity = deep.complexity_summary;
            if (complexity.big_o_patterns && complexity.big_o_patterns.length > 0) {
                html += '<div class="analysis-item">';
                html += '<span class="analysis-label">Complexity Analysis:</span>';
                html += '<div style="margin-top: 5px;">';
                complexity.big_o_patterns.forEach(p => {
                    html += `<div class="analysis-item">${p}</div>`;
                });
                html += '</div></div>';
            }
            if (complexity.recursion_detected) {
                html += `<div class="analysis-item">Recursion detected in ${complexity.recursion_detected} file(s)</div>`;
            }
            if (complexity.nested_loops_detected) {
                html += `<div class="analysis-item">Nested loops detected in ${complexity.nested_loops_detected} file(s)</div>`;
            }
        }

        if (deep.optimization_summary && deep.optimization_summary.length > 0) {
            html += '<div class="analysis-item">';
            html += '<span class="analysis-label">Optimizations Detected:</span>';
            html += '<div style="margin-top: 5px;">';
            deep.optimization_summary.forEach(opt => {
                html += `<div class="analysis-item">${opt}</div>`;
            });
            html += '</div></div>';
        }

        if (deep.code_quality_summary?.weaknesses?.length > 0) {
            html += '<div class="analysis-item">';
            html += '<span class="analysis-label">Areas for Improvement:</span>';
            html += '<div style="margin-top: 5px;">';
            deep.code_quality_summary.weaknesses.forEach(w => {
                html += `<div class="analysis-item">${w}</div>`;
            });
            html += '</div></div>';
        }

        html += '</div>';
    }

    return html;
}

export function formatGeminiAnalysis(analysis) {
    let html = '<div class="analysis-section" style="border-left-color: #7c3aed;">';
    html += '<h4 style="color: #7c3aed;">AI Deep Analysis (Gemini)</h4>';

    html += `<div class="analysis-item"><span class="analysis-label">Project:</span><span class="analysis-value">${analysis.project_name || 'Unknown'}</span></div>`;
    html += `<div class="analysis-item"><span class="analysis-label">Files Analyzed:</span><span class="analysis-value">${analysis.files_analyzed || 0}</span></div>`;
    html += '</div>';

    const overall = analysis.overall_assessment || {};
    if (overall.quality_score || overall.summary) {
        html += '<div class="analysis-section">';
        html += '<h4>Overall Assessment</h4>';
        if (overall.quality_score) {
            const scoreColor = overall.quality_score >= 70 ? '#22c55e' : overall.quality_score >= 40 ? '#d97706' : '#dc2626';
            html += `<div class="analysis-item"><span class="analysis-label">Quality Score:</span><span class="analysis-value" style="color: ${scoreColor}; font-weight: bold; font-size: 1.2em;">${overall.quality_score}/100</span></div>`;
        }
        if (overall.skill_level) {
            const levelBadge = {
                junior: 'badge-info',
                mid: 'badge',
                senior: 'badge-success',
                expert: 'badge-purple'
            };
            html += `<div class="analysis-item"><span class="analysis-label">Skill Level:</span><span class="badge ${levelBadge[overall.skill_level] || 'badge'}">${overall.skill_level.toUpperCase()}</span></div>`;
        }
        if (overall.summary) {
            html += `<div class="analysis-item" style="margin-top: 10px;"><p style="font-style: italic;">"${overall.summary}"</p></div>`;
        }
        html += '</div>';
    }

    const completion = analysis.project_completion || {};
    if (completion.status || completion.evidence || completion.missing_or_risks) {
        html += '<div class="analysis-section">';
        html += '<h4>Project Completion</h4>';
        if (completion.status) {
            const status = completion.status.toUpperCase();
            const statusColor = status === 'COMPLETE' ? '#22c55e' : status === 'MOSTLY_COMPLETE' ? '#84cc16' : status === 'PARTIAL' ? '#d97706' : '#dc2626';
            html += `<div class="analysis-item"><span class="analysis-label">Status:</span><span class="analysis-value" style="color: ${statusColor}; font-weight: 600;">${status}</span></div>`;
        }
        if (completion.confidence !== undefined) {
            html += `<div class="analysis-item"><span class="analysis-label">Confidence:</span><span class="analysis-value">${completion.confidence}</span></div>`;
        }
        if (completion.evidence && completion.evidence.length > 0) {
            html += '<div class="analysis-item"><span class="analysis-label">Evidence:</span><div style="margin-top: 5px;">';
            completion.evidence.forEach(item => {
                html += `<span class="badge">${item}</span>`;
            });
            html += '</div></div>';
        }
        if (completion.missing_or_risks && completion.missing_or_risks.length > 0) {
            html += '<div class="analysis-item"><span class="analysis-label">Missing/Risks:</span><div style="margin-top: 5px;">';
            completion.missing_or_risks.forEach(item => {
                html += `<span class="badge" style="background: #d97706;">${item}</span>`;
            });
            html += '</div></div>';
        }
        html += '</div>';
    }

    const arch = analysis.architecture || {};
    if (arch.structure_quality || (arch.patterns_used && arch.patterns_used.length > 0)) {
        html += '<div class="analysis-section">';
        html += '<h4>Architecture</h4>';
        if (arch.structure_quality) {
            html += `<div class="analysis-item"><span class="analysis-label">Structure Quality:</span><span class="badge">${arch.structure_quality}</span></div>`;
        }
        if (arch.patterns_used && arch.patterns_used.length > 0) {
            html += '<div class="analysis-item"><span class="analysis-label">Patterns Used:</span><div style="margin-top: 5px;">';
            arch.patterns_used.forEach(p => html += `<span class="badge">${p}</span>`);
            html += '</div></div>';
        }
        if (arch.separation_of_concerns) {
            html += `<div class="analysis-item"><span class="analysis-label">Separation of Concerns:</span><span class="analysis-value">${arch.separation_of_concerns}</span></div>`;
        }
        if (arch.modularity) {
            html += `<div class="analysis-item"><span class="analysis-label">Modularity:</span><span class="analysis-value">${arch.modularity}</span></div>`;
        }
        html += '</div>';
    }

    const cq = analysis.code_quality || {};
    if (Object.keys(cq).length > 0) {
        html += '<div class="analysis-section">';
        html += '<h4>Code Quality</h4>';
        Object.keys(cq).forEach(metric => {
            const entry = cq[metric];
            if (!entry) return;
            html += '<div class="analysis-item">';
            html += `<span class="analysis-label">${metric.charAt(0).toUpperCase() + metric.slice(1).replace('_', ' ')}:</span>`;
            if (entry.score !== undefined) {
                html += `<span class="analysis-value">${entry.score}/10</span>`;
            }
            if (entry.observations && entry.observations.length > 0) {
                html += '<div style="margin-top: 5px;">';
                entry.observations.forEach(o => {
                    html += `<div class="analysis-item">${o}</div>`;
                });
                html += '</div>';
            }
            html += '</div>';
        });
        html += '</div>';
    }

    const skills = analysis.skills_demonstrated || [];
    if (skills.length > 0) {
        html += '<div class="analysis-section">';
        html += '<h4>Skills Demonstrated</h4>';
        skills.forEach(s => {
            html += '<div class="analysis-item">';
            html += `<span class="analysis-label">${s.skill}</span> - <span class="badge">${s.proficiency}</span>`;
            if (s.evidence) {
                html += `<div style="margin-top: 5px;">${s.evidence}</div>`;
            }
            html += '</div>';
        });
        html += '</div>';
    }

    const bp = analysis.best_practices || {};
    if ((bp.followed && bp.followed.length > 0) || (bp.missing && bp.missing.length > 0)) {
        html += '<div class="analysis-section">';
        html += '<h4>Best Practices</h4>';
        if (bp.followed && bp.followed.length > 0) {
            html += '<div class="analysis-item"><span class="analysis-label" style="color: #22c55e;">Followed:</span><div style="margin-top: 5px;">';
            bp.followed.forEach(p => html += `<div style="margin: 3px 0;">✓ ${p}</div>`);
            html += '</div></div>';
        }
        if (bp.missing && bp.missing.length > 0) {
            html += '<div class="analysis-item"><span class="analysis-label" style="color: #d97706;">Could Improve:</span><div style="margin-top: 5px;">';
            bp.missing.forEach(p => html += `<div style="margin: 3px 0;">○ ${p}</div>`);
            html += '</div></div>';
        }
        html += '</div>';
    }

    const sec = analysis.security || {};
    if (sec.score || (sec.concerns && sec.concerns.length > 0)) {
        html += '<div class="analysis-section">';
        html += '<h4>Security Assessment</h4>';
        if (sec.score) {
            const secColor = sec.score >= 7 ? '#22c55e' : sec.score >= 4 ? '#d97706' : '#dc2626';
            html += `<div class="analysis-item"><span class="analysis-label">Security Score:</span><span style="color: ${secColor}; font-weight: bold;">${sec.score}/10</span></div>`;
        }
        if (sec.concerns && sec.concerns.length > 0) {
            html += '<div class="analysis-item"><span class="analysis-label">Concerns:</span><div style="margin-top: 5px;" class="text-muted">';
            sec.concerns.forEach(c => html += `<div>⚠ ${c}</div>`);
            html += '</div></div>';
        }
        if (sec.recommendations && sec.recommendations.length > 0) {
            html += '<div class="analysis-item"><span class="analysis-label">Recommendations:</span><div style="margin-top: 5px;">';
            sec.recommendations.forEach(r => html += `<div>→ ${r}</div>`);
            html += '</div></div>';
        }
        html += '</div>';
    }

    const perf = analysis.performance || {};
    if (perf.score || (perf.observations && perf.observations.length > 0)) {
        html += '<div class="analysis-section">';
        html += '<h4>Performance Analysis</h4>';
        if (perf.score) {
            html += `<div class="analysis-item"><span class="analysis-label">Performance Score:</span><span class="analysis-value">${perf.score}/10</span></div>`;
        }
        if (perf.observations && perf.observations.length > 0) {
            html += '<div class="analysis-item"><span class="analysis-label">Observations:</span><div style="margin-top: 5px;" class="text-muted">';
            perf.observations.forEach(o => html += `<div>• ${o}</div>`);
            html += '</div></div>';
        }
        if (perf.optimization_opportunities && perf.optimization_opportunities.length > 0) {
            html += '<div class="analysis-item"><span class="analysis-label">Optimization Opportunities:</span><div style="margin-top: 5px;">';
            perf.optimization_opportunities.forEach(o => html += `<div>→ ${o}</div>`);
            html += '</div></div>';
        }
        html += '</div>';
    }

    const recs = analysis.recommendations || {};
    if (recs.immediate || recs.short_term || recs.long_term) {
        html += '<div class="analysis-section" style="border-left-color: #22c55e;">';
        html += '<h4>Recommendations</h4>';
        if (recs.immediate && recs.immediate.length > 0) {
            html += '<div class="analysis-item"><span class="badge" style="background: #dc2626;">High Priority</span><div style="margin-top: 5px;">';
            recs.immediate.forEach(r => html += `<div>• ${r}</div>`);
            html += '</div></div>';
        }
        if (recs.short_term && recs.short_term.length > 0) {
            html += '<div class="analysis-item"><span class="badge" style="background: #d97706;">Short Term</span><div style="margin-top: 5px;">';
            recs.short_term.forEach(r => html += `<div>• ${r}</div>`);
            html += '</div></div>';
        }
        if (recs.long_term && recs.long_term.length > 0) {
            html += '<div class="analysis-item"><span class="badge" style="background: #0284c7;">Long Term</span><div style="margin-top: 5px;">';
            recs.long_term.forEach(r => html += `<div>• ${r}</div>`);
            html += '</div></div>';
        }
        html += '</div>';
    }

    const notable = analysis.notable_code || [];
    if (notable.length > 0) {
        html += '<div class="analysis-section">';
        html += '<h4>Notable Code</h4>';
        notable.forEach(n => {
            html += '<div class="analysis-item">';
            html += `<strong>${n.description}</strong>`;
            if (n.file) html += ` <span class="text-muted">(${n.file})</span>`;
            if (n.why_notable) html += `<div style="margin-top: 5px; font-size: 0.9em;">${n.why_notable}</div>`;
            html += '</div>';
        });
        html += '</div>';
    }

    if (analysis.raw_analysis && !analysis.overall_assessment?.quality_score) {
        html += '<div class="analysis-section">';
        html += '<h4>Analysis Output</h4>';
        html += `<pre style="white-space: pre-wrap; font-size: 0.9em;">${analysis.raw_analysis}</pre>`;
        html += '</div>';
    }

    return html;
}
