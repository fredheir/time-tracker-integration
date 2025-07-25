# Daily Work Analysis & Clockify Integration

Analyze development work patterns, achievements, and activities for a specified date using multiple data sources and generate Clockify time blocks with calendar integration.

## Usage
```
/daily_work_analysis [date]
```

**Arguments:**
- `date`: Target date in format "jul 24", "2025-07-24", "yesterday", "today", etc.

## Phase 1: Data Collection & Time Tracking

### 1.1 Run Time Tracker Analysis
Execute the time tracker to collect session data:

```bash
cd /home/rolf/fuzzy-ops/tools/time-tracker-integration
uv run src/time_tracker.py --start $DATE --end $DATE
```

**Expected Output**: CSV and JSON files with session data, project breakdowns, and service usage statistics

### 1.2 Extract Claude Work Insights  
Run the JSONL extraction script on all available Claude projects:

```bash
# Find all Claude project JSONL files for the target date
find ~/.claude/projects -name "*.jsonl" -newermt "$DATE" ! -newermt "$(date -d "$DATE + 1 day" +%Y-%m-%d)" | head -10

# Extract insights from each relevant file
for file in $(find ~/.claude/projects -name "*.jsonl" -newermt "$DATE" ! -newermt "$(date -d "$DATE + 1 day" +%Y-%m-%d)" | head -5); do
    echo "=== Analyzing: $file ==="
    python extract_claude_work_insights.py "$file" $DATE
done
```

**Expected Output**: Detailed session analysis including:
- Git branches worked on
- Working directories 
- Tool usage patterns
- User requests and assistant responses
- Token usage and interaction complexity

### 1.3 Check Git Activity
Examine git commit activity across key repositories:

```bash
# Check key repositories for commits
for repo in /home/rolf/Projects/ai_augmentation /home/rolf/Projects/political_template /home/rolf/fuzzy-ops; do
    if [ -d "$repo/.git" ]; then
        echo "=== Git activity in $repo ==="
        git -C "$repo" log --pretty=format:"%h %ad %s" --date=iso --since="$DATE 00:00" --until="$DATE 23:59" --author="$(git config user.name)"
    fi
done
```

**Expected Output**: List of commits with timestamps showing completed features, fixes, and improvements

### 1.4 Calendar Integration
Fetch calendar events for context on meetings and scheduled work:

```bash
# Check for calendar events using gcalcli or similar tool
gcalcli agenda --nostarted --calendar="primary" $DATE $(date -d "$DATE + 1 day" +%Y-%m-%d) 2>/dev/null || echo "Calendar tool not available - manual calendar review recommended"

# Alternative: Check common meeting time patterns from time tracking data
echo "=== Meeting Detection from Time Tracking ==="
echo "Look for gaps in development activity that might indicate meetings or calls"
```

## Phase 2: Data Analysis & Time Block Generation

### 2.1 Analyze Time Tracking Data
**Primary Focus Areas**:
- Session continuity and gaps (potential meetings)
- Development intensity periods
- Tool usage patterns (Claude, Cursor, Git integration)
- Project focus allocation

### 2.2 Cross-Reference Data Sources
**Synthesize the following**:
1. **Time tracker** session duration vs **Claude JSONL** interaction complexity
2. **Git commits** timing vs **time tracker** project focus  
3. **Calendar events** vs **development session gaps**
4. **Meeting patterns** vs **productivity blocks**

### 2.3 Generate Clockify Time Blocks
**Structure for each time block**:
```
**Start Time - End Time** (Duration) - **Project: [Name]**
**Description:** "[Achievement-focused description with specific deliverables]"
- Key technical work completed
- Git commits: [commit hash] - [message]
- Business value delivered
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

### 3.4 Calendar Context Integration
**Meeting Analysis**:
- Scheduled meetings vs development time
- Meeting preparation and follow-up time
- Context switching overhead
- Optimal development block identification

**Time Optimization Insights**:
- Best performing development windows
- Meeting schedule impact on productivity
- Recommendations for schedule optimization

## Phase 4: Output Format

### 4.1 Clockify Time Blocks (Primary Output)
```markdown
# Clockify Time Blocks for [Date]

## Development Sessions
### **HH:MM - HH:MM** (Xh Ym) - **Project: [Name]**
**Description:** "[Achievement summary with business value]"
- Specific deliverables completed
- Git commits: [hash] - [message]
- Technical impact and next steps

## Meetings & Calls
### **HH:MM - HH:MM** (Xh Ym) - **Meeting: [Type/Purpose]**
**Description:** "[Meeting purpose and outcomes]"
- Key participants and decisions
- Action items assigned
- Impact on development priorities

## **Total Time: Xh Ym**
- Development: Xh Ym
- Meetings: Xh Ym  
- Administrative: Xh Ym
```

### 4.2 Productivity Analysis
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

### Calendar Integration Options
1. **gcalcli**: Command-line Google Calendar access
2. **Outlook CLI**: For Microsoft calendars
3. **Manual Review**: Prompt user to add meeting context
4. **Time Gap Analysis**: Detect meeting periods from development gaps

### Data Sources Priority
1. **Time Tracker CSV**: Primary source for session timing
2. **Git Commits**: Achievement validation and timing
3. **Claude JSONL**: Work complexity and tool usage
4. **Calendar Events**: Meeting context and schedule impact

### Quality Indicators
**High-Value Work**:
- Extended Claude sessions (>100 interactions)
- Multiple git commits in focused timeframes
- Complex problem-solving with tool integration
- Sustained development blocks (>2 hours)

**Meeting Effectiveness**:
- Clear outcomes and action items
- Minimal development disruption
- Follow-up development work alignment

## Success Metrics
- **Accuracy**: Time blocks match actual work performed
- **Completeness**: All significant work captured
- **Clarity**: Descriptions highlight business value
- **Efficiency**: Quick generation with minimal manual input
- **Integration**: Seamless calendar and development data fusion

**Remember**: Focus on **business value delivered** and **achievements completed**, not just time spent or tools used. Include meeting context to provide complete daily work picture for stakeholders.