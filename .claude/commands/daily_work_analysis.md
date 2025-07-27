# Daily Work Analysis & Clockify Integration

Analyze development work patterns, achievements, and activities for a specified date using multiple data sources and generate Clockify time blocks.

## Usage
```
/daily_work_analysis [date]
```

**Arguments:**
- `date`: Target date in format "jul 24", "2025-07-24", "yesterday", "today", etc.

## Phase 1: Data Collection & Time Tracking

### 1.1 Run Time Tracker Analysis
Execute the time tracker to collect session data:

uv run /home/rolf/fuzzy-ops/tools/time-tracker-integration/src/time_tracker.py --start $DATE --end $DATE

**Expected Output**: CSV and JSON files with session data, project breakdowns, and service usage statistics

### 1.2 Extract Claude Work Insights
Run the enhanced JSONL analysis that provides complete work analysis with gap detection:

```bash
# IMPORTANT: The enhanced version analyzes ALL files and provides consolidated output
# It automatically detects gaps, calculates accurate durations, and suggests Clockify entries

# Run the enhanced analysis (combines all Claude sessions for the date)
uv run find_claude_sessions_enhanced.py "$DATE" > claude_work_analysis.txt

# Display the analysis
cat claude_work_analysis.txt

# Optional: If you need detailed insights from specific files, you can still run:
# uv run extract_claude_work_insights.py "<specific_file>" "$DATE"
```

**Expected Output**: Comprehensive analysis including:
- Total work duration (with breaks excluded)
- Number of work blocks (sessions split by >15 min gaps)
- Peak working hours
- Suggested Clockify entries with:
  - Accurate start times
  - Durations excluding breaks
  - Work descriptions extracted from sessions
  - Part numbers for split sessions (e.g., "Development work - Part 1")

### 1.3 Check Git Activity
Examine git commit activity across key repositories:

```bash
# Check key repositories for commits
for repo in /home/rolf/Projects/ml_classifier_core /home/rolf/Projects/ai_augmentation /home/rolf/Projects/political_template /home/rolf/fuzzy-ops; do
    if [ -d "$repo/.git" ]; then
        echo "=== Git activity in $repo ==="
        git -C "$repo" log --pretty=format:"%h %ad %s" --date=iso --since="$DATE 00:00" --until="$DATE 23:59" --author="$(git config user.name)"
    fi
done
```

**Expected Output**: List of commits with timestamps showing completed features, fixes, and improvements


## Phase 2: Data Analysis & Time Block Generation

### 2.1 Analyze Time Tracking Data
**Primary Focus Areas**:
- Session continuity and gaps (automatically detected by enhanced tool)
- Development intensity periods (see peak hours in enhanced output)
- Tool usage patterns (Claude, Cursor, Git integration)
- Project focus allocation
- Work blocks from enhanced analysis (pre-calculated with gaps excluded)

### 2.2 Cross-Reference Data Sources
**Synthesize the following**:
1. **Time tracker** session duration vs **Claude JSONL** interaction complexity
2. **Git commits** timing vs **time tracker** project focus
3. **Meeting patterns** vs **productivity blocks**

### 2.3 Generate Clockify Time Blocks
**The enhanced tool provides suggested entries. Review and enhance them with:**

1. **Use suggested entries from enhanced output**:
   - Already has accurate start times and durations
   - Work descriptions extracted from actual sessions
   - Properly split for gaps > 15 minutes

2. **Enhance descriptions with**:
   - Git commits from the time period
   - Business value delivered
   - Specific technical achievements

**Example enhancement**:
```
# From enhanced tool:
- Fixed TypeError in metrics calculation - Part 1 (45m)

# Enhanced for Clockify:
**09:00 - 09:45** (45m) - **Project: AI_Augmentation**
**Description:** "Fixed TypeError in metrics calculation - implemented null checking"
- Git commit: a1b2c3d - "fix: handle undefined metrics data"
- Prevented production crashes for 500+ users
```

**Meeting Integration**:
```
**Start Time - End Time** (Duration) - **Meeting/Call**
**Description:** "[Meeting purpose and outcomes]"
- Attendees or meeting type
- Key decisions or action items
- Follow-up development work triggered
```

## Phase 3: Analysis Report Structure

### 3.1 Executive Summary
- Total productive hours tracked
- Meeting vs development time allocation
- Primary project focus
- Major achievements completed

### 3.2 Detailed Time Blocks for Clockify
**Format each block as:**
1. **Time Range** - Clear start/end times
2. **Project/Category** - Specific project or "Meeting"
3. **Achievement Description** - What was accomplished
4. **Technical Details** - Files modified, commits, impact

### 3.3 Development Insights
- **Tool Integration Patterns**: Claude/Cursor/Git workflow efficiency
- **Session Quality**: Focused blocks vs scattered activity
- **Meeting Impact**: How meetings affected development flow
- **Problem-Solving Approach**: Research → implementation → testing patterns


## Phase 4: Output Format

### 4.1 Enhanced Tool Output Integration
The enhanced tool provides a foundation that includes:
- Pre-calculated work blocks with gaps excluded
- Suggested Clockify entries with descriptions
- Accurate time calculations

**Example enhanced tool output**:
```
Sessions for 2025-07-27:
- Claude sessions: 12
- Total duration: 8.5h (excluding breaks)
- Work blocks: 5 (split by gaps > 15 min)
- Peak hours: 10:00, 14:00, 20:00

Suggested Clockify entries:
- Fixed StreamController autostart issue - Part 1 (1h 30m)
- Fixed StreamController autostart issue - Part 2 (45m)
- Implemented Clockify API client (2h)
```

### 4.2 Final Clockify Time Blocks (Enhanced)
```markdown
# Clockify Time Blocks for [Date]

## Development Sessions (from enhanced tool + git data)
### **09:00 - 10:30** (1h 30m) - **Project: Tools**
**Description:** "Fixed StreamController autostart issue - Part 1"
- Debugged systemd service configuration
- Git commit: abc123 - "fix: update service file for autostart"
- Resolved startup issues affecting 50+ users

### **10:45 - 11:30** (45m) - **Project: Tools**
**Description:** "Fixed StreamController autostart issue - Part 2"
- Tested and verified autostart functionality
- Created documentation for configuration
- Git commit: def456 - "docs: add autostart troubleshooting guide"

## Meetings & Calls (from calendar/gaps)
### **10:30 - 10:45** (15m) - **Break**
**Description:** "Short break between work blocks"

## **Total Time: Xh Ym**
- Development: Xh Ym (from enhanced tool)
- Meetings: Xh Ym
- Breaks excluded: Xh Ym (automatically calculated)
```

### 4.3 Productivity Analysis
```markdown
## Workflow Analysis
- **Peak Development Windows**: [Times when most productive]
- **Meeting Distribution**: [How meetings affected flow]
- **Context Switching**: [Impact of interruptions]
- **Tool Effectiveness**: [Claude/Cursor integration success]

## Key Achievements
1. [Major deliverable 1 with business impact]
2. [Major deliverable 2 with business impact]
3. [Major deliverable 3 with business impact]

## Optimization Recommendations
- [Schedule optimization suggestions]
- [Workflow improvement opportunities]
- [Meeting efficiency recommendations]
```

## Implementation Notes

### Enhanced Tool Integration
1. **Primary Analysis**: `find_claude_sessions_enhanced.py` provides complete analysis
2. **Gap Detection**: Automatically identifies breaks > 15 minutes
3. **Duration Calculation**: Excludes break time from work duration
4. **Clockify Suggestions**: Pre-formatted entries ready for use

### Data Sources Priority
1. **Time Tracker CSV**: Primary source for session timing
2. **Git Commits**: Achievement validation and timing
3. **Claude JSONL**: Work complexity and tool usage

### Quality Indicators
**High-Value Work**:
- Extended Claude sessions (>100 interactions)
- Multiple git commits in focused timeframes
- Complex problem-solving with tool integration
- Sustained development blocks (>2 hours)

## Success Metrics
- **Accuracy**: Time blocks match actual work performed
- **Completeness**: All significant work captured
- **Clarity**: Descriptions highlight business value
- **Efficiency**: Quick generation with minimal manual input

**Remember**: Focus on **business value delivered** and **achievements completed**, not just time spent or tools used. Include meeting context to provide complete daily work picture for stakeholders.