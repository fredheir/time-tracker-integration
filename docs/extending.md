# Extending Time Tracker Integration

## Adding a New Service

Here's a complete example of adding VSCode support:

### 1. Create the Extractor

Create `src/vscode_extractor.py`:

```python
from pathlib import Path
from datetime import datetime
import json
from typing import List, Optional

from base_extractor import BaseExtractor, Session


class VscodeExtractor(BaseExtractor):
    """Extract coding sessions from VSCode"""
    
    def __init__(self, config):
        super().__init__(config)
        # VSCode stores data similar to Cursor
        self.db_path = Path("~/.config/Code/User/globalStorage/state.vscdb").expanduser()
        
    def is_available(self) -> bool:
        """Check if VSCode data exists"""
        return self.db_path.exists()
        
    def extract_sessions(self, start_date: Optional[datetime] = None, 
                        end_date: Optional[datetime] = None) -> List[Session]:
        """Extract VSCode coding sessions"""
        sessions = []
        
        # Implementation would parse VSCode's SQLite database
        # This is a simplified example
        
        # For now, return empty list
        return sessions
```

### 2. Update Configuration

Add to `config/config.yaml`:

```yaml
services:
  vscode:
    enabled: true
    data_path: ~/.config/Code/User/globalStorage/state.vscdb
```

### 3. Update TimeTracker

In `src/time_tracker.py`, add the import and initialization:

```python
from vscode_extractor import VscodeExtractor

def _initialize_extractors(self):
    """Initialize enabled service extractors"""
    if self.config['services']['claude']['enabled']:
        self.extractors.append(ClaudeExtractor(self.config))
        
    if self.config['services']['cursor']['enabled']:
        self.extractors.append(CursorExtractor(self.config))
        
    # Add VSCode support
    if self.config['services'].get('vscode', {}).get('enabled', False):
        self.extractors.append(VscodeExtractor(self.config))
```

## Adding a New Repository Type

To add support for a different version control system (e.g., Mercurial):

### 1. Update GitAnalyzer

Add a new method in `src/git_analyzer.py`:

```python
def _fetch_hg_commits(self, repo_name: str, repo_path: str,
                     start_date: Optional[datetime],
                     end_date: Optional[datetime]) -> List[Dict[str, Any]]:
    """Fetch commits from Mercurial repository"""
    commits = []
    
    try:
        # Build hg log command
        cmd = f'cd "{repo_path}" && hg log --template "{{node|short}}|{{date|isodate}}|{{author}}|{{desc|firstline}}\\n"'
        if start_date:
            cmd += f' --date ">{start_date.isoformat()}"'
            
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        # Parse results similar to git
        # ...
        
    except Exception as e:
        print(f"Error fetching Mercurial commits for {repo_name}: {e}")
        
    return commits
```

### 2. Update Configuration

```yaml
repositories:
  github:
    - user/repo
  local:
    my_git_project: /path/to/git/repo
  mercurial:
    my_hg_project: /path/to/hg/repo
```

## Custom Analysis Plugins

You can also create analysis plugins that process the extracted data:

```python
class ProductivityAnalyzer:
    """Analyze productivity patterns"""
    
    def analyze(self, sessions_df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze productivity metrics"""
        return {
            'most_productive_hour': self._find_productive_hour(sessions_df),
            'average_session_length': self._calculate_avg_session(sessions_df),
            'focus_score': self._calculate_focus_score(sessions_df)
        }
```

## Testing Your Extensions

Create unit tests for your extractors:

```python
import unittest
from datetime import datetime
from my_extractor import MyExtractor

class TestMyExtractor(unittest.TestCase):
    def setUp(self):
        self.config = {
            'services': {
                'myservice': {
                    'enabled': True,
                    'data_path': '/test/path'
                }
            }
        }
        self.extractor = MyExtractor(self.config)
        
    def test_extract_sessions(self):
        sessions = self.extractor.extract_sessions(
            start_date=datetime(2025, 6, 1),
            end_date=datetime(2025, 6, 30)
        )
        self.assertIsInstance(sessions, list)
```