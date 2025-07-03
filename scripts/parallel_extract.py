#!/usr/bin/env python3
"""Parallel extraction runner for time tracker"""

import sys
import os
import json
import yaml
import argparse
import tempfile
import concurrent.futures
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.claude_extractor import ClaudeExtractor
from src.cursor_realtime_extractor import CursorRealtimeExtractor
from src.git_extractor import GitExtractor
from src.time_tracker import TimeTracker, Session


def extract_claude(config, start_date, end_date):
    """Extract Claude sessions"""
    print("[Claude] Starting extraction...")
    extractor = ClaudeExtractor(config)
    if extractor.is_available():
        sessions = extractor.extract_sessions(start_date, end_date)
        print(f"[Claude] Extracted {len(sessions)} sessions")
        return sessions
    else:
        print("[Claude] Not available")
        return []


def extract_cursor(config, start_date, end_date):
    """Extract Cursor sessions"""
    print("[Cursor] Starting extraction...")
    extractor = CursorRealtimeExtractor(config)
    if extractor.is_available():
        sessions = extractor.extract_sessions(start_date, end_date)
        print(f"[Cursor] Extracted {len(sessions)} sessions")
        return sessions
    else:
        print("[Cursor] Not available")
        return []


def extract_git(config, start_date, end_date):
    """Extract Git sessions"""
    print("[Git] Starting extraction...")
    extractor = GitExtractor(config)
    if extractor.is_available():
        sessions = extractor.extract_sessions(start_date, end_date)
        print(f"[Git] Extracted {len(sessions)} sessions")
        return sessions
    else:
        print("[Git] Not available")
        return []


def main():
    parser = argparse.ArgumentParser(description='Parallel time tracking extraction')
    parser.add_argument('--days', type=int, required=True, help='Number of days to analyze')
    parser.add_argument('--config', default='./config/config.yaml', help='Config file path')
    
    args = parser.parse_args()
    
    # Load config
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=args.days)
    
    print(f"Parallel extraction for {args.days} days...")
    print(f"From: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Run extractors in parallel
    all_sessions = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        # Submit all extraction tasks
        futures = {
            executor.submit(extract_claude, config, start_date, end_date): 'Claude',
            executor.submit(extract_cursor, config, start_date, end_date): 'Cursor',
            executor.submit(extract_git, config, start_date, end_date): 'Git'
        }
        
        # Collect results
        for future in concurrent.futures.as_completed(futures):
            source = futures[future]
            try:
                sessions = future.result()
                all_sessions.extend(sessions)
            except Exception as e:
                print(f"[{source}] Error: {e}")
    
    print(f"\nTotal sessions from all sources: {len(all_sessions)}")
    
    # Run analysis and generate report
    tracker = TimeTracker(config)
    sessions_df = tracker.analyze_sessions(all_sessions, start_date, end_date)
    tracker.generate_report(sessions_df, start_date, end_date)


if __name__ == '__main__':
    main()