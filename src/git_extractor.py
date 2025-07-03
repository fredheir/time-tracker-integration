#!/usr/bin/env python3
"""Git commit extractor for time tracking"""

import subprocess
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

try:
    from .base_extractor import BaseExtractor, Session
except ImportError:
    from base_extractor import BaseExtractor, Session


class GitExtractor(BaseExtractor):
    """Extract Git commits as time tracking sessions"""
    
    service_name = "Git"
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
    def is_available(self) -> bool:
        """Check if Git data is available"""
        # Check if we have repositories configured
        repos = self.config.get('repositories', {})
        github_repos = repos.get('github', [])
        local_repos = repos.get('local', {})
        
        return len(github_repos) > 0 or len(local_repos) > 0
        
    def extract_sessions(self, start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None) -> List[Session]:
        """Extract Git commits as sessions"""
        if not self.is_available():
            return []
            
        sessions = []
        
        # Get GitHub commits
        github_repos = self.config['repositories'].get('github', [])
        for repo in github_repos:
            # Extract different GitHub event types if enabled
            git_config = self.config['services']['git']
            
            # Commits
            if git_config.get('track_commits', True):
                commits = self._fetch_github_commits(repo, start_date, end_date)
                sessions.extend(self._commits_to_sessions(commits, repo))
            
            # GitHub Actions
            if git_config.get('track_actions', False):
                actions = self._fetch_github_actions(repo, start_date, end_date)
                sessions.extend(self._actions_to_sessions(actions, repo))
            
            # Issues and Issue Comments
            if git_config.get('track_issues', False):
                issues = self._fetch_github_issues(repo, start_date, end_date)
                sessions.extend(self._issues_to_sessions(issues, repo))
                
            # Pull Requests
            if git_config.get('track_pull_requests', False):
                prs = self._fetch_github_pull_requests(repo, start_date, end_date)
                sessions.extend(self._pull_requests_to_sessions(prs, repo))
            
        # Get local commits
        local_repos = self.config['repositories'].get('local', {})
        for repo_name, repo_path in local_repos.items():
            commits = self._fetch_local_commits(repo_name, repo_path, start_date, end_date)
            sessions.extend(self._commits_to_sessions(commits, repo_name))
            
        return sorted(sessions, key=lambda s: s.start)
        
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
        
    def _commits_to_sessions(self, commits: List[Dict[str, Any]], repo: str) -> List[Session]:
        """Convert Git commits to Session objects"""
        sessions = []
        
        for commit in commits:
            # Create a point-in-time event for each commit
            # Duration is configurable but represents visualization only, not actual work time
            commit_duration = self.config['services']['git'].get('commit_duration_minutes', 1)
            start_time = commit['timestamp']
            end_time = start_time + timedelta(minutes=commit_duration)
            
            session = Session(
                start=start_time,
                end=end_time,
                service="Git",
                project=repo.split('/')[-1] if '/' in repo else repo,  # Extract repo name
                metrics={
                    'interactions': 1,
                    'commit_sha': commit['sha'],
                    'commit_message': commit['message'],
                    'author': commit['author'],
                    'repository': repo,
                    'activity_count': 1
                }
            )
            
            sessions.append(session)
            
        return sessions
    
    def _fetch_github_actions(self, repo: str, start_date: Optional[datetime],
                             end_date: Optional[datetime]) -> List[Dict[str, Any]]:
        """Fetch GitHub Actions workflow runs using gh CLI"""
        runs = []
        
        try:
            # GitHub Actions API endpoint for workflow runs
            cmd = f'gh api "/repos/{repo}/actions/runs?per_page=100" --jq ".workflow_runs[]"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Process each workflow run line by line
                for line in result.stdout.strip().split('\n'):
                    if line:
                        run = json.loads(line)
                        run_time = datetime.fromisoformat(run['created_at'].replace('Z', '+00:00'))
                        
                        # Filter by date range
                        if start_date and run_time < start_date:
                            continue
                        if end_date and run_time > end_date:
                            continue
                            
                        runs.append({
                            'id': run['id'],
                            'name': run['name'],
                            'event': run['event'],
                            'status': run['status'],
                            'conclusion': run.get('conclusion', 'in_progress'),
                            'created_at': run_time,
                            'updated_at': datetime.fromisoformat(run['updated_at'].replace('Z', '+00:00')),
                            'workflow_name': run['name'],
                            'run_number': run['run_number'],
                            'actor': run['actor']['login'] if run.get('actor') else 'unknown'
                        })
        except Exception as e:
            print(f"Error fetching GitHub Actions for {repo}: {e}")
            
        return runs
    
    def _actions_to_sessions(self, runs: List[Dict[str, Any]], repo: str) -> List[Session]:
        """Convert GitHub Actions runs to Session objects"""
        sessions = []
        
        for run in runs:
            # Duration from created to updated (or default if still running)
            duration = (run['updated_at'] - run['created_at']).total_seconds() / 60
            if duration < 1:
                duration = self.config['services']['git'].get('action_duration_minutes', 10)
                
            session = Session(
                start=run['created_at'],
                end=run['created_at'] + timedelta(minutes=duration),
                service="Git",
                project=repo.split('/')[-1],
                metrics={
                    'type': 'github_action',
                    'action_id': run['id'],
                    'workflow_name': run['workflow_name'],
                    'event': run['event'],
                    'status': run['status'],
                    'conclusion': run['conclusion'],
                    'run_number': run['run_number'],
                    'actor': run['actor'],
                    'repository': repo,
                    'activity_count': 1
                }
            )
            sessions.append(session)
            
        return sessions
    
    def _fetch_github_issues(self, repo: str, start_date: Optional[datetime],
                            end_date: Optional[datetime]) -> List[Dict[str, Any]]:
        """Fetch GitHub issues and comments using gh CLI"""
        issues_data = []
        
        # Make timezone-aware copies of dates if needed
        tz_start_date = start_date
        tz_end_date = end_date
        
        try:
            # Fetch issues with their events
            cmd = f'gh api "/repos/{repo}/issues?state=all&per_page=100&sort=updated&direction=desc" --jq ".[]"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        issue = json.loads(line)
                        issue_created = datetime.fromisoformat(issue['created_at'].replace('Z', '+00:00'))
                        issue_updated = datetime.fromisoformat(issue['updated_at'].replace('Z', '+00:00'))
                        
                        # Check if issue was created or updated in our date range
                        # Ensure timezone-aware comparison
                        if tz_start_date and tz_start_date.tzinfo is None:
                            tz_start_date = tz_start_date.replace(tzinfo=issue_created.tzinfo)
                        if tz_end_date and tz_end_date.tzinfo is None:
                            tz_end_date = tz_end_date.replace(tzinfo=issue_created.tzinfo)
                            
                        if tz_end_date and issue_updated < tz_start_date:
                            continue
                        if tz_start_date and issue_created > tz_end_date:
                            continue
                            
                        issue_data = {
                            'number': issue['number'],
                            'title': issue['title'],
                            'state': issue['state'],
                            'created_at': issue_created,
                            'updated_at': issue_updated,
                            'user': issue['user']['login'],
                            'comments_count': issue['comments']
                        }
                        
                        # Add issue creation event
                        if (not tz_start_date or issue_created >= tz_start_date) and (not tz_end_date or issue_created <= tz_end_date):
                            issues_data.append({
                                **issue_data,
                                'event_type': 'issue_created',
                                'event_time': issue_created
                            })
                        
                        # Fetch comments for this issue
                        if issue['comments'] > 0:
                            comments_cmd = f'gh api "/repos/{repo}/issues/{issue["number"]}/comments" --jq ".[]"'
                            comments_result = subprocess.run(comments_cmd, shell=True, capture_output=True, text=True)
                            
                            if comments_result.returncode == 0:
                                for comment_line in comments_result.stdout.strip().split('\n'):
                                    if comment_line:
                                        comment = json.loads(comment_line)
                                        comment_time = datetime.fromisoformat(comment['created_at'].replace('Z', '+00:00'))
                                        
                                        if (not tz_start_date or comment_time >= tz_start_date) and (not tz_end_date or comment_time <= tz_end_date):
                                            issues_data.append({
                                                **issue_data,
                                                'event_type': 'issue_comment',
                                                'event_time': comment_time,
                                                'comment_author': comment['user']['login'],
                                                'comment_id': comment['id']
                                            })
                                            
        except Exception as e:
            print(f"Error fetching issues for {repo}: {e}")
            
        return issues_data
    
    def _issues_to_sessions(self, issues: List[Dict[str, Any]], repo: str) -> List[Session]:
        """Convert GitHub issues to Session objects"""
        sessions = []
        
        for issue in issues:
            # Different durations for different event types
            if issue['event_type'] == 'issue_created':
                duration = self.config['services']['git'].get('issue_creation_duration_minutes', 15)
            else:  # issue_comment
                duration = self.config['services']['git'].get('issue_comment_duration_minutes', 5)
                
            session = Session(
                start=issue['event_time'],
                end=issue['event_time'] + timedelta(minutes=duration),
                service="Git",
                project=repo.split('/')[-1],
                metrics={
                    'type': issue['event_type'],
                    'issue_number': issue['number'],
                    'issue_title': issue['title'],
                    'issue_state': issue['state'],
                    'author': issue.get('comment_author', issue['user']),
                    'repository': repo,
                    'activity_count': 1
                }
            )
            sessions.append(session)
            
        return sessions
    
    def _fetch_github_pull_requests(self, repo: str, start_date: Optional[datetime],
                                   end_date: Optional[datetime]) -> List[Dict[str, Any]]:
        """Fetch GitHub pull request events using gh CLI"""
        pr_events = []
        
        # Make timezone-aware copies of dates if needed
        tz_start_date = start_date
        tz_end_date = end_date
        
        try:
            # Fetch pull requests
            cmd = f'gh api "/repos/{repo}/pulls?state=all&per_page=100&sort=updated&direction=desc" --jq ".[]"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        pr = json.loads(line)
                        pr_created = datetime.fromisoformat(pr['created_at'].replace('Z', '+00:00'))
                        pr_updated = datetime.fromisoformat(pr['updated_at'].replace('Z', '+00:00'))
                        
                        # Filter by date range
                        # Ensure timezone-aware comparison
                        if tz_start_date and tz_start_date.tzinfo is None:
                            tz_start_date = tz_start_date.replace(tzinfo=pr_created.tzinfo)
                        if tz_end_date and tz_end_date.tzinfo is None:
                            tz_end_date = tz_end_date.replace(tzinfo=pr_created.tzinfo)
                            
                        if tz_end_date and pr_updated < tz_start_date:
                            continue
                        if tz_start_date and pr_created > tz_end_date:
                            continue
                            
                        pr_data = {
                            'number': pr['number'],
                            'title': pr['title'],
                            'state': pr['state'],
                            'user': pr['user']['login'],
                            'merged': pr.get('merged_at') is not None
                        }
                        
                        # PR creation event
                        if (not tz_start_date or pr_created >= tz_start_date) and (not tz_end_date or pr_created <= tz_end_date):
                            pr_events.append({
                                **pr_data,
                                'event_type': 'pr_created',
                                'event_time': pr_created
                            })
                        
                        # PR merge event
                        if pr.get('merged_at'):
                            merge_time = datetime.fromisoformat(pr['merged_at'].replace('Z', '+00:00'))
                            if (not tz_start_date or merge_time >= tz_start_date) and (not tz_end_date or merge_time <= tz_end_date):
                                pr_events.append({
                                    **pr_data,
                                    'event_type': 'pr_merged',
                                    'event_time': merge_time,
                                    'merged_by': pr.get('merged_by', {}).get('login', 'unknown')
                                })
                        
                        # Fetch PR reviews and comments
                        pr_number = pr['number']
                        
                        # Reviews
                        reviews_cmd = f'gh api "/repos/{repo}/pulls/{pr_number}/reviews" --jq ".[]"'
                        reviews_result = subprocess.run(reviews_cmd, shell=True, capture_output=True, text=True)
                        
                        if reviews_result.returncode == 0 and reviews_result.stdout.strip():
                            for review_line in reviews_result.stdout.strip().split('\n'):
                                if review_line:
                                    review = json.loads(review_line)
                                    review_time = datetime.fromisoformat(review['submitted_at'].replace('Z', '+00:00'))
                                    
                                    if (not tz_start_date or review_time >= tz_start_date) and (not tz_end_date or review_time <= tz_end_date):
                                        pr_events.append({
                                            **pr_data,
                                            'event_type': 'pr_reviewed',
                                            'event_time': review_time,
                                            'reviewer': review['user']['login'],
                                            'review_state': review['state']
                                        })
                                        
        except Exception as e:
            print(f"Error fetching pull requests for {repo}: {e}")
            
        return pr_events
    
    def _pull_requests_to_sessions(self, pr_events: List[Dict[str, Any]], repo: str) -> List[Session]:
        """Convert GitHub pull request events to Session objects"""
        sessions = []
        
        duration_map = {
            'pr_created': self.config['services']['git'].get('pr_creation_duration_minutes', 20),
            'pr_merged': self.config['services']['git'].get('pr_merge_duration_minutes', 10),
            'pr_reviewed': self.config['services']['git'].get('pr_review_duration_minutes', 15)
        }
        
        for event in pr_events:
            duration = duration_map.get(event['event_type'], 10)
            
            metrics = {
                'type': event['event_type'],
                'pr_number': event['number'],
                'pr_title': event['title'],
                'pr_state': event['state'],
                'repository': repo,
                'activity_count': 1
            }
            
            # Add event-specific fields
            if event['event_type'] == 'pr_created':
                metrics['author'] = event['user']
            elif event['event_type'] == 'pr_merged':
                metrics['merged_by'] = event.get('merged_by', 'unknown')
            elif event['event_type'] == 'pr_reviewed':
                metrics['reviewer'] = event['reviewer']
                metrics['review_state'] = event['review_state']
                
            session = Session(
                start=event['event_time'],
                end=event['event_time'] + timedelta(minutes=duration),
                service="Git",
                project=repo.split('/')[-1],
                metrics=metrics
            )
            sessions.append(session)
            
        return sessions