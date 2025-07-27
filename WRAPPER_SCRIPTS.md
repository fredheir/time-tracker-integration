# Time Tracker Wrapper Scripts

These bash wrapper scripts allow you to run the time tracker tools from anywhere on your system.

## Available Wrappers

### time-tracker
Main time tracking tool that analyzes coding sessions across Claude, Cursor, and Git
```bash
# Usage examples:
time-tracker --days 7
time-tracker --start "2025-07-20" --end "2025-07-27"
time-tracker --output csv
```

### claude-sessions
Find Claude sessions with gap detection and duration calculation
```bash
# Usage examples:
claude-sessions "2025-07-27"
claude-sessions "yesterday"
claude-sessions "27 jul"
```

### claude-insights
Extract work insights from Claude JSONL sessions
```bash
# Usage examples:
claude-insights /path/to/session.jsonl "2025-07-27"
claude-insights ~/.claude/projects/*/file.jsonl "yesterday"
```

### claude-insights-enhanced
Extract enhanced work descriptions with deliverable focus
```bash
# Usage examples:
claude-insights-enhanced
# (Follow the module's import instructions)
```

## Installation

To make these commands available system-wide:

```bash
# Create symlinks in /usr/local/bin
sudo ln -s $(pwd)/time-tracker /usr/local/bin/
sudo ln -s $(pwd)/claude-sessions /usr/local/bin/
sudo ln -s $(pwd)/claude-insights /usr/local/bin/
sudo ln -s $(pwd)/claude-insights-enhanced /usr/local/bin/
```

Or add this directory to your PATH:
```bash
echo 'export PATH="$PATH:/home/rolf/fuzzy-ops/tools/time-tracker-integration"' >> ~/.bashrc
source ~/.bashrc
```

## Benefits

- Run from any directory without `cd` commands
- No need to remember the full `uv run python` syntax
- Consistent with the `clockify-track` wrapper pattern
- Used by `/daily_work_analysis` slash command

## Note

These wrappers ensure:
- Proper directory context
- Dependencies installed via `uv`
- All arguments passed through correctly