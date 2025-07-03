#!/usr/bin/env python3
"""
Comprehensive extraction of Cursor chat data from multiple sources
"""

import os
import json
import sqlite3
import struct
from datetime import datetime
import re
from pathlib import Path
import glob

def parse_timestamp(timestamp):
    """Convert various timestamp formats to datetime"""
    if isinstance(timestamp, (int, float)):
        # Try as milliseconds first (JavaScript timestamp)
        if timestamp > 1e12:
            return datetime.fromtimestamp(timestamp / 1000)
        # Otherwise assume seconds
        return datetime.fromtimestamp(timestamp)
    elif isinstance(timestamp, str):
        # Try parsing ISO format
        try:
            return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except:
            pass
        # Try parsing various date formats
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y/%m/%d %H:%M:%S"
        ]
        for fmt in formats:
            try:
                return datetime.strptime(timestamp, fmt)
            except:
                pass
    return None

def is_in_date_range(date_obj, start_date, end_date):
    """Check if date is within specified range"""
    if not date_obj:
        return False
    return start_date <= date_obj <= end_date

def analyze_sqlite_db(db_path, start_date, end_date):
    """Analyze SQLite database for chat data"""
    results = []
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print(f"\nAnalyzing SQLite DB: {db_path}")
        print(f"Tables found: {[t[0] for t in tables]}")
        
        for table in tables:
            table_name = table[0]
            
            # Get all data from table
            try:
                cursor.execute(f"SELECT * FROM {table_name}")
                rows = cursor.fetchall()
                
                # Get column names
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [col[1] for col in cursor.fetchall()]
                
                print(f"\nTable {table_name}: {len(rows)} rows, columns: {columns}")
                
                # Look for chat-related data
                for row in rows:
                    row_dict = dict(zip(columns, row))
                    
                    # Check if any column contains chat-related keywords
                    has_chat_data = False
                    for key, value in row_dict.items():
                        if value and isinstance(value, str):
                            if any(keyword in str(value).lower() for keyword in 
                                  ['chat', 'message', 'conversation', 'prompt', 'response', 'claude', 'gpt', 'ai']):
                                has_chat_data = True
                                break
                    
                    # Check for timestamps
                    timestamp_found = None
                    for key, value in row_dict.items():
                        if 'time' in key.lower() or 'date' in key.lower():
                            date_obj = parse_timestamp(value)
                            if date_obj and is_in_date_range(date_obj, start_date, end_date):
                                timestamp_found = date_obj
                                break
                    
                    if has_chat_data or timestamp_found:
                        results.append({
                            'db': db_path,
                            'table': table_name,
                            'timestamp': timestamp_found,
                            'data': row_dict
                        })
                        
            except Exception as e:
                print(f"Error reading table {table_name}: {e}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error analyzing SQLite DB {db_path}: {e}")
    
    return results

def analyze_log_files(log_dir, start_date, end_date):
    """Analyze log files for chat data"""
    results = []
    
    # Look for log files from June 19-22
    date_patterns = ['20250619', '20250620', '20250621', '20250622', 
                     '2025-06-19', '2025-06-20', '2025-06-21', '2025-06-22']
    
    for pattern in date_patterns:
        log_paths = glob.glob(f"{log_dir}/**/*{pattern}*", recursive=True)
        
        for log_path in log_paths:
            if os.path.isfile(log_path):
                try:
                    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                    # Look for chat-related content
                    if any(keyword in content.lower() for keyword in 
                          ['chat', 'message', 'conversation', 'prompt', 'response', 'claude', 'gpt']):
                        
                        # Extract relevant lines
                        lines = content.split('\n')
                        relevant_lines = []
                        
                        for line in lines:
                            if any(keyword in line.lower() for keyword in 
                                  ['chat', 'message', 'conversation', 'prompt', 'response', 'claude', 'gpt']):
                                relevant_lines.append(line)
                        
                        if relevant_lines:
                            results.append({
                                'file': log_path,
                                'lines': relevant_lines[:50]  # First 50 relevant lines
                            })
                            
                except Exception as e:
                    print(f"Error reading log file {log_path}: {e}")
    
    return results

def extract_leveldb_data(db_path):
    """Try to extract data from LevelDB using python-leveldb if available"""
    results = []
    
    try:
        import plyvel
        db = plyvel.DB(db_path, create_if_missing=False)
        
        print(f"\nSuccessfully opened LevelDB at {db_path}")
        
        # Iterate through all key-value pairs
        for key, value in db:
            try:
                # Try to decode as JSON
                if value:
                    try:
                        json_data = json.loads(value.decode('utf-8', errors='ignore'))
                        results.append({
                            'key': key.decode('utf-8', errors='ignore'),
                            'value': json_data
                        })
                    except:
                        # If not JSON, store as string
                        value_str = value.decode('utf-8', errors='ignore')
                        if len(value_str) > 10:  # Only store meaningful strings
                            results.append({
                                'key': key.decode('utf-8', errors='ignore'),
                                'value': value_str
                            })
            except:
                pass
        
        db.close()
        
    except ImportError:
        print("plyvel not installed. Trying alternative method...")
        
        # Alternative: read raw log files
        log_file = os.path.join(db_path, '000003.log')
        if os.path.exists(log_file):
            with open(log_file, 'rb') as f:
                data = f.read()
                
            # Look for JSON patterns in the raw data
            text = data.decode('utf-8', errors='ignore')
            
            # Find potential JSON objects
            json_matches = re.finditer(r'\{[^{}]*\}', text)
            for match in json_matches:
                try:
                    json_obj = json.loads(match.group())
                    results.append({'raw_json': json_obj})
                except:
                    pass
    
    except Exception as e:
        print(f"Error with LevelDB extraction: {e}")
    
    return results

def main():
    cursor_dir = "/home/rolf/.config/Cursor"
    
    # Define our date range (June 19-22, 2024)
    # Note: Using 2025 based on the log file dates found
    start_date = datetime(2025, 6, 19)
    end_date = datetime(2025, 6, 22, 23, 59, 59)
    
    print(f"Extracting Cursor chat data")
    print(f"Looking for data from {start_date} to {end_date}")
    print("=" * 60)
    
    all_results = {
        'sqlite_data': [],
        'log_data': [],
        'leveldb_data': []
    }
    
    # 1. Analyze SQLite databases
    print("\n1. ANALYZING SQLITE DATABASES")
    print("-" * 60)
    
    db_paths = glob.glob(f"{cursor_dir}/**/state.vscdb", recursive=True)
    for db_path in db_paths:
        sqlite_results = analyze_sqlite_db(db_path, start_date, end_date)
        all_results['sqlite_data'].extend(sqlite_results)
    
    # 2. Analyze log files
    print("\n\n2. ANALYZING LOG FILES")
    print("-" * 60)
    
    log_results = analyze_log_files(cursor_dir, start_date, end_date)
    all_results['log_data'] = log_results
    
    # 3. Try LevelDB extraction
    print("\n\n3. ANALYZING LEVELDB")
    print("-" * 60)
    
    leveldb_path = os.path.join(cursor_dir, "Local Storage", "leveldb")
    leveldb_results = extract_leveldb_data(leveldb_path)
    all_results['leveldb_data'] = leveldb_results
    
    # Print summary
    print("\n\nSUMMARY OF FINDINGS")
    print("=" * 60)
    print(f"SQLite entries found: {len(all_results['sqlite_data'])}")
    print(f"Log files with chat data: {len(all_results['log_data'])}")
    print(f"LevelDB entries found: {len(all_results['leveldb_data'])}")
    
    # Save detailed results
    output_file = "/home/rolf/cursor_chat_comprehensive_results.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nDetailed results saved to: {output_file}")
    
    # Print some sample results
    if all_results['sqlite_data']:
        print("\n\nSAMPLE SQLITE DATA:")
        print("-" * 60)
        for item in all_results['sqlite_data'][:3]:
            print(f"\nDatabase: {item['db']}")
            print(f"Table: {item['table']}")
            print(f"Timestamp: {item['timestamp']}")
            print(f"Data: {json.dumps(item['data'], indent=2)[:500]}...")
    
    if all_results['log_data']:
        print("\n\nSAMPLE LOG DATA:")
        print("-" * 60)
        for item in all_results['log_data'][:3]:
            print(f"\nFile: {item['file']}")
            print("Relevant lines:")
            for line in item['lines'][:5]:
                print(f"  {line[:150]}...")

if __name__ == "__main__":
    main()