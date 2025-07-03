"""
Google Calendar integration for time tracking heatmap.
Fetches meetings and filters them for display in the heatmap visualization.
"""

import datetime
import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import yaml
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

class CalendarIntegration:
    """Handles Google Calendar integration for fetching and filtering meetings."""
    
    def __init__(self, owner_email: str = None, config_path: str = None):
        """
        Initialize calendar integration.
        
        Args:
            owner_email: Email of the calendar owner (used for filtering)
            config_path: Path to config.yaml file
        """
        self.config = self._load_config(config_path)
        self.owner_email = owner_email or self.config.get('calendar', {}).get('owner_email') or self._get_owner_email()
        self.service = None
        self._credentials = None
        self._config_dir = Path.home() / '.config' / 'cli-tools'
        self._ensure_config_dir()
    
    def _load_config(self, config_path: str = None) -> Dict:
        """Load configuration from config.yaml."""
        if config_path is None:
            config_path = Path('./config/config.yaml')
        else:
            config_path = Path(config_path)
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Warning: Could not load config from {config_path}: {e}")
        
        return {}
    
    def _ensure_config_dir(self):
        """Ensure configuration directory exists."""
        self._config_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_owner_email(self) -> str:
        """Get owner email from config or environment."""
        # Try to load from config
        config_file = self._config_dir / 'calendar_config.json'
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    return config.get('owner_email', 'rolf')
            except:
                pass
        
        # Default to 'rolf' if not configured
        return os.environ.get('CALENDAR_OWNER_EMAIL', 'rolf')
    
    def _load_credentials(self) -> Optional[Credentials]:
        """Load credentials from token file."""
        token_file = self._config_dir / 'calendar_token.json'
        if not token_file.exists():
            return None
        
        try:
            with open(token_file, 'r') as f:
                token_data = json.load(f)
            return Credentials.from_authorized_user_info(token_data, SCOPES)
        except Exception as e:
            print(f"Error loading credentials: {e}")
            return None
    
    def _save_credentials(self, creds: Credentials):
        """Save credentials to token file."""
        token_file = self._config_dir / 'calendar_token.json'
        with open(token_file, 'w') as f:
            f.write(creds.to_json())
    
    def authenticate(self) -> bool:
        """
        Authenticate with Google Calendar API.
        
        Returns:
            bool: True if authentication successful
        """
        creds = self._load_credentials()
        
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # Check for OAuth client config from fuzzy-ops setup
                config_file = self._config_dir / 'gmail_config.json'
                if not config_file.exists():
                    print(f"Error: OAuth config not found at {config_file}")
                    print("Please copy your OAuth client configuration from fuzzy-ops")
                    return False
                
                try:
                    with open(config_file, 'r') as f:
                        client_config = json.load(f)
                    
                    flow = InstalledAppFlow.from_client_config(
                        client_config, SCOPES)
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    print(f"Error during authentication: {e}")
                    return False
            
            # Save the credentials for the next run
            self._save_credentials(creds)
        
        self._credentials = creds
        self.service = build('calendar', 'v3', credentials=creds)
        return True
    
    def _is_real_meeting(self, event: Dict) -> bool:
        """
        Determine if an event is a real meeting (not a time blocker).
        
        Args:
            event: Calendar event dict
            
        Returns:
            bool: True if this is a real meeting with external attendees
        """
        filtering_config = self.config.get('calendar', {}).get('filtering', {})
        
        # Check if calendar integration is enabled
        if not self.config.get('calendar', {}).get('enabled', True):
            return False
        
        # Check if it's a declined event
        if filtering_config.get('exclude_declined', True) and event.get('status') == 'cancelled':
            return False
        
        # Get attendees
        attendees = event.get('attendees', [])
        if not attendees:
            return False
        
        # Check minimum attendee count
        min_attendees = filtering_config.get('minimum_attendees', 2)
        if len(attendees) < min_attendees:
            return False
        
        # Check if user has declined
        if filtering_config.get('exclude_declined', True):
            for attendee in attendees:
                if attendee.get('self') and attendee.get('responseStatus') == 'declined':
                    return False
        
        # Check for external attendees if required
        if filtering_config.get('require_external_attendees', True):
            external_attendees = []
            for attendee in attendees:
                email = attendee.get('email', '').lower()
                # Skip the owner and resource rooms
                if (email and 
                    not attendee.get('self') and 
                    not attendee.get('resource') and
                    self.owner_email.lower() not in email):
                    external_attendees.append(email)
            
            if not external_attendees:
                return False
        
        # Check for excluded keywords in title
        summary = event.get('summary', '').lower()
        exclude_keywords = filtering_config.get('exclude_keywords', [
            'block', 'busy', 'focus time', 'work time', 
            'deep work', 'no meetings', 'hold', 'tentative'
        ])
        
        for keyword in exclude_keywords:
            if keyword.lower() in summary:
                return False
        
        # Check if marked as free time
        if filtering_config.get('exclude_free_time', True) and event.get('transparency') == 'transparent':
            return False
        
        return True
    
    def get_meetings(self, start_date: datetime.datetime, 
                    end_date: datetime.datetime) -> List[Dict]:
        """
        Fetch meetings from Google Calendar.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            List of meeting dictionaries
        """
        if not self.service:
            if not self.authenticate():
                return []
        
        try:
            # Call the Calendar API
            # Ensure timezone-naive datetime for API
            if start_date.tzinfo is not None:
                start_date = start_date.replace(tzinfo=None)
            if end_date.tzinfo is not None:
                end_date = end_date.replace(tzinfo=None)
                
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=start_date.isoformat() + 'Z',
                timeMax=end_date.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Filter for real meetings only
            meetings = []
            for event in events:
                if self._is_real_meeting(event):
                    meeting = self._format_meeting(event)
                    if meeting:
                        meetings.append(meeting)
            
            return meetings
            
        except HttpError as error:
            print(f'An error occurred: {error}')
            return []
    
    def _format_meeting(self, event: Dict) -> Optional[Dict]:
        """
        Format a calendar event into a meeting dict for the heatmap.
        
        Args:
            event: Google Calendar event
            
        Returns:
            Formatted meeting dict or None
        """
        # Skip all-day events
        start_info = event.get('start', {})
        if 'date' in start_info and 'dateTime' not in start_info:
            return None
        
        try:
            # Parse start and end times
            start_str = start_info.get('dateTime')
            end_str = event.get('end', {}).get('dateTime')
            
            if not start_str or not end_str:
                return None
            
            # Parse ISO format timestamps
            start = datetime.datetime.fromisoformat(start_str.replace('Z', '+00:00'))
            end = datetime.datetime.fromisoformat(end_str.replace('Z', '+00:00'))
            
            # Get attendee list
            attendees = []
            for attendee in event.get('attendees', []):
                if not attendee.get('resource') and attendee.get('email'):
                    attendees.append({
                        'email': attendee['email'],
                        'displayName': attendee.get('displayName', attendee['email']),
                        'responseStatus': attendee.get('responseStatus', 'unknown')
                    })
            
            return {
                'id': event['id'],
                'summary': event.get('summary', 'Untitled Meeting'),
                'start': start.isoformat(),
                'end': end.isoformat(),
                'duration_minutes': (end - start).total_seconds() / 60,
                'location': event.get('location', ''),
                'description': event.get('description', ''),
                'attendees': attendees,
                'attendee_count': len(attendees),
                'type': 'meeting'
            }
            
        except Exception as e:
            print(f"Error formatting meeting: {e}")
            return None
    
    def get_meetings_for_range(self, start_date: datetime.date, 
                              days: int = 30) -> List[Dict]:
        """
        Get meetings for a date range.
        
        Args:
            start_date: Start date
            days: Number of days to fetch
            
        Returns:
            List of meetings
        """
        start_datetime = datetime.datetime.combine(start_date, datetime.time.min)
        end_datetime = start_datetime + datetime.timedelta(days=days)
        
        return self.get_meetings(start_datetime, end_datetime)