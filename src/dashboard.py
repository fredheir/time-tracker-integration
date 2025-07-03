#!/usr/bin/env python3
"""Web dashboard for time tracking visualization"""

import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import plotly.graph_objects as go
import plotly.express as px
from flask import Flask, render_template, jsonify, request
import numpy as np

app = Flask(__name__, template_folder='../templates', static_folder='../static')

class DashboardData:
    """Load and process time tracking data for visualization"""
    
    def __init__(self):
        self.data_dir = Path('./data')
        self.sessions_df = None
        self.load_latest_data()
        
    def load_latest_data(self):
        """Load the most recent time tracking data"""
        csv_files = list(self.data_dir.glob('time_tracking_*.csv'))
        if not csv_files:
            self.sessions_df = pd.DataFrame()
            return
            
        latest_file = max(csv_files, key=lambda f: f.stat().st_mtime)
        self.sessions_df = pd.read_csv(latest_file)
        self.sessions_df['start'] = pd.to_datetime(self.sessions_df['start'])
        self.sessions_df['end'] = pd.to_datetime(self.sessions_df['end'])
        
    def get_timeline_data(self):
        """Prepare data for timeline visualization"""
        if self.sessions_df.empty:
            return []
            
        timeline_data = []
        for _, session in self.sessions_df.iterrows():
            timeline_data.append({
                'start': session['start'].isoformat(),
                'end': session['end'].isoformat(),
                'repo': session.get('identified_repo', 'Unknown'),
                'service': session.get('service', 'Unknown'),
                'duration': session.get('duration_hours', 0),
                'commits': session.get('commits_in_window', 0)
            })
        return timeline_data
        
    def get_heatmap_data(self):
        """Prepare data for activity heatmap"""
        if self.sessions_df.empty:
            return {'z': [], 'x': [], 'y': []}
            
        # Create hourly bins for each day
        df = self.sessions_df.copy()
        df['date'] = df['start'].dt.date
        df['hour'] = df['start'].dt.hour
        
        # Calculate intensity (sessions per hour)
        heatmap = df.groupby(['date', 'hour']).size().reset_index(name='intensity')
        
        # Create full grid (all hours for all days)
        dates = pd.date_range(df['date'].min(), df['date'].max(), freq='D').date
        hours = range(24)
        
        full_grid = pd.DataFrame(
            [(d, h) for d in dates for h in hours],
            columns=['date', 'hour']
        )
        
        heatmap = full_grid.merge(heatmap, on=['date', 'hour'], how='left')
        heatmap['intensity'] = heatmap['intensity'].fillna(0)
        
        # Reshape for heatmap
        pivot = heatmap.pivot(index='hour', columns='date', values='intensity')
        
        return {
            'z': pivot.values.tolist(),
            'x': [str(d) for d in pivot.columns],
            'y': [f"{h:02d}:00" for h in pivot.index]
        }
        
    def get_repo_summary(self):
        """Get summary statistics by repository"""
        if self.sessions_df.empty:
            return []
            
        summary = self.sessions_df.groupby('identified_repo').agg({
            'duration_hours': 'sum',
            'service': 'count',
            'commits_in_window': 'max'
        }).reset_index()
        
        summary.columns = ['repo', 'total_hours', 'sessions', 'commits']
        summary = summary.sort_values('total_hours', ascending=False)
        
        return summary.to_dict('records')
        
    def get_daily_summary(self):
        """Get daily activity summary"""
        if self.sessions_df.empty:
            return []
            
        df = self.sessions_df.copy()
        df['date'] = df['start'].dt.date
        
        daily = df.groupby('date').agg({
            'duration_hours': 'sum',
            'service': 'count'
        }).reset_index()
        
        daily.columns = ['date', 'hours', 'sessions']
        daily['date'] = daily['date'].astype(str)
        
        return daily.to_dict('records')

dashboard_data = DashboardData()

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/timeline')
def api_timeline():
    """API endpoint for timeline data"""
    return jsonify(dashboard_data.get_timeline_data())

@app.route('/api/heatmap')
def api_heatmap():
    """API endpoint for heatmap data"""
    return jsonify(dashboard_data.get_heatmap_data())

@app.route('/api/summary/repos')
def api_repo_summary():
    """API endpoint for repository summary"""
    return jsonify(dashboard_data.get_repo_summary())

@app.route('/api/summary/daily')
def api_daily_summary():
    """API endpoint for daily summary"""
    return jsonify(dashboard_data.get_daily_summary())

@app.route('/api/refresh')
def api_refresh():
    """Refresh data from disk"""
    dashboard_data.load_latest_data()
    return jsonify({'status': 'refreshed'})

if __name__ == '__main__':
    print("Starting Time Tracker Dashboard...")
    print("Open http://localhost:5000 in your browser")
    app.run(debug=True, port=5000)