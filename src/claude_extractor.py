"""Claude Code time tracking extractor"""

import json
import glob
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
import pandas as pd

try:
    from .base_extractor import BaseExtractor, Session
except ImportError:
    from base_extractor import BaseExtractor, Session


class ClaudeExtractor(BaseExtractor):
    """Extract coding sessions from Claude Code JSONL files"""
    
    def __init__(self, config):
        super().__init__(config)
        self.data_path = Path(config['services']['claude']['data_path']).expanduser()
        self.block_size = config['analysis']['block_size_minutes']
        
    def is_available(self) -> bool:
        """Check if Claude data directory exists"""
        return self.data_path.exists()
        
    def extract_sessions(self, start_date: Optional[datetime] = None, 
                        end_date: Optional[datetime] = None) -> List[Session]:
        """Extract Claude coding sessions"""
        if not self.is_available():
            print(f"Claude data not found at {self.data_path}")
            return []
            
        # Get all JSONL files
        jsonl_files = list(self.data_path.rglob('*.jsonl'))
        print(f"Found {len(jsonl_files)} Claude JSONL files")
        
        # Extract all entries
        all_entries = []
        for file_path in jsonl_files:
            entries = self._parse_jsonl_file(file_path)
            all_entries.extend(entries)
            
        if not all_entries:
            return []
            
        # Convert to DataFrame for easier processing
        df = pd.DataFrame(all_entries)
        
        # Filter by date range
        if start_date:
            # Convert to UTC for comparison
            if start_date.tzinfo is None:
                start_date = pd.Timestamp(start_date).tz_localize('UTC')
            df = df[df['timestamp'] >= start_date]
        if end_date:
            # Convert to UTC for comparison
            if end_date.tzinfo is None:
                end_date = pd.Timestamp(end_date).tz_localize('UTC')
            df = df[df['timestamp'] <= end_date]
            
        # Create activity blocks
        blocks = self._create_activity_blocks(df)
        
        # Convert blocks to sessions
        sessions = []
        for _, block in blocks.iterrows():
            session = Session(
                start=block['block_start'],
                end=block['block_start'] + timedelta(minutes=self.block_size),
                service='Claude',
                project=block.get('project', 'Unknown'),
                metrics={
                    'interactions': block['interactions'],
                    'input_tokens': block['input_tokens'],
                    'output_tokens': block['output_tokens']
                }
            )
            sessions.append(session)
            
        # Merge consecutive sessions
        threshold = self.config['analysis']['merge_threshold_minutes']
        return self.merge_consecutive_sessions(sessions, threshold)
        
    def _parse_jsonl_file(self, file_path):
        """Parse a single JSONL file"""
        entries = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if 'timestamp' in data:
                            timestamp = datetime.fromisoformat(
                                data['timestamp'].replace('Z', '+00:00')
                            )
                            # Parse project name from encoded path
                            project_name = file_path.parent.name
                            # Convert encoded path back to readable format
                            if project_name.startswith('-home-'):
                                # Extract the last meaningful part of the path
                                parts = project_name.split('-')
                                if 'ai_augmentation' in project_name:
                                    project_name = 'ai_augmentation'
                                elif 'political_template' in project_name or 'political-template' in project_name:
                                    project_name = 'political_template'
                                else:
                                    # Take the last non-empty part
                                    project_name = [p for p in parts if p][-1] if parts else project_name
                            
                            entries.append({
                                'timestamp': timestamp,
                                'session': file_path.stem,
                                'project': project_name,
                                'input_tokens': data.get('input_tokens', 0),
                                'output_tokens': data.get('output_tokens', 0),
                                'file_path': str(file_path)
                            })
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            
        return entries
        
    def _create_activity_blocks(self, df):
        """Convert timestamps to activity blocks"""
        if df.empty:
            return pd.DataFrame()
            
        # Round timestamps to block boundaries
        df['block_start'] = df['timestamp'].dt.floor(f'{self.block_size}min')
        
        # Group by block
        blocks = df.groupby(['block_start', 'project']).agg({
            'session': 'nunique',
            'input_tokens': 'sum',
            'output_tokens': 'sum',
            'timestamp': 'count'
        }).rename(columns={
            'session': 'active_sessions',
            'timestamp': 'interactions'
        }).reset_index()
        
        blocks['total_tokens'] = blocks['input_tokens'] + blocks['output_tokens']
        
        return blocks