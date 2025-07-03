# Google Calendar Integration

This document describes the Google Calendar integration feature that displays meetings alongside coding activity in the time tracker heatmap.

## Overview

The calendar integration fetches meetings from your Google Calendar and displays them in both the ASCII and web heatmaps with distinct visual indicators. This helps you see the correlation between meetings and coding productivity.

## Features

- **Smart Meeting Filtering**: Only shows meetings with external attendees, excluding time blockers and declined meetings
- **Visual Differentiation**: Meetings appear in purple tones while coding activity uses green tones
- **Detailed Tooltips**: Hover over meeting blocks to see meeting title, attendees, duration, and location
- **Configurable**: Extensive configuration options for filtering and display preferences

## Setup

### 1. Prerequisites

The calendar integration uses the same OAuth setup as the fuzzy-ops project. You'll need:

- Google OAuth credentials at `~/.config/cli-tools/gmail_config.json`
- Python packages: `google-api-python-client`, `google-auth-httplib2`, `google-auth-oauthlib`

### 2. First-Time Authentication

1. Copy the OAuth credentials from fuzzy-ops if not already present:
   ```bash
   cp ~/.config/cli-tools/gmail_config.json ~/.config/cli-tools/
   ```

2. Run the test script to authenticate:
   ```bash
   uv run test_calendar_integration.py
   ```

3. A browser window will open for Google authentication. Grant calendar read access.

4. The token will be saved at `~/.config/cli-tools/calendar_token.json`

## Configuration

Calendar settings are configured in `config/config.yaml`:

```yaml
# Calendar integration settings
calendar:
  enabled: true
  
  # Owner email for filtering (meetings without this person are shown)
  owner_email: rolf
  
  # Meeting display preferences
  display:
    # Show meetings in ASCII heatmap
    show_in_ascii: true
    
    # Show meetings in web dashboard
    show_in_web: true
    
    # Meeting colors for web dashboard (purple theme by default)
    colors:
      light: "#f3e5ff"
      medium_light: "#d4b5ff"
      medium: "#b794f6"
      medium_dark: "#9f7aea"
      dark: "#805ad5"
  
  # Meeting filtering options
  filtering:
    # Exclude meetings with these keywords in the title
    exclude_keywords:
      - block
      - busy
      - "focus time"
      - "work time"
      - "deep work"
      - "no meetings"
      - hold
      - tentative
    
    # Only include meetings with external attendees
    require_external_attendees: true
    
    # Exclude meetings marked as free/transparent
    exclude_free_time: true
    
    # Exclude declined meetings
    exclude_declined: true
    
    # Minimum attendee count (set to 2 to exclude 1:1s with self)
    minimum_attendees: 2
```

## Usage

### ASCII Heatmap

Run the heatmap generator as usual:

```bash
uv run src/generate_heatmap.py
```

Meetings will appear with special characters:
- `◊` - Light meeting coverage (< 25% of block)
- `◈` - Medium-light coverage (25-50%)
- `◆` - Medium-heavy coverage (50-75%)
- `♦` - Full meeting block (75-100%)

To disable meetings in the ASCII heatmap:
```bash
uv run src/generate_heatmap.py --no-meetings
```

### Web Dashboard

Generate the dashboard as usual:

```bash
uv run src/generate_static_dashboard.py
```

Meetings appear in purple tones, distinct from the green coding activity. The legend shows both scales.

## Meeting Filtering Logic

The system filters meetings to show only "real" meetings:

1. **External Attendees**: Must have at least one attendee other than the calendar owner
2. **Not Declined**: Excludes meetings you've declined
3. **Not Time Blockers**: Excludes events with keywords like "block", "busy", "focus time"
4. **Not Free Time**: Excludes events marked as free/transparent in Google Calendar
5. **Minimum Attendees**: By default requires at least 2 attendees

## Troubleshooting

### Authentication Issues

If authentication fails:
1. Ensure `~/.config/cli-tools/gmail_config.json` exists
2. Delete `~/.config/cli-tools/calendar_token.json` and re-authenticate
3. Check that the OAuth app has calendar.readonly scope

### No Meetings Showing

If no meetings appear:
1. Run `test_calendar_integration.py` to verify the connection
2. Check that meetings have external attendees
3. Review exclude_keywords in config - your meeting titles might match
4. Verify the owner_email setting matches your calendar email

### Performance

The calendar API is called once per dashboard generation. Meeting data is not cached, ensuring fresh data but potentially slower generation for large date ranges.