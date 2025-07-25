# Daily Work Analysis Slash Command

## Quick Reference

### Usage
```
/daily_work_analysis [date]
```

### Examples
- `/daily_work_analysis jul 23`
- `/daily_work_analysis 2025-07-24` 
- `/daily_work_analysis yesterday`
- `/daily_work_analysis today`

### What It Does
1. **Collects Data**: Time tracker, Claude sessions, git commits, calendar events
2. **Analyzes Patterns**: Development vs meeting time, productivity windows
3. **Generates Output**: Clockify time blocks with achievement descriptions

### Output Includes
- **Clockify Time Blocks**: Ready-to-paste time entries with business value descriptions
- **Meeting Integration**: Calendar events and development session gaps
- **Productivity Analysis**: Peak performance windows and workflow insights
- **Achievement Summary**: Git commits, technical deliverables, business impact

### Key Features
- **Multi-Source Analysis**: Combines time tracking, code commits, and calendar data
- **Business Value Focus**: Descriptions emphasize deliverables and impact
- **Meeting Detection**: Identifies gaps in development for meeting periods
- **Calendar Integration**: Attempts gcalcli integration for meeting context
- **Productivity Insights**: Recommendations for schedule optimization

### File Locations
- **Slash Command**: `/home/rolf/.claude/slash_commands/daily_work_analysis.md`
- **Documentation**: `/home/rolf/fuzzy-ops/tools/time-tracker-integration/daily_work_analysis.md`
- **Time Tracker**: `/home/rolf/fuzzy-ops/tools/time-tracker-integration/src/time_tracker.py`
- **Claude Insights**: `/home/rolf/fuzzy-ops/tools/time-tracker-integration/extract_claude_work_insights.py`

### Sample Output Format
```
# Clockify Time Blocks for July 23rd, 2025

## Morning Development Sessions
### **06:30 - 09:20** (2h 50m) - **Project: AI Augmentation**
**Description:** "Initial research and setup for dashboard metrics analysis..."

## **Total Time: 13h 43m**
### Key Achievements:
1. Complete Timesheet Analysis System - Built from scratch with fraud detection
2. Dashboard Unification - Consolidated multiple views with improved UX
3. 8 Major Git Commits - Substantial feature deliveries
```

The command automates the entire workflow from the manual analysis we performed, making it repeatable for any date with a single command.