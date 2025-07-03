# Visualization Options

The Time Tracker Integration provides multiple ways to visualize your coding activity.

## 1. ASCII Heatmap (Simplest)

GitHub-style activity heatmap in your terminal showing coding intensity.

### Generate Heatmap
```bash
uv run src/generate_heatmap.py
```

### Features
- **15-minute granularity** - Shows intensity for each quarter hour
- **Visual intensity** - Uses Unicode blocks (░ ▒ ▓ █)  
- **Daily summaries** - Total hours per day
- **Hour distribution** - See your most active times
- **No dependencies** - Pure terminal output

### Example Output
```
06/24 ............ ............ ............ .........▓██ ███████▒.... .......▓████    4.7h
06/25 ............ ............ ....▒███▓..▓ .▓██........ ............ ............    2.8h
```

## 2. Static Dashboard (Recommended for Reports)

The simplest option - generates a self-contained HTML file with interactive charts.

### Generate Dashboard
```bash
# Generate from latest data
./dashboard.sh

# Generate from specific CSV
./dashboard.sh data/time_tracking_20250625.csv
```

### Features
- **No server required** - Just open the HTML file
- **Interactive charts** using Chart.js
- **Responsive design** - Works on mobile
- **Includes**:
  - Daily activity bar chart
  - Repository time distribution (donut chart)
  - Session timeline
  - Repository summary cards
  - Key statistics

### Output
- File: `data/dashboard.html`
- Opens automatically in browser (Linux/Mac)
- Completely self-contained - share the HTML file with anyone

## 2. Interactive Web Dashboard

A full-featured Flask web application with real-time updates.

### Start Server
```bash
# With uv
uv run --with flask --with plotly --with pandas --with pyyaml python src/dashboard.py

# Or with uv pip
uv pip install flask plotly
uv run src/dashboard.py
```

### Features
- **Real-time updates** - Auto-refreshes every 30 seconds
- **Advanced visualizations**:
  - Interactive timeline (vis-timeline)
  - Activity heatmap (Plotly)
  - Zoomable charts
- **API endpoints** for custom integrations
- **Date range filtering**

### Access
- Open http://localhost:5000 in your browser
- API endpoints:
  - `/api/timeline` - Session data
  - `/api/heatmap` - Activity heatmap
  - `/api/summary/repos` - Repository statistics
  - `/api/summary/daily` - Daily summaries

## 3. Command Line Visualization

The basic time tracker already provides console output:

```bash
uv run src/time_tracker.py --days 7
```

Output includes:
- Repository summary with total hours
- Service breakdown (Claude/Cursor)
- Daily activity timeline
- CSV/JSON exports for custom analysis

## Comparison

| Feature | Static Dashboard | Web Dashboard | CLI Output |
|---------|-----------------|---------------|------------|
| Setup | None | Flask required | None |
| Interactivity | Basic | Full | None |
| Sharing | Easy (HTML file) | Requires hosting | Text/CSV |
| Real-time | No | Yes | No |
| Mobile | Yes | Yes | No |
| Dependencies | None | Flask, Plotly | None |

## Custom Visualizations

Both dashboards expose the data in formats suitable for further analysis:

### Using the Data
```python
import pandas as pd
import matplotlib.pyplot as plt

# Load the data
df = pd.read_csv('data/time_tracking_latest.csv')
df['start'] = pd.to_datetime(df['start'])
df['end'] = pd.to_datetime(df['end'])

# Create custom visualizations
# ... your code here
```

### Data Structure
Each session includes:
- `start`, `end` - Timestamps
- `identified_repo` - Repository name
- `service` - Tool used (Claude/Cursor)
- `duration_hours` - Session length
- `commits_in_window` - Related commits

## Tips

1. **For quick checks**: Use the static dashboard
2. **For monitoring**: Use the web dashboard
3. **For automation**: Use the JSON API or CSV exports
4. **For presentations**: Export charts from the static dashboard

## Extending Visualizations

To add new chart types, edit:
- Static: `src/generate_static_dashboard.py`
- Web: `templates/dashboard.html` and `src/dashboard.py`

Both use standard libraries (Chart.js, Plotly) with extensive documentation.