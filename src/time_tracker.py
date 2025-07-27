#!/usr/bin/env python3
"""Main time tracking integration script"""

import argparse
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
from collections import defaultdict

try:
    from .base_extractor import Session
    from .claude_extractor import ClaudeExtractor
    from .cursor_realtime_extractor import CursorRealtimeExtractor
    from .git_extractor import GitExtractor
    from .git_analyzer import GitAnalyzer
except ImportError:
    # Running as script
    from base_extractor import Session
    from claude_extractor import ClaudeExtractor
    from cursor_realtime_extractor import CursorRealtimeExtractor
    from git_extractor import GitExtractor
    from git_analyzer import GitAnalyzer


class TimeTracker:
    """Main time tracking integration class"""
    
    def __init__(self, config_path: str = './config/config.yaml'):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
            
        self.extractors = []
        self._initialize_extractors()
        self.git_analyzer = GitAnalyzer(self.config)
        
    def _initialize_extractors(self):
        """Initialize enabled service extractors"""
        if self.config['services']['claude']['enabled']:
            self.extractors.append(ClaudeExtractor(self.config))
            
        if self.config['services']['cursor']['enabled']:
            self.extractors.append(CursorRealtimeExtractor(self.config))
            
        if self.config['services'].get('git', {}).get('enabled', True):
            self.extractors.append(GitExtractor(self.config))
            
    def extract_all_sessions(self, start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None) -> List[Session]:
        """Extract sessions from all enabled services"""
        all_sessions = []
        
        for extractor in self.extractors:
            if extractor.is_available():
                print(f"\nExtracting {extractor.service_name} sessions...")
                sessions = extractor.extract_sessions(start_date, end_date)
                print(f"Found {len(sessions)} {extractor.service_name} sessions")
                all_sessions.extend(sessions)
            else:
                print(f"\n{extractor.service_name} data not available")
                
        return sorted(all_sessions, key=lambda s: s.start)
        
    def analyze_sessions(self, sessions: List[Session], 
                        start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None) -> pd.DataFrame:
        """Analyze sessions and match with Git commits"""
        print("\nFetching Git commits...")
        commits_df = self.git_analyzer.get_all_commits(start_date, end_date)
        print(f"Found {len(commits_df)} commits")
        
        # Match sessions with repositories
        analyzed_sessions = []
        for session in sessions:
            repo, commit_count = self.git_analyzer.find_repository_for_session(
                session.start, commits_df
            )
            
            session_data = session.to_dict()
            session_data['identified_repo'] = repo or session.project
            session_data['commits_in_window'] = commit_count
            analyzed_sessions.append(session_data)
            
        return pd.DataFrame(analyzed_sessions)
        
    def generate_report(self, sessions_df: pd.DataFrame, 
                       start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None):
        """Generate comprehensive time tracking report"""
        print("\n" + "=" * 80)
        print("TIME TRACKING INTEGRATION REPORT")
        if start_date or end_date:
            date_range = []
            if start_date:
                date_range.append(f"From: {start_date.date()}")
            if end_date:
                date_range.append(f"To: {end_date.date()}")
            print(" | ".join(date_range))
        print("=" * 80)
        
        # Summary by repository
        self._print_repository_summary(sessions_df)
        
        # Summary by service
        self._print_service_summary(sessions_df)
        
        # Daily breakdown
        self._print_daily_breakdown(sessions_df)
        
        # Save outputs
        self._save_outputs(sessions_df)
        
    def _print_repository_summary(self, df: pd.DataFrame):
        """Print summary grouped by repository"""
        print("\n=== SUMMARY BY REPOSITORY ===")
        
        repo_stats = defaultdict(lambda: {
            'total_hours': 0,
            'sessions': 0,
            'services': set(),
            'commits': 0
        })
        
        for _, row in df.iterrows():
            # Use project field for Claude sessions, identified_repo for others
            if row['service'] == 'Claude':
                repo = row['project'] or 'Unknown'
            else:
                repo = row['identified_repo'] or row['project'] or 'Unknown'
            repo_stats[repo]['total_hours'] += row['duration_hours']
            repo_stats[repo]['sessions'] += 1
            repo_stats[repo]['services'].add(row['service'])
            repo_stats[repo]['commits'] = max(
                repo_stats[repo]['commits'], 
                row.get('commits_in_window', 0)
            )
            
        # Sort by total hours
        sorted_repos = sorted(repo_stats.items(), 
                            key=lambda x: x[1]['total_hours'], 
                            reverse=True)
        
        for repo, stats in sorted_repos:
            print(f"\n{repo}:")
            print(f"  Total Time: {stats['total_hours']:.1f} hours")
            print(f"  Sessions: {stats['sessions']}")
            print(f"  Services: {', '.join(sorted(stats['services']))}")
            if stats['commits'] > 0:
                print(f"  Related Commits: {stats['commits']}")
                
    def _print_service_summary(self, df: pd.DataFrame):
        """Print summary grouped by service"""
        print("\n=== SUMMARY BY SERVICE ===")
        
        service_summary = df.groupby('service').agg({
            'duration_hours': 'sum',
            'identified_repo': 'count'
        }).rename(columns={'identified_repo': 'sessions'})
        
        for service, row in service_summary.iterrows():
            print(f"\n{service}:")
            print(f"  Total Time: {row['duration_hours']:.1f} hours")
            print(f"  Sessions: {row['sessions']}")
            
    def _print_daily_breakdown(self, df: pd.DataFrame):
        """Print daily activity breakdown"""
        print("\n=== DAILY BREAKDOWN ===")
        
        # Add date column
        df['date'] = pd.to_datetime(df['start'], utc=True).dt.date
        
        # Get last 7 days
        recent_dates = sorted(df['date'].unique(), reverse=True)[:7]
        
        for date in recent_dates:
            day_data = df[df['date'] == date]
            total_hours = day_data['duration_hours'].sum()
            
            print(f"\n{date.strftime('%A, %B %d, %Y')}:")
            print(f"  Total: {total_hours:.1f} hours")
            
            for _, session in day_data.iterrows():
                start = pd.to_datetime(session['start'])
                end = pd.to_datetime(session['end'])
                # Use project field for Claude sessions, identified_repo for others
                if session['service'] == 'Claude':
                    repo = session['project'] or 'Unknown'
                else:
                    repo = session['identified_repo'] or session['project'] or 'Unknown'
                
                print(f"  {start.strftime('%H:%M')} - {end.strftime('%H:%M')} "
                      f"[{session['service']}] {repo}")
                      
    def _save_outputs(self, df: pd.DataFrame):
        """Save output files"""
        output_dir = Path(self.config['output']['data_directory'])
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if self.config['output']['generate_csv']:
            csv_path = output_dir / f'time_tracking_{timestamp}.csv'
            df.to_csv(csv_path, index=False)
            print(f"\nSaved CSV to: {csv_path}")
            
        if self.config['output']['generate_json']:
            json_path = output_dir / f'time_tracking_{timestamp}.json'
            df.to_json(json_path, orient='records', date_format='iso')
            print(f"Saved JSON to: {json_path}")


def main():
    parser = argparse.ArgumentParser(description='Integrate time tracking from multiple sources')
    parser.add_argument('--config', default='./config/config.yaml',
                       help='Path to configuration file')
    parser.add_argument('--start', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--days', type=int, help='Number of days to analyze (from today)')
    
    args = parser.parse_args()
    
    # Parse date arguments
    start_date = None
    end_date = None
    
    if args.days:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=args.days)
    else:
        if args.start:
            start_date = datetime.strptime(args.start, '%Y-%m-%d')
        if args.end:
            end_date = datetime.strptime(args.end, '%Y-%m-%d')
            
    # Run time tracking
    tracker = TimeTracker(args.config)
    sessions = tracker.extract_all_sessions(start_date, end_date)
    
    if not sessions:
        print("No sessions found in the specified date range")
        return
        
    sessions_df = tracker.analyze_sessions(sessions, start_date, end_date)
    tracker.generate_report(sessions_df, start_date, end_date)


if __name__ == '__main__':
    main()