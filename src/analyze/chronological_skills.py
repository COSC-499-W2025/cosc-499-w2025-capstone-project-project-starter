"""
chronological_skills.py
---
Generates a chronological timeline of detected skills and media-based
metadata across all supported analyzers (code, text, video).

Integrates outputs from multiple analyzers, orders them by file
modification time, filters optionally by date, and exports results
to JSON, CSV, and plain text.

Usage (uncomment demo section at bottom):
    docker compose run --rm backend python3 -m src.analyze.chronological_skills
"""

import numpy as np
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

# Analyzer Imports
from src.analyze.code_analyzer import CodeAnalyzer
from src.analyze.text_analyzer import TextAnalyzer
from src.analyze.video_analyzer import VideoAnalyzer
from src.image_processor import ImageProcessor

# Core Class
class ChronologicalSkillList:
    """Combines multiple analyzers to build a unified skill timeline."""

    def __init__(self):
        self.code_analyzer = CodeAnalyzer()
        self.text_analyzer = TextAnalyzer()
        self.video_analyzer = VideoAnalyzer()
        self.image_analyzer = ImageProcessor()

    def build_skill_timeline(
        self, directory_path: str, after_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Build a chronological list of discovered skills and media metadata.

        Args:
            directory_path: Root directory to analyze.
            after_date: Optional datetime filter. If provided, only include
                        files modified after this date.

        Returns:
            List of normalized event dictionaries.
        """
        timeline: List[Dict[str, Any]] = []

        # --- CODE ANALYSIS ---
        print("[+] Running Code Analyzer...")
        try:
            code_results = self.code_analyzer.analyze_directory(directory_path)
            for r in code_results:
                fp = Path(r.file_path)
                ts = datetime.fromtimestamp(fp.stat().st_mtime)
                if after_date and ts < after_date:
                    continue
                timeline.append({
                    "file": str(fp),
                    "timestamp": ts,
                    "category": "code",
                    "skills": sorted(r.skills),
                    "metadata": {
                        "language": r.language,
                        "frameworks": r.frameworks
                    }
                })
        except Exception as e:
            print(f"[warn] Code analysis failed: {e}")

        # --- TEXT ANALYSIS ---
        print("[+] Running Text Analyzer...")
        try:
            text_files = [
                f for f in Path(directory_path).rglob("*")
                if f.suffix.lower() in {".txt", ".pdf", ".docx"}
            ]
            for f in text_files:
                ts = datetime.fromtimestamp(f.stat().st_mtime)
                if after_date and ts < after_date:
                    continue
                try:
                    metrics = self.text_analyzer.analyze_file(str(f))
                    top_keywords = [k for k, _ in metrics.top_keywords[:10]]
                    timeline.append({
                        "file": str(f),
                        "timestamp": ts,
                        "category": "text",
                        "skills": ["writing"],
                        "metadata": {
                            "word_count": metrics.word_count,
                            "lexical_diversity": metrics.lexical_diversity,
                            "avg_word_length": metrics.avg_word_length,
                        }
                    })
                except Exception as inner_e:
                    print(f"[warn] Skipping text file {f}: {inner_e}")
        except Exception as e:
            print(f"[warn] Text analysis failed: {e}")

        # --- VIDEO ANALYSIS ---
        print("[+] Running Video Analyzer...")
        try:
            video_files = [
                f for f in Path(directory_path).rglob("*")
                if f.suffix.lower() in {".mp4", ".mov", ".avi", ".mkv", ".wmv"}
            ]
            for f in video_files:
                ts = datetime.fromtimestamp(f.stat().st_mtime)
                if after_date and ts < after_date:
                    continue
                try:
                    vres = self.video_analyzer.analyze_file(f)
                    if vres:
                        timeline.append({
                            "file": str(f),
                            "timestamp": ts,
                            "category": "video",
                            "skills": ["videography"],
                            "metadata": vres.to_dict(),
                        })
                except Exception as inner_e:
                    print(f"[warn] Skipping video {f}: {inner_e}")
        except Exception as e:
            print(f"[warn] Video analysis failed: {e}")

        # --- IMAGE ANALYSIS ---
        print("[+] Running Image Analyzer...")
        try:
            image_files = [
                f for f in Path(directory_path).rglob("*")
                if f.suffix.lower() in {".png", ".jpg", ".jpeg"}
            ]
            for f in image_files:
                ts = datetime.fromtimestamp(f.stat().st_mtime)
                if after_date and ts < after_date:
                    continue
                try:
                    result = self.image_analyzer.analyze_image(str(f))
                    timeline.append({
                        "file": str(f),
                        "timestamp": ts,
                        "category": "image",
                        "skills": ["artistry"], 
                        "metadata": result,
                    })
                except Exception as inner_e:
                    print(f"[warn] Skipping image {f}: {inner_e}")
        except Exception as e:
            print(f"[warn] Image analysis failed: {e}")

        timeline.sort(key=lambda e: e["timestamp"])
        return timeline

    def export_results(
        self, events: List[Dict[str, Any]], output_dir: str = "src/analyze/skills_output"
    ):
        """Export timeline data to JSON, CSV, and plain text formats."""
        Path(output_dir).mkdir(exist_ok=True)

        # JSON
        json_path = Path(output_dir) / "chronological_skills.json"
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump([
                {
                    **e,
                    "timestamp": e["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
                    "metadata": make_json_serializable(e["metadata"])
                } for e in events
            ], jf, indent=2)
        print(f"[✓] JSON exported: {json_path}")

        # CSV
        csv_path = Path(output_dir) / "chronological_skills.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as cf:
            writer = csv.writer(cf)
            writer.writerow(["timestamp", "category", "file", "skills"])
            for e in events:
                writer.writerow([
                    e["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
                    e["category"],
                    e["file"],
                    ", ".join(e["skills"]),
                ])
        print(f"[✓] CSV exported: {csv_path}")

        # TXT summary
        txt_path = Path(output_dir) / "chronological_skills.txt"
        with open(txt_path, "w", encoding="utf-8") as tf:
            tf.write("=== Skill & Media Timeline ===\n\n")
            for e in events:
                tf.write(f"[{e['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}] "
                         f"({e['category'].upper()}) {e['file']}\n")
                tf.write(f"  Skills: {', '.join(e['skills'])}\n\n")
        print(f"[✓] TXT exported: {txt_path}")

        return {
            "json": str(json_path),
            "csv": str(csv_path),
            "txt": str(txt_path)
        }
    
def make_json_serializable(obj):
    """Recursively convert NumPy types to Python native types."""
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(v) for v in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return obj
    
# # Command-Line Entrypoint (Demo/Debugging, un-comment to run demo)
# if __name__ == "__main__":
#     analyzer = ChronologicalSkillList()
#     events = analyzer.build_skill_timeline("tests/categorize/demo_projects2", None)
#     analyzer.export_results(events)