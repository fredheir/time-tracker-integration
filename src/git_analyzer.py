"""Git commit analyzer for repository identification"""

import subprocess
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd


class GitAnalyzer:
    """Analyze Git commits to identify which repository was being worked on"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.commits_cache = None
        
    def get_all_commits(self, start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None) -> pd.DataFrame:
        """Fetch all commits from configured repositories"""
        if self.commits_cache is not None:
            return self.commits_cache
            
        all_commits = []
        
        # Get GitHub commits
        github_repos = self.config['repositories'].get('github', [])
        for repo in github_repos:
            commits = self._fetch_github_commits(repo, start_date, end_date)
            all_commits.extend(commits)
            
        # Get local commits
        local_repos = self.config['repositories'].get('local', {})
        for repo_name, repo_path in local_repos.items():
            commits = self._fetch_local_commits(repo_name, repo_path, start_date, end_date)
            all_commits.extend(commits)
            
        self.commits_cache = pd.DataFrame(all_commits)
        return self.commits_cache
        
    def find_repository_for_session(self, session_time: datetime, 
                                   commits_df: pd.DataFrame) -> Tuple[Optional[str], int]:
        """Find which repository was likely being worked on during a session"""
        window_before = self.config['analysis']['commit_window_hours_before']
        window_after = self.config['analysis']['commit_window_hours_after']
        
        window_start = session_time - timedelta(hours=window_before)
        window_end = session_time + timedelta(hours=window_after)
        
        # Find commits within the window
        mask = (commits_df['timestamp'] >= window_start) & \
               (commits_df['timestamp'] <= window_end)
        relevant_commits = commits_df[mask]
        
        if len(relevant_commits) > 0:
            # Return the repo with the most commits in this window
            repo_counts = relevant_commits['repo'].value_counts()
            return repo_counts.index[0], len(relevant_commits)
            
        return None, 0
        
    def _fetch_github_commits(self, repo: str, start_date: Optional[datetime],
                             end_date: Optional[datetime]) -> List[Dict[str, Any]]:
        """Fetch commits from GitHub using gh CLI"""
        commits = []
        
        try:
            # Build the API URL with date filters
            url = f"/repos/{repo}/commits?per_page=100"
            if start_date:
                url += f"&since={start_date.isoformat()}Z"
            if end_date:
                url += f"&until={end_date.isoformat()}Z"
                
            cmd = f'gh api "{url}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                github_commits = json.loads(result.stdout)
                for commit in github_commits:
                    commits.append({
                        'repo': repo,
                        'sha': commit['sha'][:7],
                        'timestamp': datetime.fromisoformat(
                            commit['commit']['author']['date'].replace('Z', '+00:00')
                        ),
                        'message': commit['commit']['message'].split('\n')[0],
                        'author': commit['commit']['author']['name']
                    })
        except Exception as e:
            print(f"Error fetching commits for {repo}: {e}")
            
        return commits
        
    def _fetch_local_commits(self, repo_name: str, repo_path: str,
                            start_date: Optional[datetime],
                            end_date: Optional[datetime]) -> List[Dict[str, Any]]:
        """Fetch commits from local Git repository"""
        commits = []
        
        try:
            # Build git log command
            cmd = f'cd "{repo_path}" && git log --all --format="%H|%aI|%an|%s"'
            if start_date:
                cmd += f' --since="{start_date.isoformat()}"'
            if end_date:
                cmd += f' --until="{end_date.isoformat()}"'
                
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        sha, timestamp, author, message = line.split('|', 3)
                        commits.append({
                            'repo': repo_name,
                            'sha': sha[:7],
                            'timestamp': datetime.fromisoformat(timestamp),
                            'message': message,
                            'author': author
                        })
        except Exception as e:
            print(f"Error fetching commits for {repo_name}: {e}")
            
        return commits