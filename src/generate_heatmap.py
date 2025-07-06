#!/usr/bin/env python3
"""Generate an ASCII heatmap of coding activity"""

import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import sys
from calendar_integration import CalendarIntegration

def generate_ascii_heatmap(csv_file=None, include_meetings=None):
    """Generate a GitHub-style ASCII heatmap"""
    
    # Load config to check if meetings should be included
    config = {}
    config_path = Path('./config/config.yaml')
    if config_path.exists():
        try:
            import yaml
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f) or {}
        except:
            pass
    
    # Use config setting if include_meetings not explicitly set
    if include_meetings is None:
        include_meetings = config.get('calendar', {}).get('display', {}).get('show_in_ascii', True)
    
    # Find the latest CSV if not specified
    data_dir = Path('./data')
    if csv_file is None:
        csv_files = list(data_dir.glob('time_tracking_*.csv'))
        if not csv_files:
            print("No time tracking data found. Run time tracker first.")
            return
        csv_file = max(csv_files, key=lambda f: f.stat().st_mtime)
    
    # Load data
    df = pd.read_csv(csv_file)
    df['start'] = pd.to_datetime(df['start'], format='ISO8601', utc=True)
    df['end'] = pd.to_datetime(df['end'], format='ISO8601', utc=True)
    
    # Create 15-minute blocks for the entire date range
    start_date = df['start'].min().normalize()
    end_date = df['end'].max().normalize() + timedelta(days=1)
    
    # Generate all 15-minute blocks
    time_blocks = pd.date_range(start=start_date, end=end_date, freq='15min')
    
    # Count activity intensity for each block
    intensity_map = {}
    
    for _, session in df.iterrows():
        # Find all 15-minute blocks this session overlaps
        session_start = session['start']
        session_end = session['end']
        
        # Find blocks within this session
        block_start = session_start.floor('15min')
        block_end = session_end.ceil('15min')
        
        current_block = block_start
        while current_block < block_end:
            # Calculate overlap percentage
            block_end_time = current_block + timedelta(minutes=15)
            overlap_start = max(current_block, session_start)
            overlap_end = min(block_end_time, session_end)
            
            if overlap_end > overlap_start:
                overlap_minutes = (overlap_end - overlap_start).total_seconds() / 60
                intensity = overlap_minutes / 15.0  # Percentage of block
                
                key = (current_block.date(), current_block.hour, current_block.minute)
                intensity_map[key] = intensity_map.get(key, 0) + intensity
                
            current_block += timedelta(minutes=15)
    
    # Fetch calendar meetings if enabled
    meetings_map = {}
    if include_meetings:
        try:
            cal = CalendarIntegration()
            if cal.authenticate():
                meetings = cal.get_meetings(start_date, end_date)
                
                # Process meetings into 15-minute blocks
                for meeting in meetings:
                    meeting_start = pd.to_datetime(meeting['start'])
                    meeting_end = pd.to_datetime(meeting['end'])
                    
                    # Find blocks within this meeting
                    block_start = meeting_start.floor('15min')
                    block_end = meeting_end.ceil('15min')
                    
                    current_block = block_start
                    while current_block < block_end:
                        block_end_time = current_block + timedelta(minutes=15)
                        overlap_start = max(current_block, meeting_start)
                        overlap_end = min(block_end_time, meeting_end)
                        
                        if overlap_end > overlap_start:
                            overlap_minutes = (overlap_end - overlap_start).total_seconds() / 60
                            intensity = overlap_minutes / 15.0
                            
                            key = (current_block.date(), current_block.hour, current_block.minute)
                            meetings_map[key] = meetings_map.get(key, 0) + intensity
                            
                        current_block += timedelta(minutes=15)
                        
                print(f"Loaded {len(meetings)} meetings")
        except Exception as e:
            print(f"Warning: Could not load calendar meetings: {e}")
            include_meetings = False
    
    # Generate the heatmap
    print("\n" + "=" * 80)
    print("CODING ACTIVITY HEATMAP (15-minute blocks)")
    print("=" * 80)
    legend = "\nIntensity: . ∙ (none) ░ (light) ▒ (medium) ▓ (heavy) █ (intense)"
    legend += "\nHours:     . (even hours) ∙ (odd hours) - alternating background for hour boundaries"
    if include_meetings and meetings_map:
        legend += "\nMeetings:  ◊ (light) ◈ (medium) ◆ (heavy) ♦ (full)"
    print(legend)
    # Create hour header with proper alignment
    # Each hour has 4 blocks, so 3 hours = 12 blocks = 12 characters
    print("\nHour  00         03         06         09         12         15         18         21         24")
    print("      |          |          |          |          |          |          |          |          |")
    
    # Group by date
    current_date = start_date.date()
    while current_date <= end_date.date():
        # Skip if no activity on this day
        day_has_activity = any(k[0] == current_date for k in intensity_map.keys())
        if not day_has_activity and current_date != datetime.now().date():
            current_date += timedelta(days=1)
            continue
            
        print(f"\n{current_date.strftime('%m/%d')} ", end='')
        
        # Print each hour's 4 blocks (15-min each)
        for hour in range(24):
            for quarter in [0, 15, 30, 45]:
                key = (current_date, hour, quarter)
                intensity = intensity_map.get(key, 0)
                meeting_intensity = meetings_map.get(key, 0)
                
                # If there's a meeting, show meeting character instead
                if meeting_intensity > 0:
                    if meeting_intensity < 0.25:
                        char = '◊'
                    elif meeting_intensity < 0.5:
                        char = '◈'
                    elif meeting_intensity < 0.75:
                        char = '◆'
                    else:
                        char = '♦'
                else:
                    # Convert coding intensity to character
                    # Use alternating background characters for hour boundaries
                    if intensity == 0:
                        # Alternate empty character based on hour (even/odd)
                        char = '.' if hour % 2 == 0 else '∙'
                    elif intensity < 0.25:
                        char = '░'
                    elif intensity < 0.5:
                        char = '▒'
                    elif intensity < 0.75:
                        char = '▓'
                    else:
                        char = '█'
                    
                print(char, end='')
                
        # Add daily summary
        day_total = sum(v for k, v in intensity_map.items() if k[0] == current_date)
        hours = day_total * 0.25  # Convert 15-min blocks to hours
        if hours > 0:
            print(f"  {hours:5.1f}h", end='')
            
        current_date += timedelta(days=1)
    
    # Print summary statistics
    print("\n\n" + "-" * 80)
    total_blocks = len([v for v in intensity_map.values() if v > 0])
    total_hours = sum(intensity_map.values()) * 0.25
    
    print(f"Total: {total_hours:.1f} hours across {total_blocks} active 15-minute blocks")
    
    # Most active times
    print("\nMost active times:")
    sorted_times = sorted(intensity_map.items(), key=lambda x: x[1], reverse=True)[:5]
    for (date, hour, minute), intensity in sorted_times:
        time_str = f"{date} {hour:02d}:{minute:02d}"
        print(f"  {time_str}: {'█' * int(intensity * 4)} ({intensity:.1f}x)")
    
    # Activity by hour of day
    print("\nActivity by hour of day:")
    hour_totals = {}
    for (date, hour, minute), intensity in intensity_map.items():
        hour_totals[hour] = hour_totals.get(hour, 0) + intensity
        
    print("Hour: ", end='')
    for h in range(24):
        print(f"{h:2d} ", end='')
    print("\nWork: ", end='')
    
    max_hour = max(hour_totals.values()) if hour_totals else 1
    for h in range(24):
        total = hour_totals.get(h, 0)
        bars = int((total / max_hour) * 3)
        char = [' ', '▁', '▄', '█'][min(bars, 3)]
        print(f" {char} ", end='')
    print()

if __name__ == '__main__':
    csv_file = None
    include_meetings = True
    
    # Parse command line arguments
    args = sys.argv[1:]
    for arg in args:
        if arg == '--no-meetings':
            include_meetings = False
        elif not arg.startswith('--'):
            csv_file = arg
    
    generate_ascii_heatmap(csv_file, include_meetings)