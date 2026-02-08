"""
Git Repository Analyzer
Analyzes Git repositories to extract contribution metrics, commit history, and contributor statistics.
"""
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import subprocess
import re


class GitAnalyzer:
    """Analyzer for Git repositories."""
    
    def __init__(self, repo_path: str):
        """
        Initialize Git analyzer.
        
        Args:
            repo_path: Path to the Git repository
        """
        self.repo_path = Path(repo_path)
        if not self.repo_path.exists():
            raise FileNotFoundError(f"Repository not found: {repo_path}")
        
        self.git_dir = self.repo_path / ".git"
        if not self.git_dir.exists():
            raise ValueError(f"Not a Git repository: {repo_path}")
    
    def _run_git_command(self, args: List[str]) -> str:
        """Run a git command and return output."""
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Git command failed: {e.stderr}")
    
    def get_commit_count(self) -> int:
        """Get total number of commits."""
        output = self._run_git_command(["rev-list", "--count", "HEAD"])
        return int(output)
    
    def get_contributors(self) -> List[Dict[str, Any]]:
        """
        Get list of all contributors with their statistics.
        
        Returns:
            List of contributor dictionaries with name, email, and commit count
        """
        output = self._run_git_command([
            "shortlog", "-sne", "--all", "--no-merges"
        ])
        
        contributors = []
        for line in output.split('\n'):
            if not line.strip():
                continue
            
            # Parse format: "   123  John Doe <john@example.com>"
            match = re.match(r'\s*(\d+)\s+([^<]+)<([^>]+)>', line)
            if match:
                commits = int(match.group(1))
                name = match.group(2).strip()
                email = match.group(3).strip()
                
                contributors.append({
                    "name": name,
                    "email": email,
                    "commits": commits
                })
        
        return contributors
    
    def get_contributor_stats(self, author_email: str) -> Dict[str, Any]:
        """
        Get detailed statistics for a specific contributor.
        
        Args:
            author_email: Email of the contributor
            
        Returns:
            Dictionary with detailed contributor statistics
        """
        # Get commits by author
        commit_log = self._run_git_command([
            "log", "--author", author_email, "--pretty=format:%H|%ad|%s",
            "--date=iso", "--no-merges"
        ])
        
        if not commit_log:
            return {
                "commits": 0,
                "files_changed": 0,
                "insertions": 0,
                "deletions": 0,
                "commit_messages": []
            }
        
        commits = commit_log.split('\n')
        commit_hashes = [c.split('|')[0] for c in commits if c]
        
        # Get stats for this author
        stats_output = self._run_git_command([
            "log", "--author", author_email, "--shortstat", "--no-merges"
        ])
        
        # Parse insertions and deletions
        insertions = 0
        deletions = 0
        files_changed = 0
        
        for line in stats_output.split('\n'):
            if 'file' in line and 'changed' in line:
                # Parse: "3 files changed, 45 insertions(+), 12 deletions(-)"
                files_match = re.search(r'(\d+) file', line)
                insert_match = re.search(r'(\d+) insertion', line)
                delete_match = re.search(r'(\d+) deletion', line)
                
                if files_match:
                    files_changed += int(files_match.group(1))
                if insert_match:
                    insertions += int(insert_match.group(1))
                if delete_match:
                    deletions += int(delete_match.group(1))
        
        # Get first and last commit dates
        first_commit = self._run_git_command([
            "log", "--author", author_email, "--reverse", 
            "--pretty=format:%ad", "--date=iso", "-1", "--no-merges"
        ])
        
        last_commit = self._run_git_command([
            "log", "--author", author_email,
            "--pretty=format:%ad", "--date=iso", "-1", "--no-merges"
        ])
        
        # Get files touched by this author
        files_touched = self._run_git_command([
            "log", "--author", author_email, "--name-only",
            "--pretty=format:", "--no-merges"
        ])
        
        unique_files = set(f for f in files_touched.split('\n') if f.strip())
        
        return {
            "commits": len(commit_hashes),
            "files_changed": files_changed,
            "insertions": insertions,
            "deletions": deletions,
            "first_commit": first_commit,
            "last_commit": last_commit,
            "unique_files_touched": len(unique_files),
            "files_touched": sorted(unique_files)
        }
    
    def get_file_extensions(self) -> Dict[str, int]:
        """Get count of files by extension in the repository."""
        try:
            output = self._run_git_command(["ls-files"])
            files = output.split('\n')
            
            extensions = defaultdict(int)
            for file in files:
                if not file:
                    continue
                ext = Path(file).suffix
                if ext:
                    extensions[ext] = extensions.get(ext, 0) + 1
                else:
                    extensions['[no extension]'] = extensions.get('[no extension]', 0) + 1
            
            return dict(extensions)
        except Exception:
            return {}
    
    def get_commit_timeline(self, days: int = 90) -> Dict[str, int]:
        """
        Get commit timeline for the last N days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary mapping date to commit count
        """
        since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        try:
            output = self._run_git_command([
                "log", "--since", since_date, "--pretty=format:%ad",
                "--date=short", "--no-merges"
            ])
            
            timeline = defaultdict(int)
            for line in output.split('\n'):
                if line:
                    timeline[line] += 1
            
            return dict(timeline)
        except Exception:
            return {}
    
    def get_branch_count(self) -> int:
        """Get number of branches."""
        try:
            output = self._run_git_command(["branch", "-a"])
            return len([b for b in output.split('\n') if b.strip()])
        except Exception:
            return 0
    
    def get_remote_url(self) -> Optional[str]:
        """Get remote repository URL."""
        try:
            return self._run_git_command(["config", "--get", "remote.origin.url"])
        except Exception:
            return None
    
    def analyze_repository(self) -> Dict[str, Any]:
        """
        Perform comprehensive repository analysis.
        
        Returns:
            Dictionary with complete repository analysis
        """
        print("📊 Analyzing Git repository...")
        
        # Basic stats
        total_commits = self.get_commit_count()
        contributors = self.get_contributors()
        file_extensions = self.get_file_extensions()
        timeline = self.get_commit_timeline(90)
        branch_count = self.get_branch_count()
        remote_url = self.get_remote_url()
        
        # Calculate contribution percentages
        total_contributor_commits = sum(c['commits'] for c in contributors)
        for contributor in contributors:
            contributor['percentage'] = (contributor['commits'] / total_contributor_commits * 100) if total_contributor_commits > 0 else 0
        
        # Get detailed stats for each contributor
        print(f"   Found {len(contributors)} contributor(s)")
        for i, contributor in enumerate(contributors):
            print(f"   Analyzing contributor {i+1}/{len(contributors)}: {contributor['name']}")
            detailed_stats = self.get_contributor_stats(contributor['email'])
            contributor.update(detailed_stats)
        
        return {
            "repository_path": str(self.repo_path),
            "remote_url": remote_url,
            "total_commits": total_commits,
            "branch_count": branch_count,
            "contributor_count": len(contributors),
            "contributors": contributors,
            "file_extensions": file_extensions,
            "commit_timeline_90_days": timeline,
            "analysis_date": datetime.now().isoformat()
        }



