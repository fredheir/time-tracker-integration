#!/bin/bash
# Generate and open static dashboard with support for custom days and parallel processing

# Change to script directory
cd "$(dirname "$0")"

# Parse command line arguments
DAYS=7
PARALLEL=false
EXTRA_ARGS=()

usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  --days N       Number of days to analyze (default: 7)"
    echo "  --parallel     Run extractors in parallel (faster for large date ranges)"
    echo "  --help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Last 7 days"
    echo "  $0 --days 30          # Last 30 days"
    echo "  $0 --days 14 --parallel  # Last 14 days with parallel extraction"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --days)
            DAYS="$2"
            shift 2
            ;;
        --parallel)
            PARALLEL=true
            shift
            ;;
        --help|-h)
            usage
            ;;
        *)
            EXTRA_ARGS+=("$1")
            shift
            ;;
    esac
done

echo "=== Time Tracker Dashboard Generator ==="
echo "Analyzing last $DAYS days of activity"
if [ "$PARALLEL" = true ]; then
    echo "Mode: Parallel extraction"
else
    echo "Mode: Sequential extraction"
fi
echo ""

# Function to run time tracker
run_time_tracker() {
    if command -v uv &> /dev/null; then
        uv run --with pandas --with pyyaml python src/time_tracker.py --days "$DAYS"
    else
        # Fallback to python3 if uv is not found
        echo "Warning: uv not found. Running with system python. Make sure dependencies are installed."
        python3 src/time_tracker.py --days "$DAYS"
    fi
}

# Function to run parallel extraction
run_parallel_extraction() {
    if command -v uv &> /dev/null; then
        uv run --with pandas --with pyyaml python scripts/parallel_extract.py --days "$DAYS"
    else
        # Fallback to python3 if uv is not found
        echo "Warning: uv not found. Running with system python. Make sure dependencies are installed."
        python3 scripts/parallel_extract.py --days "$DAYS"
    fi
}

# Run extraction based on mode
if [ "$PARALLEL" = true ]; then
    echo "Starting parallel extraction..."
    run_parallel_extraction
else
    echo "Extracting fresh activity data..."
    run_time_tracker
fi

# Run dashboard generator
echo ""
echo "Generating static dashboard..."
if command -v uv &> /dev/null; then
    uv run --with pandas --with pyyaml --with flask --with plotly --with google-api-python-client --with google-auth-httplib2 --with google-auth-oauthlib python src/generate_static_dashboard.py "${EXTRA_ARGS[@]}"
else
    # Fallback to python3 if uv is not found
    echo "Warning: uv not found. Running with system python. Make sure dependencies are installed."
    python3 src/generate_static_dashboard.py "${EXTRA_ARGS[@]}"
fi

# Open in browser if available
if command -v xdg-open &> /dev/null; then
    xdg-open data/dashboard.html
elif command -v open &> /dev/null; then
    open data/dashboard.html
else
    echo "Dashboard generated at: data/dashboard.html"
    echo "Open this file in your browser to view"
fi