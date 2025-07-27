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
        'content_length': len(text_content),
        'raw_content': content  # Keep raw content for deeper analysis
    }


def analyze_work_session(records):
    """Analyze a session to understand what work was done"""
    user_requests = []
    assistant_responses = []
    technical_work = []
    file_modifications = []
    tools_used = Counter()
    total_tokens = 0
    
    for record in records:
        if record['role'] == 'user' and record['type'] == 'user':
            # Filter out command outputs and focus on actual user requests
            text = record['text_content']
            # More specific filtering to get actual user questions/requests
            if (text and len(text.strip()) > 10 and 
                not any(skip in text.lower() for skip in [
                    '<command-', 'git status', 'git diff', 'running…', 
                    '<local-command-', 'caveat: the messages below',
                    '<system-reminder>'
                ])):
                user_requests.append({
                    'timestamp': record['timestamp'],
                    'text': text[:500],  # Increase to 500 chars for more context
                    'full_text': text  # Keep full text for detailed analysis
                })
        
        elif record['role'] == 'assistant':
            text = record['text_content']
            assistant_responses.append({
                'timestamp': record['timestamp'],
                'text': text[:500],
                'full_text': text,
                'tools': record['tool_names']
            })
            
            # Extract technical work mentions
            if any(keyword in text.lower() for keyword in [
                'implement', 'create', 'modify', 'fix', 'update', 'add',
                'file', 'function', 'class', 'method', 'variable',
                'telegram', 'monitoring', 'feature', 'bug', 'issue'
            ]):
                technical_work.append({
                    'timestamp': record['timestamp'],
                    'work': text[:300],
                    'tools': record['tool_names']
                })
            
            # Extract file modification mentions
            if any(pattern in text.lower() for pattern in [
                '.py', '.js', '.ts', '.md', '.json', '.yaml', '.yml',
                'edit', 'write', 'create file', 'modify file'
            ]):
                file_modifications.append({
                    'timestamp': record['timestamp'],
                    'modification': text[:400],
                    'tools': record['tool_names']
                })
            
        if record['tool_names']:
            for tool in record['tool_names']:
                tools_used[tool] += 1
                
        total_tokens += record['input_tokens'] + record['output_tokens']
    
    # Extract structured data using the new methods
    files_modified = extract_file_changes(records)
    code_blocks = extract_code_blocks(records)
    commands_run = extract_bash_commands(records)
    errors_encountered = extract_errors(records)
    
    session_data = {
        'user_requests': user_requests,
        'assistant_responses': assistant_responses,
        'technical_work': technical_work,
        'file_modifications': file_modifications,
        'tools_used': dict(tools_used),
        'total_tokens': total_tokens,
        'interaction_count': len(records),
        # New structured data
        'files_modified': files_modified,
        'code_blocks': code_blocks,
        'commands_run': commands_run,
        'errors_encountered': errors_encountered
    }
    
    # Infer deliverables from all the extracted data
    session_data['deliverables'] = infer_deliverables(session_data)
    
    return session_data


def extract_file_changes(session_records):
    """Extract file modifications from session records"""
    file_changes = []
    
    for record in session_records:
        if record['role'] == 'assistant' and record['raw_content']:
            content = record['raw_content']
            
            # Look for Edit/Write/MultiEdit tool usage
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get('type') == 'tool_use':
                        tool_name = item.get('name', '')
                        if tool_name in ['Edit', 'Write', 'MultiEdit']:
                            params = item.get('input', {})
                            file_changes.append({
                                'timestamp': record['timestamp'],
                                'tool': tool_name,
                                'file_path': params.get('file_path', 'unknown'),
                                'action': 'modified' if tool_name == 'Edit' else 'created',
                                'details': params
                            })
            
            # Also look for file mentions in text
            text = record['text_content']
            file_patterns = re.findall(r'(?:created?|modified?|updated?|wrote|edit(?:ed)?)\s+(?:file\s+)?([/\w\-_\.]+\.\w+)', text, re.IGNORECASE)
            for file_path in file_patterns:
                if file_path not in [fc['file_path'] for fc in file_changes]:
                    file_changes.append({
                        'timestamp': record['timestamp'],
                        'tool': 'mentioned',
                        'file_path': file_path,
                        'action': 'referenced',
                        'details': {}
                    })
    
    return file_changes


def extract_code_blocks(session_records):
    """Extract code blocks from session records"""
    code_blocks = []
    
    for record in session_records:
        if record['text_content']:
            # Extract markdown code blocks
            code_pattern = r'```(\w*)\n(.*?)```'
            matches = re.findall(code_pattern, record['text_content'], re.DOTALL)
            
            for lang, code in matches:
                if code.strip():
                    code_blocks.append({
                        'timestamp': record['timestamp'],
                        'language': lang or 'unknown',
                        'code': code.strip()[:500],  # First 500 chars
                        'full_code': code.strip(),
                        'role': record['role']
                    })
    
    return code_blocks


def extract_bash_commands(session_records):
    """Extract bash commands executed during the session"""
    commands = []
    
    for record in session_records:
        if record['tool_names'] and 'Bash' in record['tool_names']:
            # Extract from tool use
            if isinstance(record['raw_content'], list):
                for item in record['raw_content']:
                    if isinstance(item, dict) and item.get('name') == 'Bash':
                        params = item.get('input', {})
                        commands.append({
                            'timestamp': record['timestamp'],
                            'command': params.get('command', 'unknown'),
                            'description': params.get('description', ''),
                            'timeout': params.get('timeout', 120000)
                        })
    
    return commands


def extract_errors(session_records):
    """Extract errors and issues encountered during the session"""
    errors = []
    
    error_patterns = [
        r'(?:error|exception|traceback|failed?):\s*(.+)',
        r'(?:command not found|permission denied|no such file)',
        r'(?:TypeError|ValueError|AttributeError|KeyError|ImportError)',
        r'(?:SyntaxError|IndentationError|NameError)',
        r'(?:ConnectionError|TimeoutError|HTTPError)'
    ]
    
    for record in session_records:
        text = record['text_content'].lower()
        
        for pattern in error_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                errors.append({
                    'timestamp': record['timestamp'],
                    'error': match if isinstance(match, str) else match[0],
                    'context': text[:200],
                    'role': record['role']
                })
    
    return errors


def infer_deliverables(session_data):
    """Infer concrete deliverables from session data"""
    deliverables = []
    
    # Files created/modified
    for fc in session_data.get('files_modified', []):
        if fc['action'] in ['created', 'modified']:
            deliverables.append({
                'type': 'file',
                'name': fc['file_path'],
                'action': fc['action']
            })
    
    # Features implemented (from technical work)
    feature_patterns = [
        r'(?:implemented?|created?|added?|built)\s+(?:new\s+)?(\w+\s+\w+)',
        r'(?:feature|functionality|module|component):\s*([^\.]+)',
        r'PR\s*#?(\d+)',
        r'(?:pull request|merge request)\s+(?:created|opened|submitted)'
    ]
    
    tech_work = session_data.get('technical_work', [])
    for work in tech_work:
        text = work.get('work', '')
        for pattern in feature_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                deliverables.append({
                    'type': 'feature',
                    'name': match if isinstance(match, str) else match[0],
                    'action': 'implemented'
                })
    
    # Commands that suggest deliverables
    for cmd in session_data.get('commands_run', []):
        command = cmd.get('command', '')
        if 'git commit' in command:
            deliverables.append({
                'type': 'commit',
                'name': cmd.get('description', 'Code commit'),
                'action': 'committed'
            })
        elif 'git push' in command or 'gh pr create' in command:
            deliverables.append({
                'type': 'pr',
                'name': cmd.get('description', 'Pull request'),
                'action': 'created'
            })
    
    return deliverables


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
                print(f"\nUser Requests ({len(session['user_requests'])}):")
                for i, req in enumerate(session['user_requests'][:5], 1):
                    timestamp = req['timestamp'][:19] if req['timestamp'] else 'Unknown'
                    print(f"  {i}. [{timestamp}] {req['text']}")
            
            if session['technical_work']:
                print(f"\nTechnical Work ({len(session['technical_work'])}):")
                for i, work in enumerate(session['technical_work'][:10], 1):
                    timestamp = work['timestamp'][:19] if work['timestamp'] else 'Unknown'
                    tools = f" (Tools: {', '.join(work['tools'])})" if work['tools'] else ""
                    print(f"  {i}. [{timestamp}] {work['work']}{tools}")
            
            if session['file_modifications']:
                print(f"\nFile Modifications ({len(session['file_modifications'])}):")
                for i, mod in enumerate(session['file_modifications'][:10], 1):
                    timestamp = mod['timestamp'][:19] if mod['timestamp'] else 'Unknown'
                    tools = f" (Tools: {', '.join(mod['tools'])})" if mod['tools'] else ""
                    print(f"  {i}. [{timestamp}] {mod['modification']}{tools}")
            
            # Display new structured data
            if session.get('files_modified'):
                print(f"\nFiles Changed ({len(session['files_modified'])}):")
                for i, fc in enumerate(session['files_modified'][:5], 1):
                    print(f"  {i}. {fc['action']}: {fc['file_path']} (via {fc['tool']})")
            
            if session.get('commands_run'):
                print(f"\nCommands Executed ({len(session['commands_run'])}):")
                for i, cmd in enumerate(session['commands_run'][:5], 1):
                    print(f"  {i}. {cmd['command'][:80]}{'...' if len(cmd['command']) > 80 else ''}")
                    if cmd['description']:
                        print(f"     → {cmd['description']}")
            
            if session.get('errors_encountered'):
                print(f"\nErrors Encountered ({len(session['errors_encountered'])}):")
                for i, err in enumerate(session['errors_encountered'][:3], 1):
                    print(f"  {i}. {err['error'][:100]}{'...' if len(err['error']) > 100 else ''}")
            
            if session.get('deliverables'):
                print(f"\nDeliverables ({len(session['deliverables'])}):")
                for i, dlv in enumerate(session['deliverables'][:5], 1):
                    print(f"  {i}. [{dlv['type']}] {dlv['action']}: {dlv['name']}")
            
            print("-" * 40)


if __name__ == "__main__":
    main()