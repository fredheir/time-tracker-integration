"""Base class for time tracking service extractors"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd


class Session:
    """Represents a coding session"""
    def __init__(self, start: datetime, end: datetime, service: str, 
                 project: Optional[str] = None, metrics: Optional[Dict[str, Any]] = None):
        self.start = start
        self.end = end
        self.service = service
        self.project = project
        self.metrics = metrics or {}
        
    @property
    def duration(self):
        return self.end - self.start
        
    def to_dict(self):
        return {
            'start': self.start,
            'end': self.end,
            'service': self.service,
            'project': self.project,
            'duration_hours': self.duration.total_seconds() / 3600,
            **self.metrics
        }


class BaseExtractor(ABC):
    """Base class for extracting coding sessions from different services"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.service_name = self.__class__.__name__.replace('Extractor', '').lower()
        
    @abstractmethod
    def extract_sessions(self, start_date: Optional[datetime] = None, 
                        end_date: Optional[datetime] = None) -> List[Session]:
        """Extract coding sessions from the service"""
        pass
        
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the service data is available"""
        pass
        
    def filter_sessions(self, sessions: List[Session], 
                       start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None) -> List[Session]:
        """Filter sessions by date range"""
        if start_date:
            sessions = [s for s in sessions if s.start >= start_date]
        if end_date:
            sessions = [s for s in sessions if s.start <= end_date]
        return sessions
        
    def merge_consecutive_sessions(self, sessions: List[Session], 
                                  threshold_minutes: int = 10) -> List[Session]:
        """Merge sessions that are close together"""
        if not sessions:
            return []
            
        sessions = sorted(sessions, key=lambda s: s.start)
        merged = []
        current = sessions[0]
        
        for session in sessions[1:]:
            time_gap = (session.start - current.end).total_seconds() / 60
            
            if time_gap <= threshold_minutes and session.project == current.project:
                # Merge sessions
                current.end = session.end
                # Merge metrics
                for key, value in session.metrics.items():
                    if isinstance(value, (int, float)):
                        current.metrics[key] = current.metrics.get(key, 0) + value
            else:
                merged.append(current)
                current = session
                
        merged.append(current)
        return merged