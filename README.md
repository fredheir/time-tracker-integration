# Time Tracker Integration

A modular, extensible system for tracking coding time across multiple development tools and aligning it with Git commit history.

## Features

- **Multi-Service Support**: Currently supports Claude Code and Cursor, easily extensible for other tools
- **Git Integration**: Automatically matches coding sessions with repository commits
- **Flexible Configuration**: YAML-based configuration for easy customization
- **Multiple Output Formats**: CSV, JSON, and console reports
- **Smart Session Merging**: Combines nearby sessions for accurate time tracking

## Installation

1. Clone the repository:
```bash
git clone https://github.com/fredheir/time-tracker-integration.git
cd time-tracker-integration
```

2. Install dependencies:
```bash
# Core functionality only
uv pip install pandas pyyaml

# Or install all features
uv pip install -r requirements.txt
```

3. Ensure you have the GitHub CLI installed (for GitHub repository tracking):
```bash
gh --version  # Should show gh version
```

## Quick Start

### Basic Usage
```bash
# Last 7 days (recommended for first run)
uv run src/time_tracker.py --days 7

# Specific date range
uv run src/time_tracker.py --start 2025-06-19 --end 2025-06-23

# All available data
uv run src/time_tracker.py
```

### Generate Dashboard
```bash
# Create interactive HTML dashboard
./dashboard.sh
# Opens: data/dashboard.html
```

### First Time Setup Notes

**Claude Data**: If you see "Claude data not found", ensure Claude Code has been used and data exists in `~/.claude/projects/`

**Cursor Data**: For Cursor integration, you need either:
- The Cursor database at `~/.config/Cursor/User/globalStorage/state.vscdb`
- A pre-extracted summary file named `cursor_work_summary.json` in the data folder

## Configuration

Edit `config/config.yaml` to customize:

- **Repositories**: Add/remove GitHub and local repositories to track
- **Services**: Enable/disable tracking services
- **Analysis Settings**: Adjust time windows and merging thresholds
- **Output**: Configure report formats and output directory

### Example configuration:
```yaml
repositories:
  github:
    - your-username/your-repo
  local:
    my_project: /path/to/my_project

services:
  claude:
    enabled: true
  cursor:
    enabled: true
```

## Advanced Usage

### Custom Configuration
```bash
uv run src/time_tracker.py --config /path/to/config.yaml
```

### Output Options
All reports are saved to the `data/` directory:
- CSV files for data analysis
- JSON files for programmatic access
- Console output for quick viewing

## Visualization

### Quick Dashboard (Recommended)
Generate an interactive HTML dashboard:
```bash
./dashboard.sh
```
This creates a self-contained `data/dashboard.html` file with charts and statistics.

### Web Dashboard
For real-time monitoring with advanced features:
```bash
uv run src/dashboard.py
# Open http://localhost:5000
```

📊 **See [docs/visualization.md](docs/visualization.md) for complete visualization guide and options.**

## Adding New Services

To add support for a new development tool:

1. Create a new extractor class in `src/` that inherits from `BaseExtractor`
2. Implement the required methods:
   - `is_available()`: Check if service data exists
   - `extract_sessions()`: Extract coding sessions
3. Add the service to `config.yaml`
4. Import and initialize in `TimeTracker._initialize_extractors()`

Example:
```python
from base_extractor import BaseExtractor, Session

class MyToolExtractor(BaseExtractor):
    def is_available(self):
        # Check if data exists
        pass
        
    def extract_sessions(self, start_date=None, end_date=None):
        # Extract and return Session objects
        pass
```

## Data Sources

### Claude Code
- Location: `~/.claude/projects/**/*.jsonl`
- Format: JSONL files with interaction timestamps

### Cursor
- Location: `~/.config/Cursor/User/globalStorage/state.vscdb`
- Format: SQLite database
- Alternative: Pre-extracted JSON summaries

### Git Repositories
- GitHub: Via `gh` CLI API
- Local: Direct `git log` commands

## Output

Reports include:
- **Repository Summary**: Time spent per repository with commit counts
- **Service Summary**: Time spent using each tool
- **Daily Breakdown**: Detailed timeline of coding sessions

Output files are saved to the `data/` directory with timestamps.

## Architecture

```
time-tracker-integration/
├── config/
│   └── config.yaml          # Main configuration
├── src/
│   ├── base_extractor.py    # Base class for service extractors
│   ├── claude_extractor.py  # Claude Code extractor
│   ├── cursor_extractor.py  # Cursor extractor
│   ├── git_analyzer.py      # Git commit analysis
│   ├── time_tracker.py      # Main integration script
│   ├── dashboard.py         # Web dashboard
│   └── calendar_integration.py  # Calendar features
├── docs/                    # Documentation
├── templates/               # HTML templates
└── data/                    # Output directory (auto-created)
```

## Troubleshooting

### No Claude data found
- Ensure Claude Code has been used and data exists in `~/.claude/projects/`
- Check the path in config.yaml

### No Cursor data found
- Ensure Cursor is installed and has been used
- For initial setup, you may need to run the comprehensive extractor first

### GitHub API errors
- Ensure `gh` CLI is authenticated: `gh auth status`
- Check repository permissions

## License

MIT