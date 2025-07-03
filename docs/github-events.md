# GitHub Event Time Tracking

This document describes the enhanced GitHub event tracking capabilities added to the time tracker integration.

## Overview

The GitExtractor now supports tracking multiple types of GitHub events beyond just commits:

- **GitHub Actions**: Track workflow runs with their duration and status
- **Issues**: Track issue creation and comments  
- **Pull Requests**: Track PR creation, merges, and reviews

## Configuration

Edit `config/config.yaml` to enable the GitHub event types you want to track:

```yaml
services:
  git:
    enabled: true
    
    # GitHub event tracking options
    track_commits: true         # Track git commits (default: true)
    track_actions: true         # Track GitHub Actions workflow runs
    track_issues: true          # Track issue creation and comments
    track_pull_requests: true   # Track PR creation, merges, and reviews
    
    # Duration settings for different GitHub events (in minutes)
    action_duration_minutes: 10         # Default duration for GitHub Actions
    issue_creation_duration_minutes: 15 # Duration for issue creation
    issue_comment_duration_minutes: 5   # Duration for issue comments
    pr_creation_duration_minutes: 20    # Duration for PR creation
    pr_merge_duration_minutes: 10       # Duration for PR merges
    pr_review_duration_minutes: 15      # Duration for PR reviews
```

## Event Types

### GitHub Actions
- Tracks workflow runs from GitHub Actions
- Records: workflow name, status, conclusion, run number, and actor
- Duration: Actual runtime if completed, otherwise uses configured default

### Issues
- **Issue Creation**: Tracks when new issues are created
- **Issue Comments**: Tracks comments added to issues
- Records: issue number, title, state, and author

### Pull Requests  
- **PR Creation**: Tracks when new PRs are opened
- **PR Merges**: Tracks when PRs are merged
- **PR Reviews**: Tracks code review submissions
- Records: PR number, title, state, reviewer (for reviews), and review state

## Testing

Run the test script to see GitHub events from the last 30 days:

```bash
uv run test_github_events.py
```

## Requirements

- GitHub CLI (`gh`) must be installed and authenticated
- Appropriate permissions to access repository data via GitHub API

## Data Model

Each GitHub event is converted to a Session object with:
- `start`: Event timestamp
- `end`: Start time + configured duration
- `service`: "Git"
- `project`: Repository name
- `metrics`: Event-specific data (type, IDs, titles, authors, etc.)

## Example Output

```
Event Summary:
------------------------------------------------------------
commit: 45 events
github_action: 12 events
issue_created: 3 events
issue_comment: 8 events
pr_created: 5 events
pr_merged: 3 events
pr_reviewed: 7 events
```