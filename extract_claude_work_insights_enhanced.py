#!/usr/bin/env python3
"""
Enhanced Claude Work Insights Extractor
Extracts detailed, deliverable-focused descriptions from Claude Code sessions
"""

import json
import re
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Any, Tuple


def extract_deliverables(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract concrete deliverables from Claude sessions.
    Returns descriptions ready for time tracking.
    """
    deliverables = []
    
    # Pattern matchers for different types of work
    patterns = {
        'feature_impl': {
            'patterns': [
                r'implement(?:ed)?\s+(.+?)(?:\s+for\s+(.+?))?(?:\.|,|$)',
                r'add(?:ed)?\s+(.+?)\s+(?:feature|functionality|support)',
                r'creat(?:ed|ing)?\s+(.+?)\s+(?:component|system|module)',
                r'built\s+(.+?)\s+(?:integration|tool|utility)'
            ],
            'template': "Implemented {}"
        },
        'bug_fix': {
            'patterns': [
                r'fix(?:ed)?\s+(.+?)\s+(?:bug|issue|error|problem)',
                r'resolv(?:ed|ing)?\s+(.+?)\s+(?:error|issue)',
                r'(?:fixed|resolved)\s+(.+?)\s+in\s+(.+)',
                r'(?:TypeError|ValueError|AttributeError|KeyError).*?in\s+(.+)'
            ],
            'template': "Fixed {}"
        },
        'refactor': {
            'patterns': [
                r'refactor(?:ed|ing)?\s+(.+)',
                r'optimiz(?:ed|ing)?\s+(.+)',
                r'improv(?:ed|ing)?\s+(.+?)\s+performance',
                r'migrat(?:ed|ing)?\s+(.+?)\s+to\s+(.+)'
            ],
            'template': "Refactored {}"
        },
        'documentation': {
            'patterns': [
                r'document(?:ed|ing)?\s+(.+)',
                r'wrot(?:e|ing)\s+(?:docs|documentation)\s+for\s+(.+)',
                r'creat(?:ed|ing)?\s+(.+?)\s+(?:guide|tutorial|readme)'
            ],
            'template': "Documented {}"
        }
    }
    
    # Track what's been done to avoid duplicates
    seen_deliverables = set()
    
    for record in records:
        text = record.get('text', '').lower()
        
        # Skip system messages and very short texts
        if record['role'] != 'assistant' or len(text) < 20:
            continue
            
        # Check for each pattern type
        for work_type, config in patterns.items():
            for pattern in config['patterns']:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    # Extract the main deliverable
                    deliverable = match.group(1).strip()
                    
                    # Clean up the deliverable text
                    deliverable = re.sub(r'\s+', ' ', deliverable)
                    deliverable = deliverable.strip('.,;:')
                    
                    # Skip if too short or already seen
                    if len(deliverable) < 10 or deliverable in seen_deliverables:
                        continue
                        
                    seen_deliverables.add(deliverable)
                    
                    # Create the description
                    description = config['template'].format(deliverable)
                    
                    # Add context if available
                    if match.lastindex > 1 and match.group(2):
                        context = match.group(2).strip()
                        description += f" in {context}"
                    
                    deliverables.append({
                        'timestamp': record['timestamp'],
                        'description': description,
                        'type': work_type,
                        'raw_text': text[:200]
                    })
    
    return deliverables


def extract_error_fixes(records: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Extract specific errors that were fixed and their resolutions.
    """
    error_fixes = []
    errors_seen = {}  # Track errors to find their fixes
    
    for i, record in enumerate(records):
        text = record.get('text', '')
        
        # Look for error messages
        error_patterns = [
            r'(TypeError|ValueError|AttributeError|KeyError|ImportError|SyntaxError):\s*(.+?)(?:\n|$)',
            r'Error:\s*(.+?)(?:\n|$)',
            r'failed with:\s*(.+?)(?:\n|$)',
            r'exception:\s*(.+?)(?:\n|$)'
        ]
        
        for pattern in error_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                error_type = match.group(1) if match.lastindex > 1 else "Error"
                error_msg = match.group(2) if match.lastindex > 1 else match.group(1)
                error_key = f"{error_type}:{error_msg[:50]}"
                
                if error_key not in errors_seen:
                    errors_seen[error_key] = {
                        'type': error_type,
                        'message': error_msg.strip(),
                        'timestamp': record['timestamp'],
                        'index': i
                    }
        
        # Look for fixes in subsequent messages
        if record['role'] == 'assistant':
            fix_patterns = [
                r'fix(?:ed|ing)?\s+(?:the\s+)?(.+?)\s+error',
                r'resolv(?:ed|ing)?\s+(?:the\s+)?(.+?)\s+issue',
                r'(?:the\s+)?error\s+(?:was|is)\s+(?:fixed|resolved)',
                r'(?:corrected|addressed)\s+(?:the\s+)?(.+?)\s+problem'
            ]
            
            for pattern in fix_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    # Find recent errors that might have been fixed
                    for error_key, error_info in errors_seen.items():
                        if i - error_info['index'] < 10:  # Within 10 messages
                            error_fixes.append({
                                'timestamp': record['timestamp'],
                                'description': f"Fixed {error_info['type']}: {error_info['message'][:100]}",
                                'error_timestamp': error_info['timestamp']
                            })
                            # Mark as fixed
                            errors_seen[error_key]['fixed'] = True
    
    return error_fixes


def extract_features_implemented(records: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Extract specific features that were implemented.
    """
    features = []
    
    # Look for PR titles, commit messages, and feature descriptions
    feature_patterns = [
        r'feat(?:ure)?:\s*(.+?)(?:\n|$)',
        r'add(?:ed|s)?\s+(.+?)\s+(?:feature|functionality|capability)',
        r'implement(?:ed|s)?\s+(.+?)(?:\n|$)',
        r'creat(?:ed|es)?\s+(.+?)\s+(?:for|to)\s+(.+)',
        r'built\s+(.+?)\s+(?:with|using|for)\s+(.+)',
        r'(?:new|added)\s+(.+?)\s+(?:command|endpoint|api|function)'
    ]
    
    seen_features = set()
    
    for record in records:
        if record['role'] != 'assistant':
            continue
            
        text = record.get('text', '')
        
        for pattern in feature_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                feature = match.group(1).strip()
                
                # Clean up
                feature = re.sub(r'\s+', ' ', feature)
                feature = feature.strip('.,;:*`"\'')
                
                # Skip if too short or duplicate
                if len(feature) < 15 or feature.lower() in seen_features:
                    continue
                    
                seen_features.add(feature.lower())
                
                # Add context if available
                description = f"Implemented {feature}"
                if match.lastindex > 1 and match.group(2):
                    context = match.group(2).strip()
                    description += f" for {context}"
                
                features.append({
                    'timestamp': record['timestamp'],
                    'description': description
                })
    
    return features


def generate_time_entry_descriptions(session_data: Dict[str, Any]) -> List[str]:
    """
    Generate Clockify-ready descriptions from session data.
    """
    descriptions = []
    
    # Extract all types of work
    deliverables = extract_deliverables(session_data['records'])
    error_fixes = extract_error_fixes(session_data['records'])
    features = extract_features_implemented(session_data['records'])
    
    # Combine and deduplicate
    all_work = []
    all_work.extend([d['description'] for d in deliverables])
    all_work.extend([e['description'] for e in error_fixes])
    all_work.extend([f['description'] for f in features])
    
    # Group similar work items
    grouped_work = defaultdict(list)
    for work in all_work:
        # Extract the main action
        action_match = re.match(r'^(\w+)\s+', work)
        if action_match:
            action = action_match.group(1)
            grouped_work[action].append(work)
        else:
            grouped_work['other'].append(work)
    
    # Create concise descriptions
    for action, items in grouped_work.items():
        if len(items) == 1:
            descriptions.append(items[0])
        elif len(items) <= 3:
            # Combine similar items
            main_parts = []
            for item in items:
                # Extract the object of the action
                parts = item.split(' ', 2)
                if len(parts) > 2:
                    main_parts.append(parts[2])
            
            if main_parts:
                description = f"{action.capitalize()} {', '.join(main_parts[:2])}"
                if len(main_parts) > 2:
                    description += f" and {len(main_parts) - 2} more"
                descriptions.append(description)
        else:
            # Summarize many items
            descriptions.append(f"{action.capitalize()} {len(items)} {action.lower()} items")
    
    return descriptions[:5]  # Return top 5 most relevant


def enhance_work_summary(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create an enhanced work summary with deliverable-focused descriptions.
    """
    # Get time entry descriptions
    descriptions = generate_time_entry_descriptions({'records': records})
    
    # Extract key accomplishments
    deliverables = extract_deliverables(records)
    error_fixes = extract_error_fixes(records)
    features = extract_features_implemented(records)
    
    # Create a summary
    summary = {
        'time_entry_descriptions': descriptions,
        'deliverables': [d['description'] for d in deliverables[:10]],
        'errors_fixed': [e['description'] for e in error_fixes[:5]],
        'features_implemented': [f['description'] for f in features[:5]],
        'suggested_clockify_description': ' | '.join(descriptions[:3]) if descriptions else "Development work"
    }
    
    return summary


# Example usage
if __name__ == "__main__":
    # This would be integrated into the existing extract_claude_work_insights.py
    print("Enhanced description extraction module")
    print("Import this module and use:")
    print("  - extract_deliverables(records)")
    print("  - extract_error_fixes(records)")
    print("  - extract_features_implemented(records)")
    print("  - generate_time_entry_descriptions(session_data)")
    print("  - enhance_work_summary(records)")