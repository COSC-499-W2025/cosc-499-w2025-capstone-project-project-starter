# tests/test_resume_evidence.py

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from resume.evidence_extractor import build_evidence


class TestResumeEvidence:
    def test_build_evidence_includes_scale_timeline_tech(self):
        summary = {
            "languages": {
                "primary_language": "Python",
                "languages": ["Python", "JavaScript"]
            },
            "frameworks": ["React", "Docker"],
            "time_analysis": {
                "duration_days": 30,
                "intensity": "High",
                "first_file": "2024-01-01",
                "last_file": "2024-01-30"
            },
            "project_structure": {
                "has_tests": True,
                "has_docs": True
            },
            "file_statistics": {
                "total_lines_of_code": 2500,
                "total_files": 25
            },
            "collaboration_analysis": {
                "collaboration_level": "Team"
            }
        }

        evidence = build_evidence(summary)

        assert isinstance(evidence, list)
        assert len(evidence) >= 3

        joined = " ".join(evidence).lower()

        # scale
        assert "loc" in joined or "codebase" in joined
        assert "files" in joined

        # timeline
        assert "days" in joined or "timeline" in joined

        # tech
        assert "tech" in joined or "technolog" in joined
        assert "python" in joined

        # quality
        assert "tests" in joined
        assert "documentation" in joined or "docs" in joined

        # collaboration (optional)
        assert "collabor" in joined or "team" in joined

    def test_build_evidence_handles_missing_fields(self):
        summary = {
            "languages": {"primary_language": "C", "languages": ["C"]},
            # no frameworks, no time_analysis, no stats, no structure
        }

        evidence = build_evidence(summary)
        assert isinstance(evidence, list)
        assert len(evidence) >= 1  # should still return fallback or tech evidence

    def test_build_evidence_quality_score_line(self):
        summary = {
            "languages": {"primary_language": "Python", "languages": ["Python"]},
            "code_analysis": {
                "code_quality_summary": {"average_quality_score": 87.55}
            }
        }

        evidence = build_evidence(summary)
        joined = " ".join(evidence).lower()
        assert "quality" in joined
        assert "87.6" in joined or "87.5" in joined or "87" in joined  # rounding tolerant

    def test_build_evidence_docs_only(self):
        summary = {
            "languages": {"primary_language": "Python", "languages": ["Python"]},
            "project_structure": {"has_docs": True, "has_tests": False},
        }

        evidence = build_evidence(summary)
        joined = " ".join(evidence).lower()
        assert "documentation" in joined or "docs" in joined
        assert "tests" not in joined  # should not claim tests if absent

    def test_build_evidence_test_only(self):
        summary = {
            "languages": {"primary_language": "Python", "languages": ["Python"]},
            "project_structure": {"has_tests": True, "has_docs": False},
        }

        evidence = build_evidence(summary)
        joined = " ".join(evidence).lower()
        assert "tests" in joined
        assert "documentation" not in joined

    def test_build_evidence_dedup_and_cap(self):
        summary = {
            "languages": {"primary_language": "Python", "languages": ["Python", "Python", "Python"]},
            "frameworks": ["React", "React", "Docker"],
            "time_analysis": {"duration_days": 60, "intensity": "High"},
            "file_statistics": {"total_lines_of_code": 10000, "total_files": 200},
            "project_structure": {"has_tests": True, "has_docs": True},
            "collaboration_analysis": {"collaboration_level": "Team"},
            "code_analysis": {"code_quality_summary": {"average_quality_score": 90.0}},
        }

        evidence = build_evidence(summary)
        assert len(evidence) <= 5  # extractor caps bullets for resume brevity

        # ensure no obvious duplicates
        lowered = [e.lower().strip() for e in evidence]
        assert len(lowered) == len(set(lowered))
