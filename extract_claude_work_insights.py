#!/usr/bin/env python3
"""
Extract work insights from Claude JSONL files

This script extracts the most valuable fields from Claude Code JSONL files
to understand what work was being done, focusing on:
- User questions and requests (actual work problems)
- Git context (branches, working directories)  
- Session patterns and complexity
- Time-based work flow
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict, Counter
import re


def extract_text_content(content):
    """Extract text from content field which can be string or array"""
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get('type') == 'text':
                    text_parts.append(item.get('text', ''))
                elif 'content' in item:
                    text_parts.append(str(item['content']))
            else:
                text_parts.append(str(item))
        return ' '.join(text_parts)
    return str(content)


def clean_text_content(text):
    """Clean and summarize text content"""
    # Remove command metadata
    text = re.sub(r'<command-[^>]*>.*?</command-[^>]*>', '', text, flags=re.DOTALL)
    text = re.sub(r'<command-[^>]*>[^<]*', '', text)
    
    # Remove long diffs/code blocks but keep first line for context
    if 'diff --git' in text:
        lines = text.split('\n')
        diff_summary = []
        in_diff = False
        for line in lines:
            if line.startswith('diff --git'):
                in_diff = True
                diff_summary.append(line)
            elif in_diff and (line.startswith('@@') or line.startswith('---') or line.startswith('+++')):
                diff_summary.append(line[:100])  # Truncate long lines
            elif not in_diff:
                diff_summary.append(line)
        text = '\n'.join(diff_summary[:20])  # Limit to first 20 lines
    
    # Truncate very long content but preserve structure
    if len(text) > 500:
        text = text[:500] + "..."
    
    return text.strip()


def extract_work_context(record):
    """Extract key work context from a JSONL record"""
    timestamp = record.get('timestamp', '')
    record_type = record.get('type', '')
    git_branch = record.get('gitBranch', '')
    cwd = record.get('cwd', '')
    session_id = record.get('sessionId', '')
    
    message = record.get('message', {})
    role = message.get('role', '')
    content = message.get('content', '')
    model = message.get('model', '')
    
    # Extract usage stats
    usage = message.get('usage', {})
    input_tokens = usage.get('input_tokens', 0)
    output_tokens = usage.get('output_tokens', 0)
    
    # Clean and extract text
    text_content = extract_text_content(content)
    clean_text = clean_text_content(text_content)
    
    # Extract tool usage
    tool_use = False
    tool_names = []
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get('type') == 'tool_use':
                tool_use = True
                tool_names.append(item.get('name', 'unknown'))
    
    return {
        'timestamp': timestamp,
        'type': record_type,
        'role': role,
        'git_branch': git_branch,
        'cwd': cwd,
        'session_id': session_id,
        'model': model,
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
        'tool_use': tool_use,
        'tool_names': tool_names,
        'text_content': clean_text,
        'content_length': len(text_content)
    }


def analyze_work_session(records):
    """Analyze a session to understand what work was done"""
    user_requests = []
    assistant_responses = []
    tools_used = Counter()
    total_tokens = 0
    
    for record in records:
        if record['role'] == 'user' and record['type'] == 'user':
            # Filter out command outputs and focus on actual user requests
            text = record['text_content']
            if not any(skip in text.lower() for skip in ['<command-', 'git status', 'git diff', 'running…']):
                user_requests.append(text[:200])  # First 200 chars
        
        elif record['role'] == 'assistant':
            assistant_responses.append(record['text_content'][:200])
            
        if record['tool_names']:
            for tool in record['tool_names']:
                tools_used[tool] += 1
                
        total_tokens += record['input_tokens'] + record['output_tokens']
    
    return {
        'user_requests': user_requests,
        'assistant_responses': assistant_responses,
        'tools_used': dict(tools_used),
        'total_tokens': total_tokens,
        'interaction_count': len(records)
    }


def extract_daily_work_summary(jsonl_file, target_date='2025-07-24'):
    """Extract work summary for a specific date"""
    file_path = Path(jsonl_file)
    if not file_path.exists():
        print(f"File not found: {jsonl_file}")
        return None
    
    print(f"Processing: {file_path.name}")
    
    daily_records = []
    sessions = defaultdict(list)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    record = json.loads(line.strip())
                    context = extract_work_context(record)
                    
                    # Filter by target date
                    if context['timestamp'].startswith(target_date):
                        daily_records.append(context)
                        sessions[context['session_id']].append(context)
                        
                except json.JSONDecodeError as e:
                    print(f"JSON error at line {line_num}: {e}")
                    continue
                except Exception as e:
                    print(f"Processing error at line {line_num}: {e}")
                    continue
                    
    except Exception as e:
        print(f"File reading error: {e}")
        return None
    
    if not daily_records:
        print(f"No records found for {target_date}")
        return None
    
    # Analyze sessions
    session_summaries = {}
    for session_id, records in sessions.items():
        session_summaries[session_id] = analyze_work_session(records)
    
    # Extract key insights
    work_summary = {
        'date': target_date,
        'file': file_path.name,
        'total_records': len(daily_records),
        'session_count': len(sessions),
        'git_branches': list(set(r['git_branch'] for r in daily_records if r['git_branch'])),
        'working_directories': list(set(r['cwd'] for r in daily_records if r['cwd'])),
        'models_used': list(set(r['model'] for r in daily_records if r['model'])),
        'sessions': session_summaries
    }
    
    return work_summary


def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_claude_work_insights.py <jsonl_file> [date]")
        print("Example: python extract_claude_work_insights.py file.jsonl 2025-07-24")
        sys.exit(1)
    
    jsonl_file = sys.argv[1]
    target_date = sys.argv[2] if len(sys.argv) > 2 else '2025-07-24'
    
    summary = extract_daily_work_summary(jsonl_file, target_date)
    
    if summary:
        print("\n" + "="*60)
        print(f"WORK SUMMARY: {summary['date']}")
        print("="*60)
        
        print(f"\nFile: {summary['file']}")
        print(f"Records: {summary['total_records']}")
        print(f"Sessions: {summary['session_count']}")
        print(f"Git Branches: {', '.join(summary['git_branches'])}")
        print(f"Working Dirs: {', '.join(summary['working_directories'])}")
        print(f"Models Used: {', '.join(summary['models_used'])}")
        
        print(f"\nSESSION DETAILS:")
        print("-" * 40)
        
        for session_id, session in summary['sessions'].items():
            print(f"\nSession: {session_id[:8]}...")
            print(f"Interactions: {session['interaction_count']}")
            print(f"Tokens: {session['total_tokens']:,}")
            print(f"Tools: {', '.join(session['tools_used'].keys()) if session['tools_used'] else 'None'}")
            
            if session['user_requests']:
                print("Key Requests:")
                for i, req in enumerate(session['user_requests'][:3], 1):
                    print(f"  {i}. {req}")
            
            if session['assistant_responses']:
                print("Key Responses:")
                for i, resp in enumerate(session['assistant_responses'][:2], 1):
                    print(f"  {i}. {resp}")
            print("-" * 40)


if __name__ == "__main__":
    main()