#!/bin/bash
# Wrapper script for running common load test scenarios

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
AGENT_URL="${AGENT_URL:-http://localhost:9000}"
API_PASSWORD="${API_PASSWORD:-}"

show_help() {
    cat << EOF
Usage: ./run_load_test.sh [OPTIONS] [SCENARIO]

Load testing wrapper for Strands A2A agents.

SCENARIOS:
    light       Test with 10 users (quick smoke test)
    medium      Test with 50 users
    100         Test with 100 users
    250         Test with 250 users
    custom      Custom configuration (specify --users)

OPTIONS:
    -u, --url URL           Agent URL (default: \$AGENT_URL or http://localhost:9000)
    -p, --password PASS     API password (default: \$API_PASSWORD)
    -a, --agent TYPE        Agent type: calculator or clock (default: calculator)
    --users NUM             Number of concurrent users (for custom scenario)
    --requests NUM          Requests per user (default: 5)
    -o, --output FILE       Export results to JSON file
    -h, --help              Show this help message

EXAMPLES:
    # Quick smoke test (10 users)
    ./run_load_test.sh light

    # Test with 100 users
    export API_PASSWORD="your_password"
    ./run_load_test.sh -u https://your-agent.com 100

    # Test clock agent with 250 users
    ./run_load_test.sh -u http://localhost:9001 -a clock 250

    # Custom test with output file
    ./run_load_test.sh --users 150 --requests 10 -o results.json custom

ENVIRONMENT VARIABLES:
    AGENT_URL       Default agent URL
    API_PASSWORD    Default API password

EOF
}

# Parse arguments
SCENARIO=""
AGENT_TYPE="calculator"
USERS=""
REQUESTS=""
OUTPUT=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -u|--url)
            AGENT_URL="$2"
            shift 2
            ;;
        -p|--password)
            API_PASSWORD="$2"
            shift 2
            ;;
        -a|--agent)
            AGENT_TYPE="$2"
            shift 2
            ;;
        --users)
            USERS="$2"
            shift 2
            ;;
        --requests)
            REQUESTS="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT="$2"
            shift 2
            ;;
        light|medium|100|250|custom)
            SCENARIO="$1"
            shift
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Check required parameters
if [ -z "$API_PASSWORD" ]; then
    echo -e "${RED}Error: API password required${NC}"
    echo "Set API_PASSWORD environment variable or use --password flag"
    exit 1
fi

if [ -z "$SCENARIO" ]; then
    echo -e "${YELLOW}No scenario specified, defaulting to 'medium' (50 users)${NC}"
    SCENARIO="medium"
fi

# Set users based on scenario
case $SCENARIO in
    light)
        USERS=10
        ;;
    medium)
        USERS=50
        ;;
    100)
        USERS=100
        ;;
    250)
        USERS=250
        ;;
    custom)
        if [ -z "$USERS" ]; then
            echo -e "${RED}Error: --users required for custom scenario${NC}"
            exit 1
        fi
        ;;
    *)
        echo -e "${RED}Error: Unknown scenario '$SCENARIO'${NC}"
        show_help
        exit 1
        ;;
esac

# Determine the correct path to load_test.py
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
if [ -f "$SCRIPT_DIR/load_test.py" ]; then
    LOAD_TEST_PATH="$SCRIPT_DIR/load_test.py"
elif [ -f "$SCRIPT_DIR/../tests/load_test.py" ]; then
    LOAD_TEST_PATH="$SCRIPT_DIR/../tests/load_test.py"
else
    LOAD_TEST_PATH="load_test.py"  # Fallback
fi

# Build command
CMD="python \"$LOAD_TEST_PATH\" --url \"$AGENT_URL\" --password \"$API_PASSWORD\" --agent \"$AGENT_TYPE\" --users $USERS"

if [ -n "$REQUESTS" ]; then
    CMD="$CMD --requests $REQUESTS"
fi

if [ -n "$OUTPUT" ]; then
    CMD="$CMD --output \"$OUTPUT\""
fi

# Show configuration
echo -e "${GREEN}Starting load test...${NC}"
echo "URL: $AGENT_URL"
echo "Agent: $AGENT_TYPE"
echo "Scenario: $SCENARIO ($USERS users)"
if [ -n "$REQUESTS" ]; then
    echo "Requests per user: $REQUESTS"
fi
echo ""

# Check if load_test.py exists
if [ ! -f "$LOAD_TEST_PATH" ]; then
    echo -e "${RED}Error: load_test.py not found at $LOAD_TEST_PATH${NC}"
    echo "Expected location: tests/load_test.py"
    exit 1
fi

# Check for required Python package
if ! python -c "import aiohttp" 2>/dev/null; then
    echo -e "${YELLOW}Warning: aiohttp not installed${NC}"
    echo "Installing required package..."
    pip install aiohttp
fi

# Run the test
eval $CMD

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo -e "${GREEN}Load test completed successfully${NC}"
else
    echo -e "${RED}Load test failed with exit code $exit_code${NC}"
fi

exit $exit_code
