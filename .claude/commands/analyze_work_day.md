# Analyze Work Day

Perform comprehensive analysis of work done on a specific date using multiple data sources with automatic gap detection and accurate duration calculation.

## Usage
`/analyze_work_day [date]`

**Arguments**: 
- `date`: Target date in various formats:
  - ISO format: "2025-07-26"
  - Natural language: "yesterday", "today", "July 26", "jul 24"
  - Default: today if not specified

**Examples**:
- `/analyze_work_day 2025-07-26`
- `/analyze_work_day yesterday`
- `/analyze_work_day "July 26"`

## What This Command Does

1. **Generates time tracking overview** using dashboard and time tracker
2. **Runs enhanced Claude analysis** with automatic gap detection and work block splitting
3. **Calculates accurate durations** excluding breaks > 15 minutes
4. **Correlates with git commits** across all repositories  
5. **Identifies peak working hours** and productivity patterns
6. **Generates pre-formatted Clockify entries** with proper descriptions and part numbers

## Implementation Workflow

### Phase 1: Initial Discovery
```bash
# Get high-level overview
uv run /home/rolf/fuzzy-ops/tools/time-tracker-integration/src/time_tracker.py --start "$DATE" --end "$DATE"
```

Extract total hours and project distribution from the output.

### Phase 2: Enhanced Claude Session Analysis (NEW)
```bash
# Run the enhanced analysis that automatically handles ALL files and gap detection
uv run find_claude_sessions_enhanced.py "$DATE" > claude_work_analysis.txt

# Display the comprehensive analysis
cat claude_work_analysis.txt
```

**What the enhanced analysis provides**:
- **Total work duration** with breaks automatically excluded
- **Work blocks** split by gaps > 15 minutes  
- **Peak working hours** showing when you were most active
- **Pre-formatted Clockify entries** with:
  - Accurate start times
  - Durations excluding breaks
  - Work descriptions extracted from sessions
  - Part numbers for split sessions (e.g., "Development work - Part 1")

**Optional detailed analysis** for specific files:
```bash
# If you need deeper insights into a particular session
uv run extract_claude_work_insights.py "<specific_file>" "$DATE"
```

### Phase 3: Git Correlation
Check commits across all relevant repositories:
```bash
# Check key repositories for commits
for repo in /home/rolf/Projects/ml_classifier_core /home/rolf/Projects/ai_augmentation /home/rolf/Projects/political_template /home/rolf/fuzzy-ops; do
    if [ -d "$repo/.git" ]; then
        echo "=== Git activity in $repo ==="
        git -C "$repo" log --pretty=format:"%h %ad %s" --date=iso \
            --since="$DATE 00:00" --until="$DATE 23:59" \
            --author="$(git config user.name)"
    fi
done
```

### Phase 4: Analysis & Enhancement

1. **Use enhanced tool output as foundation**:
   - Pre-calculated work blocks with gaps excluded
   - Suggested Clockify entries with descriptions
   - Accurate time calculations

2. **Enhance descriptions with git data**:
   - Match work blocks to git commits
   - Add specific technical achievements
   - Include business value delivered

3. **Review and adjust suggested entries**:
   - Verify project assignments
   - Enhance descriptions with context
   - Split or combine entries as needed

## Expected Output Format

### Enhanced Tool Output
```
Sessions for 2025-07-27:
- Claude sessions: 12 files
- Total duration: 8.5h (excluding breaks)  
- Work blocks: 5 (split by gaps > 15 min)
- Peak hours: 10:00, 14:00, 20:00

Suggested Clockify entries:
1. 09:00 - Fixed StreamController autostart issue - Part 1 (1h 30m)
2. 10:45 - Fixed StreamController autostart issue - Part 2 (45m)
3. 14:00 - Implemented Clockify API client (2h)
```

### Final Enhanced Report
```markdown
# Work Analysis: [DATE]

## Summary (from enhanced tool)
- **Total Work Duration**: X.Xh (breaks excluded)
- **Claude Sessions**: Y files with Z interactions
- **Work Blocks**: N (automatically split by gaps)
- **Peak Hours**: HH:00, HH:00
- **Git Commits**: M commits across repositories

## Detailed Time Blocks

### 09:00 - 10:30 (1h 30m) - **Project: Tools**
**Description**: "Fixed StreamController autostart issue - Part 1"
- Debugged systemd service configuration
- Git: abc123 - "fix: update service file for autostart"
- Impact: Resolved startup issues for 50+ users

### 10:45 - 11:30 (45m) - **Project: Tools**  
**Description**: "Fixed StreamController autostart issue - Part 2"
- Tested and verified functionality
- Created troubleshooting documentation
- Git: def456 - "docs: add autostart guide"

[Gap: 10:30-10:45 - Break detected and excluded]

## Clockify Commands
```bash
# Ready-to-execute (from enhanced analysis + git correlation)
uv run --directory /home/rolf/fuzzy-ops/tools/clockify python /home/rolf/fuzzy-ops/tools/clockify/clockify_entry_manager.py create "Fixed StreamController autostart issue - debugged systemd config" -p "Tools" -s "2025-07-27 09:00" -d "1h30m"

uv run --directory /home/rolf/fuzzy-ops/tools/clockify python /home/rolf/fuzzy-ops/tools/clockify/clockify_entry_manager.py create "Fixed StreamController autostart issue - testing and docs" -p "Tools" -s "2025-07-27 10:45" -d "45m"
```
```

## Requirements

- **Tools**: 
  - `uv` for Python package management
  - Time tracker integration installed
  - `find_claude_sessions_enhanced.py` (NEW - handles gap detection)
  - `extract_claude_work_insights.py` (optional for detailed analysis)
  - Git access to relevant repositories

- **Environment**:
  - Claude sessions in `~/.claude/projects/`
  - Time tracker configuration in place
  - Clockify projects configured

## Key Improvements

### Enhanced Analysis Features
1. **Automatic gap detection**: Breaks > 15 minutes are identified and excluded
2. **Work block splitting**: Sessions are automatically split when gaps occur
3. **Accurate duration calculation**: Only actual work time is counted
4. **Peak hour identification**: Shows when you're most productive
5. **Pre-formatted entries**: Ready-to-use Clockify commands with descriptions

### Why This Matters
- **No more manual calculation** of work durations
- **Breaks are automatically excluded** from time totals
- **Part numbers** help track split sessions (e.g., "Task - Part 1", "Task - Part 2")
- **Descriptions extracted** from actual work done in Claude sessions

## Error Handling

1. **No Claude sessions found**: Check if Claude was used that day
2. **Time tracker fails**: Fall back to Claude session analysis only
3. **Git access issues**: Skip repository or note the error
4. **Missing tools**: Suggest installation commands

## Advanced Features

### Multi-Day Analysis
Can be extended to analyze date ranges:
```bash
for date in {23..26}; do
    /analyze_work_day "2025-07-$date"
done
```

### Project Focus
Add project filter to focus on specific work:
```bash
/analyze_work_day yesterday project:ai_augmentation
```

### Export Options
Generate different output formats:
- Markdown report (default)
- CSV for spreadsheet import
- JSON for further processing

## Related Commands

- `/track`: Quick time entry creation
- `/daily_work_analysis`: Previous version of this workflow
- `/summarise_day`: Lighter weight summary

## Notes

This command replaces manual correlation of multiple data sources with an automated, accurate workflow that:
- Finds ALL relevant work (not just files modified on target date)
- Extracts concrete deliverables automatically
- Suggests time entries based on actual work done
- Identifies discrepancies in time tracking

The content-based JSONL search is critical for accuracy - never use file modification dates!