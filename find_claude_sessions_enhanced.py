#!/usr/bin/env python3
"""
Enhanced Claude Session Finder
- Adds session duration calculations
- Includes Cursor IDE sessions
- Efficient content-based search
"""

import json
import os
import sys
import mmap
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Tuple
from collections import defaultdict


def parse_date(date_str: str) -> datetime:
    """Parse date string in various formats."""
    formats = [
        "%Y-%m-%d",
        "%d %b %Y",
        "%d %B %Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %b",  # Handle "27 jul" format
        "%d %B"   # Handle "27 July" format
    ]
    
    date_str = date_str.strip()
    
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            # For formats without year, assume current year
            if fmt in ["%d %b", "%d %B"]:
                current_year = datetime.now().year
                parsed = parsed.replace(year=current_year)
            return parsed
        except ValueError:
            continue
    
    # Try parsing just the date part if there's time info
    if 'T' in date_str:
        date_part = date_str.split('T')[0]
        return datetime.strptime(date_part, "%Y-%m-%d")
    
    raise ValueError(f"Could not parse date: {date_str}")


def calculate_session_duration(interactions: List[Dict[str, Any]], max_gap_minutes: int = 15) -> Dict[str, Any]:
    """
    Calculate session duration with gap detection.
    Splits work into blocks when gaps exceed max_gap_minutes.
    """
    if not interactions:
        return {
            'duration_minutes': 0,
            'formatted': '0m',
            'work_blocks': [],
            'gaps': [],
            'should_split': False
        }
    
    # Sort interactions by timestamp
    sorted_interactions = sorted(interactions, 
                               key=lambda x: x.get('timestamp', ''))
    
    # Parse timestamps and detect gaps
    work_blocks = []
    current_block = []
    gaps = []
    max_gap = timedelta(minutes=max_gap_minutes)
    
    for i, interaction in enumerate(sorted_interactions):
        ts_str = interaction.get('timestamp', '')
        try:
            ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        except:
            continue
            
        if i == 0:
            current_block = [(ts, interaction)]
        else:
            prev_ts = current_block[-1][0] if current_block else ts
            gap = ts - prev_ts
            
            if gap > max_gap:
                # Gap detected - finish current block
                if current_block:
                    work_blocks.append(current_block)
                    gaps.append({
                        'start': prev_ts,
                        'end': ts,
                        'duration_minutes': int(gap.total_seconds() / 60)
                    })
                current_block = [(ts, interaction)]
            else:
                current_block.append((ts, interaction))
    
    # Don't forget the last block
    if current_block:
        work_blocks.append(current_block)
    
    # Calculate total duration excluding gaps
    total_duration_minutes = 0
    block_details = []
    
    for block in work_blocks:
        if not block:
            continue
            
        block_timestamps = [ts for ts, _ in block]
        first_ts = min(block_timestamps)
        last_ts = max(block_timestamps)
        
        # Calculate block duration
        if len(block) == 1:
            block_duration = timedelta(minutes=5)  # Single interaction
        else:
            block_duration = (last_ts - first_ts) + timedelta(minutes=3)  # Buffer
        
        block_minutes = int(block_duration.total_seconds() / 60)
        total_duration_minutes += block_minutes
        
        block_details.append({
            'start': first_ts.isoformat(),
            'end': last_ts.isoformat(),
            'duration_minutes': block_minutes,
            'interaction_count': len(block)
        })
    
    # Format total duration
    hours = total_duration_minutes // 60
    minutes = total_duration_minutes % 60
    
    if hours > 0:
        formatted = f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
    else:
        formatted = f"{minutes}m"
    
    # Get overall time span
    all_timestamps = []
    for block in work_blocks:
        all_timestamps.extend([ts for ts, _ in block])
    
    if all_timestamps:
        first_interaction = min(all_timestamps).isoformat()
        last_interaction = max(all_timestamps).isoformat()
    else:
        first_interaction = last_interaction = None
    
    return {
        'duration_minutes': total_duration_minutes,
        'formatted': formatted,
        'first_interaction': first_interaction,
        'last_interaction': last_interaction,
        'work_blocks': block_details,
        'gaps': gaps,
        'should_split': len(work_blocks) > 1
    }


def find_cursor_sessions(target_date: datetime) -> List[Dict[str, Any]]:
    """
    Find Cursor IDE sessions for a specific date.
    """
    cursor_locations = [
        Path.home() / ".cursor" / "conversations",
        Path.home() / ".cursor" / "logs",
        Path.home() / ".config" / "Cursor" / "logs",
        Path.home() / "Library" / "Application Support" / "Cursor" / "logs",  # macOS
    ]
    
    sessions = []
    target_date_str = target_date.strftime("%Y-%m-%d")
    
    for location in cursor_locations:
        if not location.exists():
            continue
            
        # Look for JSONL files
        for jsonl_file in location.rglob("*.jsonl"):
            try:
                with open(jsonl_file, 'rb') as f:
                    # Use mmap for efficient searching
                    with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mmapped:
                        if target_date_str.encode() in mmapped:
                            # Found date, now extract interactions
                            f.seek(0)
                            interactions = []
                            
                            for line in f:
                                try:
                                    record = json.loads(line)
                                    if 'timestamp' in record:
                                        ts_str = record['timestamp']
                                        if target_date_str in ts_str:
                                            interactions.append(record)
                                except:
                                    continue
                            
                            if interactions:
                                duration_info = calculate_session_duration(interactions)
                                sessions.append({
                                    'file': str(jsonl_file),
                                    'source': 'cursor',
                                    'interaction_count': len(interactions),
                                    'duration': duration_info,
                                    'interactions': interactions[:5]  # Sample
                                })
            except Exception as e:
                continue
    
    return sessions


def find_claude_sessions_enhanced(claude_chats_dir: str, target_date: str) -> Dict[str, Any]:
    """
    Enhanced session finder with duration calculation and Cursor support.
    """
    # Parse target date
    target_datetime = parse_date(target_date)
    target_date_str = target_datetime.strftime("%Y-%m-%d")
    
    # Find Claude sessions
    claude_sessions = []
    
    # Search in the main directory and all subdirectories
    claude_path = Path(claude_chats_dir)
    if not claude_path.exists():
        # Try the projects directory instead
        claude_path = Path(os.path.expanduser("~/.claude/projects"))
    
    jsonl_files = list(claude_path.rglob("*.jsonl"))
    
    for jsonl_file in jsonl_files:
        interactions = []
        
        try:
            # Check file size first
            if jsonl_file.stat().st_size == 0:
                continue
                
            # Use regular file reading for date checking (mmap has issues with some files)
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                # Quick check if date exists in file
                found_date = False
                for line in f:
                    if target_date_str in line:
                        found_date = True
                        break
                
                if not found_date:
                    continue
                
                
                # Date found, extract interactions
                f.seek(0)
                for line in f:
                    try:
                        record = json.loads(line)
                        ts_str = record.get('timestamp', '')
                        
                        if target_date_str in ts_str:
                            interactions.append(record)
                    except:
                        continue
            
            if interactions:
                duration_info = calculate_session_duration(interactions)
                
                # Extract work summary
                work_items = []
                for interaction in interactions:
                    if interaction.get('role') == 'assistant':
                        text = interaction.get('text', '')
                        # Look for work indicators
                        if any(word in text.lower() for word in ['implemented', 'fixed', 'created', 'updated', 'built']):
                            work_items.append(text[:100] + '...')
                
                claude_sessions.append({
                    'file': str(jsonl_file),
                    'source': 'claude',
                    'interaction_count': len(interactions),
                    'duration': duration_info,
                    'work_summary': work_items[:3],
                    'work_blocks': duration_info.get('work_blocks', []),
                    'interactions': interactions
                })
                
        except Exception as e:
            print(f"Error processing {jsonl_file}: {e}")
            continue
    
    # Find Cursor sessions
    cursor_sessions = find_cursor_sessions(target_datetime)
    
    # Merge adjacent sessions (within 15 minutes)
    all_sessions = claude_sessions + cursor_sessions
    # Filter out sessions without valid timestamps
    all_sessions = [s for s in all_sessions if s['duration'].get('first_interaction')]
    all_sessions.sort(key=lambda x: x['duration']['first_interaction'])
    
    merged_sessions = []
    current_merged = None
    
    for session in all_sessions:
        if not current_merged:
            current_merged = session.copy()
            current_merged['sessions'] = [session]
        else:
            # Check if sessions are adjacent (within 15 minutes)
            current_end = datetime.fromisoformat(current_merged['duration']['last_interaction'])
            session_start = datetime.fromisoformat(session['duration']['first_interaction'])
            
            if (session_start - current_end).total_seconds() < 900:  # 15 minutes
                # Merge sessions
                current_merged['interaction_count'] += session['interaction_count']
                current_merged['duration']['last_interaction'] = session['duration']['last_interaction']
                current_merged['duration']['duration_minutes'] += session['duration']['duration_minutes']
                current_merged['sessions'].append(session)
                
                # Recalculate formatted duration
                total_minutes = current_merged['duration']['duration_minutes']
                hours = total_minutes // 60
                minutes = total_minutes % 60
                if hours > 0:
                    current_merged['duration']['formatted'] = f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
                else:
                    current_merged['duration']['formatted'] = f"{minutes}m"
            else:
                # Start new merged session
                merged_sessions.append(current_merged)
                current_merged = session.copy()
                current_merged['sessions'] = [session]
    
    if current_merged:
        merged_sessions.append(current_merged)
    
    # Create summary
    total_duration_minutes = sum(s['duration']['duration_minutes'] for s in all_sessions)
    total_hours = total_duration_minutes / 60
    
    return {
        'date': target_date,
        'claude_sessions': len(claude_sessions),
        'cursor_sessions': len(cursor_sessions),
        'total_sessions': len(all_sessions),
        'merged_sessions': len(merged_sessions),
        'total_duration': {
            'minutes': total_duration_minutes,
            'formatted': f"{total_hours:.1f}h"
        },
        'sessions': merged_sessions,
        'work_summary': {
            'claude_interactions': sum(s['interaction_count'] for s in claude_sessions),
            'cursor_interactions': sum(s['interaction_count'] for s in cursor_sessions),
            'peak_hours': extract_peak_hours(all_sessions)
        }
    }


def extract_peak_hours(sessions: List[Dict[str, Any]]) -> List[str]:
    """Extract the hours with most activity."""
    hour_counts = defaultdict(int)
    
    for session in sessions:
        try:
            start = datetime.fromisoformat(session['duration']['first_interaction'])
            end = datetime.fromisoformat(session['duration']['last_interaction'])
            
            # Count activity in each hour
            current = start.replace(minute=0, second=0, microsecond=0)
            while current <= end:
                hour_counts[current.hour] += 1
                current += timedelta(hours=1)
        except:
            continue
    
    # Get top 3 peak hours
    peak_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    return [f"{hour:02d}:00" for hour, count in peak_hours]


def generate_clockify_entries(sessions: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Generate suggested Clockify entries from sessions.
    Now handles work blocks within sessions for accurate time tracking.
    """
    entries = []
    
    for session in sessions:
        # Check if session should be split into multiple entries
        if session['duration'].get('should_split', False):
            # Create separate entries for each work block
            work_blocks = session.get('work_blocks', []) or session['duration'].get('work_blocks', [])
            
            for idx, block in enumerate(work_blocks):
                # Extract work description for this block
                block_start = datetime.fromisoformat(block['start'])
                block_end = datetime.fromisoformat(block['end'])
                
                # Get interactions within this time block
                block_interactions = []
                all_interactions = session.get('interactions', [])
                
                for interaction in all_interactions:
                    try:
                        int_time = datetime.fromisoformat(
                            interaction.get('timestamp', '').replace('Z', '+00:00'))
                        if block_start <= int_time <= block_end:
                            block_interactions.append(interaction)
                    except:
                        continue
                
                # Extract work description
                work_items = []
                for interaction in block_interactions:
                    if interaction.get('role') == 'assistant':
                        text = interaction.get('text', '').lower()
                        if 'implemented' in text:
                            match = re.search(r'implemented\s+(.+?)(?:\.|,|$)', text)
                            if match:
                                work_items.append(f"Implemented {match.group(1)}")
                        elif 'fixed' in text:
                            match = re.search(r'fixed\s+(.+?)(?:\.|,|$)', text)
                            if match:
                                work_items.append(f"Fixed {match.group(1)}")
                
                base_desc = ' | '.join(work_items[:2]) if work_items else "Development work"
                
                # Add part number if multiple blocks
                if len(work_blocks) > 1:
                    description = f"{base_desc} - Part {idx + 1}"
                else:
                    description = base_desc
                
                # Format duration for this block
                block_minutes = block['duration_minutes']
                hours = block_minutes // 60
                minutes = block_minutes % 60
                if hours > 0:
                    duration_fmt = f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
                else:
                    duration_fmt = f"{minutes}m"
                
                entries.append({
                    'description': description,
                    'duration': duration_fmt,
                    'start_time': block['start'],
                    'project': "AI_Augmentation"  # Default
                })
        else:
            # Single continuous session - use existing logic
            all_interactions = session.get('interactions', [])
            
            # Extract work description
            work_items = []
            for interaction in all_interactions:
                if interaction.get('role') == 'assistant':
                    text = interaction.get('text', '').lower()
                    if 'implemented' in text:
                        match = re.search(r'implemented\s+(.+?)(?:\.|,|$)', text)
                        if match:
                            work_items.append(f"Implemented {match.group(1)}")
                    elif 'fixed' in text:
                        match = re.search(r'fixed\s+(.+?)(?:\.|,|$)', text)
                        if match:
                            work_items.append(f"Fixed {match.group(1)}")
            
            description = ' | '.join(work_items[:2]) if work_items else "Development work"
            
            entries.append({
                'description': description,
                'duration': session['duration']['formatted'],
                'start_time': session['duration']['first_interaction'],
                'project': "AI_Augmentation"
            })
    
    return entries


# Example usage
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python find_claude_sessions_enhanced.py <date>")
        print("Example: python find_claude_sessions_enhanced.py '27 jul'")
        sys.exit(1)
    
    claude_dir = os.path.expanduser("~/.claude/chats")
    result = find_claude_sessions_enhanced(claude_dir, sys.argv[1])
    
    print(f"\nSessions for {result['date']}:")
    print(f"- Claude sessions: {result['claude_sessions']}")
    print(f"- Cursor sessions: {result['cursor_sessions']}")
    print(f"- Total duration: {result['total_duration']['formatted']}")
    print(f"- Merged into: {result['merged_sessions']} work blocks")
    
    if result['work_summary']['peak_hours']:
        print(f"- Peak hours: {', '.join(result['work_summary']['peak_hours'])}")
    
    # Generate Clockify entries
    entries = generate_clockify_entries(result['sessions'])
    print(f"\nSuggested Clockify entries:")
    for entry in entries:
        print(f"- {entry['description']} ({entry['duration']})")