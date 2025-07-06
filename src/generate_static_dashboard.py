#!/usr/bin/env python3
"""Generate a static HTML dashboard from time tracking data"""

import json
import pandas as pd
from datetime import datetime
from pathlib import Path
import sys
try:
    from calendar_integration import CalendarIntegration
except ImportError:
    CalendarIntegration = None

def generate_static_dashboard(csv_file=None):
    """Generate a self-contained HTML dashboard"""
    
    # Find the latest CSV if not specified
    data_dir = Path('./data')
    if csv_file is None:
        csv_files = list(data_dir.glob('time_tracking_*.csv'))
        if not csv_files:
            print("No time tracking data found. Running time tracker for last 7 days...")
            # Run the time tracker to generate data
            import subprocess
            import os
            
            # Check if uv is available
            if subprocess.run(['which', 'uv'], capture_output=True).returncode == 0:
                subprocess.run(['uv', 'run', '--with', 'pandas', '--with', 'pyyaml', 'python', 'src/time_tracker.py', '--days', '7'], check=True)
            else:
                subprocess.run(['python', 'src/time_tracker.py', '--days', '7'], check=True)
            
            # Now try to find the CSV again
            csv_files = list(data_dir.glob('time_tracking_*.csv'))
            if not csv_files:
                print("Failed to generate tracking data.")
                return
                
        csv_file = max(csv_files, key=lambda f: f.stat().st_mtime)
    
    # Load data
    df = pd.read_csv(csv_file)
    df['start'] = pd.to_datetime(df['start'], format='ISO8601', utc=True)
    df['end'] = pd.to_datetime(df['end'], format='ISO8601', utc=True)
    df['project'] = df['project'].fillna('Unknown')
    
    # Calculate data source statistics
    source_stats = df.groupby('service').agg({
        'duration_hours': 'sum',
        'service': 'count',
        'project': lambda x: x.nunique()
    }).rename(columns={'service': 'sessions', 'project': 'projects'}).to_dict('index')
    
    
    # Check for potential missing data sources
    expected_sources = ['Claude', 'Cursor', 'VSCode']
    found_sources = list(source_stats.keys())
    missing_sources = [s for s in expected_sources if s not in found_sources]
    
    # Prepare data for JavaScript
    timeline_data = []
    for _, row in df.iterrows():
        timeline_data.append({
            'start': row['start'].isoformat(),
            'end': row['end'].isoformat(),
            'repo': row.get('identified_repo', 'Unknown'),
            'service': row.get('service', 'Unknown'),
            'project': row.get('project', 'Unknown'),
            'duration': round(row.get('duration_hours', 0), 2),
            'commits': int(row.get('commits_in_window', 0))
        })
    
    # Daily data grouped by repo for stacked bar chart
    daily_repo_data = df.groupby([df['start'].dt.date.astype(str), 'identified_repo'])['duration_hours'].sum().unstack(fill_value=0)
    
    # Prepare repo colors
    repo_colors = {
        'political_template': '#3498db',
        'ai_augmentation': '#e74c3c',
        'Unknown': '#95a5a6',
        'core': '#2ecc71',
        'augmentation': '#f39c12',
        'Experiments': '#9b59b6',
        'Downloads': '#1abc9c'
    }
    
    # Get all unique repos
    all_repos = df['identified_repo'].unique().tolist()
    for repo in all_repos:
        if repo not in repo_colors:
            repo_colors[repo] = f'hsl({hash(repo) % 360}, 70%, 50%)'
    
    # Calculate statistics
    total_hours = df['duration_hours'].sum()
    total_sessions = len(df)
    repos = df['identified_repo'].nunique()
    
    # Repository summary
    repo_summary = df.groupby('identified_repo').agg({
        'duration_hours': 'sum',
        'service': 'count',
        'commits_in_window': 'max'
    }).round(2).to_dict('index')
    
    # Load config to check calendar settings
    config = {}
    config_path = Path('./config/config.yaml')
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f) or {}
        except:
            pass
    
    # Fetch calendar meetings if enabled in config
    meetings_data = []
    show_meetings = config.get('calendar', {}).get('display', {}).get('show_in_web', True)
    calendar_enabled = config.get('calendar', {}).get('enabled', True)
    
    if CalendarIntegration and show_meetings and calendar_enabled:
        try:
            cal = CalendarIntegration(config_path=config_path)
            if cal.authenticate():
                # Get meetings for the same date range as the time tracking data
                start_datetime = df['start'].min()
                end_datetime = df['end'].max()
                meetings = cal.get_meetings(start_datetime, end_datetime)
                
                # Prepare meetings for JavaScript
                for meeting in meetings:
                    meetings_data.append({
                        'id': meeting['id'],
                        'summary': meeting['summary'],
                        'start': meeting['start'],
                        'end': meeting['end'],
                        'duration': meeting['duration_minutes'],
                        'attendees': meeting['attendees'],
                        'attendee_count': meeting['attendee_count'],
                        'location': meeting.get('location', ''),
                        'type': 'meeting'
                    })
                
                print(f"Loaded {len(meetings_data)} calendar meetings")
        except Exception as e:
            print(f"Warning: Could not load calendar meetings: {e}")
    
    # Add Calendar to source stats if meetings were found
    if meetings_data:
        total_meeting_hours = sum(m['duration'] / 60 for m in meetings_data)
        source_stats['Calendar'] = {
            'duration_hours': total_meeting_hours,
            'sessions': len(meetings_data),
            'projects': 1
        }
    
    # Generate HTML
    html_template = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Time Tracker Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/date-fns@2.29.3/index.min.js"></script>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 0;
            background: #f5f7fa;
        }
        .dashboard-layout {
            display: flex;
            min-height: 100vh;
        }
        .sidebar {
            width: 300px;
            background: white;
            box-shadow: 2px 0 10px rgba(0,0,0,0.1);
            padding: 20px;
            overflow-y: auto;
            position: fixed;
            height: 100vh;
        }
        .main-content {
            margin-left: 320px;
            padding: 20px;
            flex: 1;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
        }
        h1 {
            color: #2c3e50;
            margin-bottom: 30px;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }
        .stat-value {
            font-size: 2.5em;
            font-weight: bold;
            color: #3498db;
        }
        .stat-label {
            color: #7f8c8d;
            margin-top: 10px;
        }
        .chart-container {
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .timeline {
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow-x: auto;
        }
        .repo-summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        .repo-card {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #3498db;
        }
        .repo-name {
            font-weight: bold;
            margin-bottom: 10px;
        }
        .repo-stats {
            font-size: 0.9em;
            color: #666;
        }
        .generated {
            text-align: center;
            color: #999;
            margin-top: 30px;
            font-size: 0.9em;
        }
        .filter-container {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            border: 1px solid #e9ecef;
        }
        .sidebar h2 {
            margin-top: 0;
            margin-bottom: 25px;
            color: #2c3e50;
            font-size: 1.3em;
            border-bottom: 2px solid #e9ecef;
            padding-bottom: 10px;
        }
        .sidebar h3 {
            margin-top: 0;
            margin-bottom: 15px;
            color: #2c3e50;
            font-size: 1.1em;
        }
        .filter-buttons {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 10px;
        }
        .filter-btn {
            padding: 6px 12px;
            border: 2px solid #ddd;
            background: white;
            border-radius: 16px;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 0.8em;
            text-align: center;
            min-width: fit-content;
        }
        .filter-btn.active {
            background: #3498db;
            color: white;
            border-color: #3498db;
        }
        .filter-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .data-sources {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .source-item {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #f0f0f0;
        }
        .source-item:last-child {
            border-bottom: none;
        }
        .source-name {
            font-weight: 500;
        }
        .source-stats {
            color: #666;
            font-size: 0.9em;
        }
        .warning {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            color: #856404;
            padding: 10px 15px;
            border-radius: 5px;
            margin-top: 15px;
            font-size: 0.9em;
        }
        .info-badge {
            background: #e9ecef;
            color: #495057;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            margin-left: 5px;
        }
        #heatmap {
            display: flex;
            flex-direction: column;
            gap: 2px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        .heatmap-row {
            display: flex;
            gap: 2px;
            align-items: center;
        }
        .heatmap-label {
            width: 60px;
            font-size: 0.8em;
            color: #666;
            text-align: right;
            padding-right: 10px;
        }
        .heatmap-blocks {
            display: flex;
            gap: 1px;
        }
        .heatmap-block {
            width: 8px;
            height: 20px;
            background: #e0e0e0;
            border-radius: 2px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .heatmap-block:hover {
            transform: scale(1.2);
        }
        .heatmap-block.intensity-0 { background: #f0f0f0; }
        .heatmap-block.intensity-1 { background: #9be9a8; }
        .heatmap-block.intensity-2 { background: #40c463; }
        .heatmap-block.intensity-3 { background: #30a14e; }
        .heatmap-block.intensity-4 { background: #216e39; }
        
        /* Alternating hour backgrounds - simple and clean */
        .heatmap-block.even-hour.intensity-0 { background: #f5f5f5; }
        .heatmap-block.odd-hour.intensity-0 { background: #e8e8e8; }
        
        /* Subtle alternating pattern for active blocks */
        .heatmap-block.odd-hour:not(.intensity-0) {
            filter: brightness(0.95);
        }
        
        /* Hour start indicators - left accent line */
        .heatmap-block.hour-start {
            box-shadow: inset 2px 0 0 0 #666;
        }
        .heatmap-block.hour-start.intensity-0 {
            box-shadow: inset 2px 0 0 0 #999;
        }
        /* Meeting blocks with different colors */
        .heatmap-block.meeting-0 { background: ''' + config.get('calendar', {}).get('display', {}).get('colors', {}).get('light', '#f3e5ff') + '''; }
        .heatmap-block.meeting-1 { background: ''' + config.get('calendar', {}).get('display', {}).get('colors', {}).get('medium_light', '#d4b5ff') + '''; }
        .heatmap-block.meeting-2 { background: ''' + config.get('calendar', {}).get('display', {}).get('colors', {}).get('medium', '#b794f6') + '''; }
        .heatmap-block.meeting-3 { background: ''' + config.get('calendar', {}).get('display', {}).get('colors', {}).get('medium_dark', '#9f7aea') + '''; }
        .heatmap-block.meeting-4 { background: ''' + config.get('calendar', {}).get('display', {}).get('colors', {}).get('dark', '#805ad5') + '''; }
        .heatmap-legend {
            display: flex;
            gap: 10px;
            margin-top: 10px;
            font-size: 0.8em;
            color: #666;
            align-items: center;
            justify-content: center;
        }
        .heatmap-hours {
            display: flex;
            gap: 1px;
            margin-bottom: 5px;
            padding-left: 70px;
        }
        .heatmap-hour {
            width: 35px;
            text-align: center;
            font-size: 0.7em;
            color: #999;
        }
    </style>
</head>
<body>
    <div class="dashboard-layout">
        <div class="sidebar">
            <h2>🎛️ Filters</h2>
            
            <div class="filter-container">
                <h3>🎯 Repository</h3>
                <div class="filter-buttons" id="repoFilterButtons"></div>
            </div>
            
            <div class="filter-container">
                <h3>📂 Project</h3>
                <div class="filter-buttons" id="projectFilterButtons"></div>
            </div>

            <div class="filter-container">
                <h3>☁️ Source</h3>
                <div class="filter-buttons" id="sourceFilterButtons"></div>
            </div>
        </div>
        
        <div class="main-content">
            <div class="container">
                <h1>⏱️ Time Tracker Dashboard</h1>
                
                <div class="stats">
                    <div class="stat-card">
                        <div class="stat-value">''' + f"{total_hours:.1f}" + '''</div>
                        <div class="stat-label">Total Hours</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">''' + str(total_sessions) + '''</div>
                        <div class="stat-label">Sessions</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">''' + str(repos) + '''</div>
                        <div class="stat-label">Repositories</div>
                    </div>
                </div>
        
        <div class="chart-container">
            <h2>📊 Daily Activity</h2>
            <div style="position: relative; height: 300px;">
                <canvas id="dailyChart"></canvas>
            </div>
        </div>
        
        <div class="chart-container">
            <h2>🍩 Time by Repository</h2>
            <div style="position: relative; height: 300px;">
                <canvas id="repoChart"></canvas>
            </div>
        </div>
        
        <div class="chart-container">
            <h2>🔥 Activity Heatmap</h2>
            <div id="heatmap"></div>
        </div>
        
        <div class="timeline">
            <h2>📅 Session Timeline</h2>
            <div style="position: relative; height: 400px;">
                <canvas id="ganttChart"></canvas>
            </div>
        </div>
        
        <div class="chart-container">
            <h2>🏆 Repository Summary</h2>
            <div class="repo-summary" id="repoSummary"></div>
        </div>
        
        <div class="data-sources">
            <h3>📊 Data Sources</h3>
            <div id="sourcesList"></div>
        </div>
        
        <div class="generated">
            Generated on ''' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '''
        </div>
            </div>
        </div>
    </div>
    
    <script>
        const timelineData = ''' + json.dumps(timeline_data) + ''';
        const meetingsData = ''' + json.dumps(meetings_data) + ''';
        const repoSummary = ''' + json.dumps(repo_summary) + ''';
        const sourceStats = ''' + json.dumps(source_stats) + ''';
        const missingSources = ''' + json.dumps(missing_sources) + ''';
        const allProjects = ''' + json.dumps(df['project'].unique().tolist()) + ''';
        const allSources = ''' + json.dumps(df['service'].unique().tolist() + (['Calendar'] if meetings_data else [])) + ''';

        // Global chart instances
        let dailyChart, repoChart, ganttChart;
        
        // Active filters
        let activeRepos = new Set(Object.keys(repoSummary));
        let activeProjects = new Set(allProjects);
        let activeSources = new Set(allSources);
        
        // Group by day for daily chart
        const dailyData = timelineData.reduce((acc, session) => {
            const day = session.start.split('T')[0];
            if (!acc[day]) acc[day] = 0;
            acc[day] += session.duration;
            return acc;
        }, {});
        
        // Prepare daily data by repository
        const dailyRepoData = {};
        const repoColors = ''' + json.dumps(repo_colors) + ''';
        const allRepos = ''' + json.dumps(all_repos) + ''';
        
        timelineData.forEach(session => {
            const day = session.start.split('T')[0];
            if (!dailyRepoData[session.repo]) {
                dailyRepoData[session.repo] = {};
            }
            if (!dailyRepoData[session.repo][day]) {
                dailyRepoData[session.repo][day] = 0;
            }
            dailyRepoData[session.repo][day] += session.duration;
        });
        
        // Get all days
        const allDays = [...new Set(timelineData.map(s => s.start.split('T')[0]))].sort();
        
        // Create datasets for stacked bar chart
        const datasets = allRepos.map(repo => ({
            label: repo,
            data: allDays.map(day => (dailyRepoData[repo] && dailyRepoData[repo][day]) || 0),
            backgroundColor: repoColors[repo] || '#95a5a6'
        }));
        
        // Daily activity chart
        const dailyCtx = document.getElementById('dailyChart').getContext('2d');
        dailyChart = new Chart(dailyCtx, {
            type: 'bar',
            data: {
                labels: allDays,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        stacked: true
                    },
                    y: {
                        stacked: true,
                        beginAtZero: true
                    }
                }
            }
        });
        
        // Repository pie chart
        const repoCtx = document.getElementById('repoChart').getContext('2d');
        const repoLabels = Object.keys(repoSummary);
        const repoData = repoLabels.map(r => repoSummary[r].duration_hours);
        
        repoChart = new Chart(repoCtx, {
            type: 'doughnut',
            data: {
                labels: repoLabels,
                datasets: [{
                    data: repoData,
                    backgroundColor: [
                        '#3498db', '#e74c3c', '#2ecc71', '#f39c12', 
                        '#9b59b6', '#1abc9c', '#34495e', '#e67e22'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
        
        // Gantt chart (simplified timeline)
        const ganttCtx = document.getElementById('ganttChart').getContext('2d');
        
        // Group sessions by service
        const services = [...new Set(timelineData.map(s => s.service))];
        const ganttDatasets = services.map((service, idx) => {
            const serviceData = timelineData
                .filter(s => s.service === service)
                .map(s => ({
                    x: [new Date(s.start), new Date(s.end)],
                    y: service,
                    repo: s.repo
                }));
            
            return {
                label: service,
                data: serviceData,
                backgroundColor: idx === 0 ? '#3498db' : '#e74c3c',
                barThickness: 20
            };
        });
        
        // Create a scatter plot that looks like a gantt chart
        // For now, let's skip the gantt chart since it's causing issues
        // We'll create a simple timeline view instead
        ganttChart = new Chart(ganttCtx, {
            type: 'bar',
            data: {
                labels: [...new Set(timelineData.map(s => s.start.split('T')[0]))].sort(),
                datasets: [{
                    label: 'Sessions per Day',
                    data: [...new Set(timelineData.map(s => s.start.split('T')[0]))].sort().map(day => 
                        timelineData.filter(s => s.start.startsWith(day)).length
                    ),
                    backgroundColor: '#3498db'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Number of Sessions'
                        }
                    }
                }
            }
        });
        
        // Generate heatmap - now accepts optional data parameter
        function generateHeatmap(data) {
            const dataToUse = data || timelineData.filter(s => 
                activeRepos.has(s.repo) && 
                activeProjects.has(s.project) && 
                activeSources.has(s.service)
            );
            
            // Filter meetings based on Calendar source being active
            const meetingsToUse = activeSources.has('Calendar') ? meetingsData : [];
            
            const heatmapContainer = document.getElementById('heatmap');
            
            // Calculate intensity for each 15-minute block
            const intensityMap = {};
            const meetingsMap = {}; // Track meetings in each block
            const blockSessions = {}; // Track sessions in each block
            const blockMeetings = {}; // Track meetings details in each block
            const hourSessions = {}; // Track sessions by hour for tooltips
            const continuousSessions = {}; // Track continuous session spans
            
            // Process coding sessions
            dataToUse.forEach(session => {
                const start = new Date(session.start);
                const end = new Date(session.end);
                const sessionId = `${session.repo}-${session.service}-${session.start}`;
                
                // Round to 15-minute blocks
                const blockStart = new Date(Math.floor(start.getTime() / (15 * 60 * 1000)) * 15 * 60 * 1000);
                const blockEnd = new Date(Math.ceil(end.getTime() / (15 * 60 * 1000)) * 15 * 60 * 1000);
                
                // Track continuous session info
                continuousSessions[sessionId] = {
                    start: blockStart,
                    end: blockEnd,
                    repo: session.repo,
                    service: session.service,
                    totalDuration: session.duration * 60, // in minutes
                    blocks: []
                };
                
                let current = new Date(blockStart);
                while (current < blockEnd) {
                    const dateKey = current.toISOString().split('T')[0];
                    const hour = current.getHours();
                    const minute = current.getMinutes();
                    const blockKey = `${dateKey}-${hour}-${minute}`;
                    const hourKey = `${dateKey}-${hour}`;
                    
                    intensityMap[blockKey] = (intensityMap[blockKey] || 0) + 1;
                    
                    // Track session info for this block
                    if (!blockSessions[blockKey]) {
                        blockSessions[blockKey] = [];
                    }
                    
                    // Calculate time spent in this specific 15-minute block
                    const blockStartTime = new Date(current);
                    const blockEndTime = new Date(current.getTime() + 15 * 60 * 1000);
                    const actualStart = start > blockStartTime ? start : blockStartTime;
                    const actualEnd = end < blockEndTime ? end : blockEndTime;
                    const blockMinutes = (actualEnd - actualStart) / (1000 * 60);
                    
                    blockSessions[blockKey].push({
                        repo: session.repo,
                        duration: blockMinutes,
                        service: session.service,
                        sessionId: sessionId
                    });
                    
                    // Add block to continuous session
                    continuousSessions[sessionId].blocks.push(blockKey);
                    
                    // Also track by hour for aggregated tooltips
                    if (!hourSessions[hourKey]) {
                        hourSessions[hourKey] = {};
                    }
                    const sessionKey = `${session.repo}-${session.service}`;
                    if (!hourSessions[hourKey][sessionKey]) {
                        hourSessions[hourKey][sessionKey] = {
                            repo: session.repo,
                            service: session.service,
                            duration: 0
                        };
                    }
                    hourSessions[hourKey][sessionKey].duration += blockMinutes;
                    
                    current = new Date(current.getTime() + 15 * 60 * 1000);
                }
            });
            
            // Process meetings
            meetingsToUse.forEach(meeting => {
                const start = new Date(meeting.start);
                const end = new Date(meeting.end);
                const meetingId = meeting.id;
                
                // Round to 15-minute blocks
                const blockStart = new Date(Math.floor(start.getTime() / (15 * 60 * 1000)) * 15 * 60 * 1000);
                const blockEnd = new Date(Math.ceil(end.getTime() / (15 * 60 * 1000)) * 15 * 60 * 1000);
                
                let current = new Date(blockStart);
                while (current < blockEnd) {
                    const dateKey = current.toISOString().split('T')[0];
                    const hour = current.getHours();
                    const minute = current.getMinutes();
                    const blockKey = `${dateKey}-${hour}-${minute}`;
                    
                    // Calculate time spent in this specific 15-minute block
                    const blockStartTime = new Date(current);
                    const blockEndTime = new Date(current.getTime() + 15 * 60 * 1000);
                    const actualStart = start > blockStartTime ? start : blockStartTime;
                    const actualEnd = end < blockEndTime ? end : blockEndTime;
                    const blockMinutes = (actualEnd - actualStart) / (1000 * 60);
                    
                    if (blockMinutes > 0) {
                        meetingsMap[blockKey] = (meetingsMap[blockKey] || 0) + 1;
                        
                        // Track meeting details for this block
                        if (!blockMeetings[blockKey]) {
                            blockMeetings[blockKey] = [];
                        }
                        
                        blockMeetings[blockKey].push({
                            summary: meeting.summary,
                            duration: blockMinutes,
                            attendees: meeting.attendees,
                            location: meeting.location,
                            totalDuration: meeting.duration
                        });
                    }
                    
                    current = new Date(current.getTime() + 15 * 60 * 1000);
                }
            });
            
            // Get date range
            const dates = [...new Set(dataToUse.map(s => s.start.split('T')[0]))].sort();
            if (dates.length === 0) {
                heatmapContainer.innerHTML = '<p style="text-align: center; color: #999;">No data to display</p>';
                return;
            }
            
            const startDate = new Date(dates[0]);
            const endDate = new Date(dates[dates.length - 1]);
            
            // Generate hour headers (starting from 4AM)
            const hoursHtml = '<div class="heatmap-hours">' + 
                Array.from({length: 24}, (_, i) => {
                    const displayHour = (i + 4) % 24;
                    return i % 3 === 0 ? `<div class="heatmap-hour">${displayHour}</div>` : '<div class="heatmap-hour"></div>';
                }).join('') + '</div>';
            
            // Generate heatmap rows
            let heatmapHtml = hoursHtml;
            
            const current = new Date(startDate);
            while (current <= endDate) {
                const dateStr = current.toISOString().split('T')[0];
                const dayLabel = current.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                
                let rowHtml = `<div class="heatmap-row">
                    <div class="heatmap-label">${dayLabel}</div>
                    <div class="heatmap-blocks">`;
                
                for (let i = 0; i < 24; i++) {
                    const hour = (i + 4) % 24; // Start from 4AM
                    for (let minute = 0; minute < 60; minute += 15) {
                        const blockKey = `${dateStr}-${hour}-${minute}`;
                        const intensity = intensityMap[blockKey] || 0;
                        const meetingIntensity = meetingsMap[blockKey] || 0;
                        
                        // Determine block class - meetings take precedence
                        let blockClass = '';
                        if (meetingIntensity > 0) {
                            blockClass = `meeting-${Math.min(Math.ceil(meetingIntensity), 4)}`;
                        } else {
                            const intensityLevel = intensity === 0 ? 0 : Math.min(Math.ceil(intensity / 2), 4);
                            blockClass = `intensity-${intensityLevel}`;
                            // Add alternating hour class for visual distinction (based on display position)
                            blockClass += i % 2 === 0 ? ' even-hour' : ' odd-hour';
                            // Add hour-start marker for the first block of each hour
                            if (minute === 0) {
                                blockClass += ' hour-start';
                            }
                        }
                        
                        // Build detailed tooltip
                        let tooltip = `${dayLabel} ${hour}:${minute.toString().padStart(2, '0')}`;
                        
                        // Check if this block has meetings
                        if (blockMeetings[blockKey]) {
                            tooltip += '\\n\\nMeetings:';
                            blockMeetings[blockKey].forEach(meeting => {
                                tooltip += `\\n• ${meeting.summary} (${Math.round(meeting.totalDuration)}m)`;
                                if (meeting.attendees.length > 0) {
                                    const attendeeNames = meeting.attendees.slice(0, 3).map(a => a.displayName || a.email.split('@')[0]).join(', ');
                                    const moreCount = meeting.attendees.length > 3 ? ` +${meeting.attendees.length - 3} more` : '';
                                    tooltip += `\\n  Attendees: ${attendeeNames}${moreCount}`;
                                }
                                if (meeting.location) {
                                    tooltip += `\\n  Location: ${meeting.location}`;
                                }
                            });
                        }
                        
                        // Check if this block has any sessions
                        if (blockSessions[blockKey]) {
                            const sessionsInBlock = blockSessions[blockKey];
                            
                            // Get unique continuous sessions in this block
                            const uniqueSessionIds = [...new Set(sessionsInBlock.map(s => s.sessionId))];
                            
                            // Show continuous session info
                            if (uniqueSessionIds.length > 0) {
                                tooltip += '\\n\\nSessions:';
                                uniqueSessionIds.forEach(sessionId => {
                                    const contSession = continuousSessions[sessionId];
                                    if (contSession) {
                                        const totalHours = Math.floor(contSession.totalDuration / 60);
                                        const totalMins = Math.round(contSession.totalDuration % 60);
                                        const totalStr = totalHours > 0 ? (totalHours + 'h ' + totalMins + 'm') : (totalMins + 'm');
                                        const blockCount = contSession.blocks.length;
                                        tooltip += '\\n• ' + contSession.repo + ' - ' + totalStr;
                                        if (blockCount > 4) { // Only show block count for longer sessions
                                            tooltip += ' (' + blockCount + ' blocks)';
                                        }
                                    }
                                });
                            }
                        }
                        
                        // Show hour-aggregated data in tooltip
                        const hourKey = `${dateStr}-${hour}`;
                        if (hourSessions[hourKey]) {
                            const sessions = Object.values(hourSessions[hourKey]);
                            tooltip += '\\n\\nHour total:';
                            sessions.forEach(s => {
                                const hours = Math.floor(s.duration / 60);
                                const mins = Math.round(s.duration % 60);
                                const durationStr = hours > 0 ? (hours + 'h ' + mins + 'm') : (mins + 'm');
                                tooltip += '\\n• ' + s.repo + ' (' + durationStr + ')';
                            });
                        } else if (!blockSessions[blockKey]) {
                            tooltip += '\\nNo activity';
                        }
                        
                        rowHtml += `<div class="heatmap-block ${blockClass}" 
                                        title="${tooltip}"></div>`;
                    }
                }
                
                rowHtml += '</div></div>';
                heatmapHtml += rowHtml;
                
                current.setDate(current.getDate() + 1);
            }
            
            // Add legend
            heatmapHtml += `<div class="heatmap-legend">
                <span>Coding:</span>
                <span style="font-size: 0.7em;">Less</span>
                <div class="heatmap-block intensity-0"></div>
                <div class="heatmap-block intensity-1"></div>
                <div class="heatmap-block intensity-2"></div>
                <div class="heatmap-block intensity-3"></div>
                <div class="heatmap-block intensity-4"></div>
                <span style="font-size: 0.7em;">More</span>
                <span style="margin-left: 20px;">Meetings:</span>
                <span style="font-size: 0.7em;">Less</span>
                <div class="heatmap-block meeting-1"></div>
                <div class="heatmap-block meeting-2"></div>
                <div class="heatmap-block meeting-3"></div>
                <div class="heatmap-block meeting-4"></div>
                <span style="font-size: 0.7em;">More</span>
            </div>`;
            
            heatmapContainer.innerHTML = heatmapHtml;
        }
        
        // Call heatmap generation after DOM is ready
        setTimeout(generateHeatmap, 100);
        
        // Create filter buttons
        function createFilterButtons() {
            createButtons('repoFilterButtons', allRepos, activeRepos, updateFilters, repoColors);
            createButtons('projectFilterButtons', allProjects, activeProjects, updateFilters);
            createButtons('sourceFilterButtons', allSources, activeSources, updateFilters);
        }

        function createButtons(containerId, items, activeSet, updateFn, colors = {}) {
            const container = document.getElementById(containerId);
            container.innerHTML = ''; // Clear existing buttons

            const allBtn = document.createElement('button');
            allBtn.className = 'filter-btn active';
            allBtn.textContent = 'All';
            allBtn.onclick = () => {
                if (activeSet.size === items.length) {
                    activeSet.clear();
                } else {
                    items.forEach(item => activeSet.add(item));
                }
                updateFn();
            };
            container.appendChild(allBtn);

            items.forEach(item => {
                const btn = document.createElement('button');
                btn.className = 'filter-btn active';
                btn.textContent = item;
                if (colors[item]) {
                    btn.style.borderColor = colors[item];
                }
                btn.onclick = () => {
                    if (activeSet.has(item)) {
                        activeSet.delete(item);
                    } else {
                        activeSet.add(item);
                    }
                    updateFn();
                };
                container.appendChild(btn);
            });
        }

        // Update all visualizations based on filters
        function updateFilters() {
            updateButtonStates('repoFilterButtons', activeRepos, repoColors);
            updateButtonStates('projectFilterButtons', activeProjects);
            updateButtonStates('sourceFilterButtons', activeSources);
            
            // Redraw all charts with filtered data
            updateCharts();
        }

        function updateButtonStates(containerId, activeSet, colors = {}) {
            const buttons = document.querySelectorAll(`#${containerId} .filter-btn`);
            buttons.forEach((btn, idx) => {
                if (idx === 0) { // All button
                    btn.classList.toggle('active', activeSet.size === (buttons.length - 1));
                } else {
                    const item = btn.textContent;
                    btn.classList.toggle('active', activeSet.has(item));
                    if (activeSet.has(item) && colors[item]) {
                        btn.style.backgroundColor = colors[item];
                        btn.style.color = 'white';
                    } else {
                        btn.style.backgroundColor = 'white';
                        btn.style.color = 'black';
                    }
                }
            });
        }
        
        // Update all charts with filtered data
        function updateCharts() {
            const filteredData = timelineData.filter(s => 
                activeRepos.has(s.repo) &&
                activeProjects.has(s.project) &&
                activeSources.has(s.service)
            );
            
            // Update stats
            const totalHours = filteredData.reduce((sum, s) => sum + s.duration, 0);
            const totalSessions = filteredData.length;
            const repos = new Set(filteredData.map(s => s.repo)).size;
            
            document.querySelector('.stat-value').textContent = totalHours.toFixed(1);
            document.querySelectorAll('.stat-value')[1].textContent = totalSessions;
            document.querySelectorAll('.stat-value')[2].textContent = repos;
            
            // Update daily chart
            const filteredDailyData = {};
            filteredData.forEach(session => {
                const day = session.start.split('T')[0];
                if (!filteredDailyData[day]) filteredDailyData[day] = {};
                if (!filteredDailyData[day][session.repo]) filteredDailyData[day][session.repo] = 0;
                filteredDailyData[day][session.repo] += session.duration;
            });
            
            // Update charts data
            const days = [...new Set(filteredData.map(s => s.start.split('T')[0]))].sort();
            const newDatasets = Array.from(activeRepos).map(repo => ({
                label: repo,
                data: days.map(day => (filteredDailyData[day] && filteredDailyData[day][repo]) || 0),
                backgroundColor: repoColors[repo] || '#95a5a6'
            }));
            
            dailyChart.data.labels = days;
            dailyChart.data.datasets = newDatasets;
            dailyChart.update();
            
            // Update repo chart
            const filteredRepoData = {};
            Array.from(activeRepos).forEach(repo => {
                filteredRepoData[repo] = filteredData
                    .filter(s => s.repo === repo)
                    .reduce((sum, s) => sum + s.duration, 0);
            });
            
            repoChart.data.labels = Object.keys(filteredRepoData);
            repoChart.data.datasets[0].data = Object.values(filteredRepoData);
            repoChart.update();
            
            // Update heatmap
            generateHeatmap(filteredData);
            
            // Update repository summary
            updateRepoSummary(filteredData);
        }
        
        // Create data sources display
        function createSourcesDisplay() {
            const container = document.getElementById('sourcesList');
            let html = '';
            
            Object.entries(sourceStats).forEach(([source, stats]) => {
                html += `
                    <div class="source-item">
                        <span class="source-name">${source}</span>
                        <span class="source-stats">
                            ${stats.duration_hours.toFixed(1)}h • ${stats.sessions} sessions • ${stats.projects} projects
                        </span>
                    </div>
                `;
            });
            
            if (missingSources.length > 0) {
                html += `
                    <div class="warning">
                        ⚠️ No data found from: ${missingSources.join(', ')}
                        <br><small>This may be normal if you don't use these tools.</small>
                    </div>
                `;
            }
            
            container.innerHTML = html;
        }
        
        // Override generateHeatmap to filter data based on active filters
        const originalGenerateHeatmap = generateHeatmap;
        generateHeatmap = function(data) {
            // Filter the data based on active filters
            const filteredData = (data || timelineData).filter(s => 
                activeRepos.has(s.repo) &&
                activeProjects.has(s.project) &&
                activeSources.has(s.service)
            );
            
            // Call the original generateHeatmap with filtered data
            originalGenerateHeatmap(filteredData);
        };
        
        // Update repository summary function
        function updateRepoSummary(data) {
            const dataToUse = data || timelineData;
            const filteredSummary = {};
            
            Array.from(activeRepos).forEach(repo => {
                const repoData = dataToUse.filter(s => s.repo === repo);
                filteredSummary[repo] = {
                    duration_hours: repoData.reduce((sum, s) => sum + s.duration, 0),
                    service: repoData.length,
                    commits_in_window: Math.max(...repoData.map(s => s.commits), 0)
                };
            });
            
            const summaryHtml = Object.entries(filteredSummary).map(([repo, stats]) => {
                const color = repoColors[repo] || '#95a5a6';
                return `
                    <div class="repo-card" style="border-left-color: ${color}">
                        <div class="repo-name">${repo}</div>
                        <div class="repo-stats">
                            ⏱️ ${stats.duration_hours.toFixed(1)} hours<br>
                            📊 ${stats.service} sessions<br>
                            💾 ${stats.commits_in_window} commits
                        </div>
                    </div>
                `;
            }).join('');
            
            document.getElementById('repoSummary').innerHTML = summaryHtml;
        }
        
        // Initialize filter buttons and sources display
        createFilterButtons();
        createSourcesDisplay();
        
        // Initial update of all charts
        updateCharts();
        
        // Repository summary cards
        setTimeout(() => {
            const summaryHtml = Object.entries(repoSummary).map(([repo, stats]) => {
                const color = repoColors[repo] || '#95a5a6';
                return `
                    <div class="repo-card" style="border-left-color: ${color}">
                        <div class="repo-name">${repo}</div>
                        <div class="repo-stats">
                            ⏱️ ${stats.duration_hours.toFixed(1)} hours<br>
                            📊 ${stats.service} sessions<br>
                            💾 ${stats.commits_in_window} commits
                        </div>
                    </div>
                `;
            }).join('');
            
            document.getElementById('repoSummary').innerHTML = summaryHtml;
        }, 100);
    </script>
</body>
</html>'''
    
    # Write to file
    output_file = Path('./data/dashboard.html')
    output_file.write_text(html_template)
    
    print(f"Dashboard generated: {output_file.absolute()}")
    print(f"Open in browser: file://{output_file.absolute()}")

if __name__ == '__main__':
    csv_file = sys.argv[1] if len(sys.argv) > 1 else None
    generate_static_dashboard(csv_file)