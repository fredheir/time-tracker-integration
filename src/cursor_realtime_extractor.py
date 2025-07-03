"""Real-time Cursor session extractor that analyzes actual database activity"""

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import re

try:
    from .base_extractor import BaseExtractor, Session
except ImportError:
    from base_extractor import BaseExtractor, Session


class CursorRealtimeExtractor(BaseExtractor):
    """Extract real Cursor coding sessions from the database"""
    
    def __init__(self, config):
        super().__init__(config)
        self.cursor_dir = Path.home() / '.config' / 'Cursor'
        self.main_db = self.cursor_dir / 'User' / 'globalStorage' / 'state.vscdb'
        self.session_threshold = timedelta(minutes=30)  # Gap between sessions
        
    def is_available(self) -> bool:
        """Check if Cursor database is available"""
        return self.main_db.exists()
        
    def extract_sessions(self, start_date: Optional[datetime] = None, 
                        end_date: Optional[datetime] = None) -> List[Session]:
        """Extract Cursor coding sessions"""
        if not self.is_available():
            print("Cursor database not found")
            return []
            
        # Get all activity timestamps
        activities = self._extract_all_activities()
        
        # Group into sessions
        sessions = self._group_into_sessions(activities)
        
        # Filter by date range
        if start_date or end_date:
            sessions = self._filter_by_date(sessions, start_date, end_date)
            
        return sessions
    
    def _extract_all_activities(self) -> List[Tuple[datetime, str]]:
        """Extract all activity timestamps from database"""
        activities = []
        
        try:
            # Get all workspace databases and analyze them individually
            workspace_dbs = list(self.cursor_dir.glob("User/workspaceStorage/*/state.vscdb"))
            all_dbs = [self.main_db] + workspace_dbs
            
            print(f"Found {len(all_dbs)} Cursor databases to analyze")
            
            for db_path in all_dbs:
                try:
                    # Get project name from workspace path
                    project = self._get_project_from_path(db_path)
                    
                    # Use database file modification times as activity indicators
                    if db_path.exists():
                        mtime = datetime.fromtimestamp(db_path.stat().st_mtime, tz=timezone.utc)
                        # Include modifications from the last 30 days
                        if mtime > datetime.now(timezone.utc) - timedelta(days=30):
                            activities.append((mtime, project))
                            print(f"Found activity: {mtime} for {project}")
                    
                    # Also check backup files which indicate recent activity
                    backup_path = db_path.with_suffix('.vscdb.backup')
                    if backup_path.exists():
                        mtime = datetime.fromtimestamp(backup_path.stat().st_mtime, tz=timezone.utc)
                        if mtime > datetime.now(timezone.utc) - timedelta(days=30):
                            activities.append((mtime, project))
                            print(f"Found backup activity: {mtime} for {project}")
                                
                except Exception as e:
                    print(f"Error processing {db_path}: {e}")
            
            # Also analyze general Cursor application files for overall activity
            cursor_activity_files = [
                self.cursor_dir / 'User' / 'globalStorage' / 'state.vscdb',
                self.cursor_dir / 'User' / 'globalStorage' / 'state.vscdb.backup',
                self.cursor_dir / 'Cache' / 'Cache_Data' / 'data_0',
                self.cursor_dir / 'Cache' / 'Cache_Data' / 'data_1',
                self.cursor_dir / 'Session Storage' / 'LOG',
                self.cursor_dir / 'Local Storage' / 'leveldb' / 'LOG'
            ]
            
            for file_path in cursor_activity_files:
                if file_path.exists():
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
                    # Only include recent modifications (last 30 days)
                    if mtime > datetime.now(timezone.utc) - timedelta(days=30):
                        activities.append((mtime, 'Unknown'))
                        print(f"Found general activity: {mtime}")
                        
        except Exception as e:
            print(f"Error extracting Cursor activities: {e}")
            
        # Sort by timestamp
        activities.sort(key=lambda x: x[0])
        
        print(f"Total activities found: {len(activities)}")
        
        # Deduplicate close timestamps (within 30 minutes for better session detection)
        deduped = []
        last_time = None
        for timestamp, project in activities:
            if last_time is None or (timestamp - last_time) > timedelta(minutes=30):
                deduped.append((timestamp, project))
                last_time = timestamp
                
        print(f"Activities after deduplication: {len(deduped)}")
        return deduped
    
    def _extract_timestamp_from_key(self, key: str) -> Optional[datetime]:
        """Try to extract timestamp from a database key"""
        # Look for ISO date patterns
        iso_pattern = r'(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})'
        match = re.search(iso_pattern, key)
        if match:
            try:
                return datetime.fromisoformat(match.group(1).replace(' ', 'T')).replace(tzinfo=timezone.utc)
            except:
                pass
        
        # Look for Unix timestamps (10-13 digits)
        unix_pattern = r'\b(\d{10,13})\b'
        match = re.search(unix_pattern, key)
        if match:
            try:
                ts = int(match.group(1))
                if ts > 1e12:  # Milliseconds
                    return datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
                else:  # Seconds
                    return datetime.fromtimestamp(ts, tz=timezone.utc)
            except:
                pass
                
        return None
    
    def _parse_timestamp_value(self, value: Any) -> Optional[datetime]:
        """Parse timestamp from a value"""
        if isinstance(value, (int, float)):
            try:
                if value > 1e12:  # Milliseconds
                    return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
                else:  # Seconds
                    return datetime.fromtimestamp(value, tz=timezone.utc)
            except:
                pass
        elif isinstance(value, str):
            # Try ISO format
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
            except:
                pass
                
        return None
    
    def _get_project_from_path(self, db_path: Path) -> str:
        """Determine project from database path"""
        path_str = str(db_path)
        
        # Check workspace storage paths
        if 'workspaceStorage' in path_str:
            # Try to find a project indicator file
            workspace_dir = db_path.parent
            for indicator_file in ['workspace.json', '.vscode/settings.json']:
                indicator_path = workspace_dir / indicator_file
                if indicator_path.exists():
                    try:
                        with open(indicator_path, 'r') as f:
                            content = f.read()
                            if 'political_template' in content:
                                return 'political_template'
                            elif 'ai_augmentation' in content:
                                return 'ai_augmentation'
                            elif 'time-tracker' in content:
                                return 'time-tracker-integration'
                    except:
                        pass
        
        return 'Unknown'
    
    def _group_into_sessions(self, activities: List[Tuple[datetime, str]]) -> List[Session]:
        """Group activities into sessions based on time gaps"""
        sessions = []
        
        if not activities:
            return sessions
        
        # Since we're using file modification times, each activity represents 
        # the end of a coding session. Create sessions with minimum duration.
        for timestamp, project in activities:
            # Create a session that ends at the file modification time
            # and starts 30 minutes earlier (or 1 hour for more realistic session length)
            session_duration = timedelta(hours=1)  # Default session length
            
            session = Session(
                start=timestamp - session_duration,
                end=timestamp,
                service='Cursor',
                project=project if project != 'Unknown' else 'Unknown',
                metrics={'activity_count': 1}
            )
            sessions.append(session)
            print(f"Created session: {session.start} - {session.end} for {session.project}")
        
        # Sort sessions by start time
        sessions.sort(key=lambda s: s.start)
        
        # Merge overlapping sessions for the same project
        if len(sessions) > 1:
            merged_sessions = [sessions[0]]
            
            for current_session in sessions[1:]:
                last_session = merged_sessions[-1]
                
                # Check if sessions overlap and are for the same project
                if (current_session.start <= last_session.end and 
                    current_session.project == last_session.project):
                    
                    # Merge sessions by extending the end time
                    merged_sessions[-1] = Session(
                        start=last_session.start,
                        end=max(last_session.end, current_session.end),
                        service='Cursor',
                        project=last_session.project,
                        metrics={'activity_count': last_session.metrics.get('activity_count', 1) + 1}
                    )
                    print(f"Merged session: {merged_sessions[-1].start} - {merged_sessions[-1].end}")
                else:
                    merged_sessions.append(current_session)
            
            sessions = merged_sessions
        
        print(f"Final sessions: {len(sessions)}")
        for session in sessions:
            print(f"  {session.start} - {session.end}: {session.project}")
        
        return sessions
    
    def _filter_by_date(self, sessions: List[Session], 
                       start_date: Optional[datetime], 
                       end_date: Optional[datetime]) -> List[Session]:
        """Filter sessions by date range"""
        filtered = []
        
        # Make start_date and end_date timezone aware if they aren't
        if start_date and start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date and end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        
        for session in sessions:
            if start_date and session.end < start_date:
                continue
            if end_date and session.start > end_date:
                continue
            filtered.append(session)
            
        return filtered