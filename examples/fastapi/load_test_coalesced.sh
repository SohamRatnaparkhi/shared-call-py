#!/bin/bash

# Load test for COALESCED endpoint (with request coalescing)
# This demonstrates how shared-call-py reduces database load

echo "🚀 Starting load test for COALESCED endpoint..."
echo "📊 Sending 1000 concurrent requests to /product/coalesced/1"
echo "   (All requests query the SAME product - requests will be coalesced)"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
URL="http://localhost:8000/product/coalesced/1"
TOTAL_REQUESTS=1000
CONCURRENT=100  # Number of concurrent requests per batch

# Check if server is running
if ! curl -s "$URL" > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Server is not running at http://localhost:8000${NC}"
    echo "Please start the server first: python main.py"
    exit 1
fi

# Reset stats before test
echo "🔄 Resetting statistics..."
curl -s -X POST http://localhost:8000/stats/reset > /dev/null

# Start timing
START_TIME=$(date +%s.%N)

# Create temporary directory for results
TEMP_DIR=$(mktemp -d)
echo "📁 Storing results in: $TEMP_DIR"

# Function to make a request and save timing
make_request() {
    local id=$1
    local start=$(date +%s.%N)
    
    response=$(curl -s -w "\n%{http_code}\n%{time_total}" "$URL" 2>/dev/null)
    
    local end=$(date +%s.%N)
    local duration=$(echo "$end - $start" | bc)
    
    http_code=$(echo "$response" | tail -n 2 | head -n 1)
    time_total=$(echo "$response" | tail -n 1)
    
    echo "${id},${http_code},${time_total},${duration}" >> "$TEMP_DIR/results.csv"
}

export -f make_request
export URL
export TEMP_DIR

# Initialize results file
echo "request_id,http_code,curl_time,total_time" > "$TEMP_DIR/results.csv"

echo -e "${YELLOW}⏳ Sending requests...${NC}"

# Send requests in batches for better concurrency control
BATCH_SIZE=$CONCURRENT
NUM_BATCHES=$((TOTAL_REQUESTS / BATCH_SIZE))

for batch in $(seq 1 $NUM_BATCHES); do
    echo -n "."
    
    # Launch batch of concurrent requests
    for i in $(seq 1 $BATCH_SIZE); do
        request_id=$(( (batch - 1) * BATCH_SIZE + i ))
        make_request $request_id &
    done
    
    # Wait for batch to complete before starting next batch
    # This creates waves of concurrent requests
    if [ $((batch % 10)) -eq 0 ]; then
        wait
        echo -n " [$((batch * BATCH_SIZE)) requests sent]"
        echo ""
    fi
done

# Wait for all background jobs to complete
wait

# End timing
END_TIME=$(date +%s.%N)
TOTAL_TIME=$(echo "$END_TIME - $START_TIME" | bc)

echo ""
echo -e "${GREEN}✅ Load test completed!${NC}"
echo ""

# Analyze results
TOTAL_REQUESTS_MADE=$(tail -n +2 "$TEMP_DIR/results.csv" | wc -l | tr -d ' ')
SUCCESS_COUNT=$(tail -n +2 "$TEMP_DIR/results.csv" | awk -F',' '$2 == 200' | wc -l | tr -d ' ')
ERROR_COUNT=$(tail -n +2 "$TEMP_DIR/results.csv" | awk -F',' '$2 != 200' | wc -l | tr -d ' ')

# Calculate statistics
if [ "$SUCCESS_COUNT" -gt 0 ]; then
    AVG_TIME=$(tail -n +2 "$TEMP_DIR/results.csv" | awk -F',' '$2 == 200 {sum+=$3; count++} END {if(count>0) print sum/count*1000; else print 0}')
    MIN_TIME=$(tail -n +2 "$TEMP_DIR/results.csv" | awk -F',' '$2 == 200 {print $3}' | sort -n | head -1 | awk '{print $1*1000}')
    MAX_TIME=$(tail -n +2 "$TEMP_DIR/results.csv" | awk -F',' '$2 == 200 {print $3}' | sort -n | tail -1 | awk '{print $1*1000}')
    P50_TIME=$(tail -n +2 "$TEMP_DIR/results.csv" | awk -F',' '$2 == 200 {print $3}' | sort -n | awk -v count=$SUCCESS_COUNT 'NR==int(count*0.5) {print $1*1000}')
    P95_TIME=$(tail -n +2 "$TEMP_DIR/results.csv" | awk -F',' '$2 == 200 {print $3}' | sort -n | awk -v count=$SUCCESS_COUNT 'NR==int(count*0.95) {print $1*1000}')
    P99_TIME=$(tail -n +2 "$TEMP_DIR/results.csv" | awk -F',' '$2 == 200 {print $3}' | sort -n | awk -v count=$SUCCESS_COUNT 'NR==int(count*0.99) {print $1*1000}')
else
    AVG_TIME=0
    MIN_TIME=0
    MAX_TIME=0
    P50_TIME=0
    P95_TIME=0
    P99_TIME=0
fi

REQUESTS_PER_SEC=$(echo "scale=2; $TOTAL_REQUESTS_MADE / $TOTAL_TIME" | bc)

# Print results
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                  COALESCED ENDPOINT RESULTS                    ║"
echo "╠════════════════════════════════════════════════════════════════╣"
echo "║ Total Requests:        $TOTAL_REQUESTS_MADE"
echo "║ Successful:            $SUCCESS_COUNT"
echo "║ Failed:                $ERROR_COUNT"
echo "║ Total Duration:        ${TOTAL_TIME}s"
echo "║ Requests/sec:          $REQUESTS_PER_SEC"
echo "║"
echo "║ Response Times (ms):"
echo "║   Min:                 $MIN_TIME"
echo "║   Max:                 $MAX_TIME"
echo "║   Average:             $AVG_TIME"
echo "║   p50 (median):        $P50_TIME"
echo "║   p95:                 $P95_TIME"
echo "║   p99:                 $P99_TIME"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Get server stats
echo "📊 Server Statistics (Request Coalescing):"
STATS=$(curl -s http://localhost:8000/stats)
echo "$STATS" | python3 -m json.tool

# Extract and highlight key metrics
HITS=$(echo "$STATS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('hits', 0))")
TOTAL=$(echo "$STATS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_requests', 0))")
HIT_RATE=$(echo "$STATS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('hit_rate', '0%'))")

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                     COALESCING IMPACT                          ║${NC}"
echo -e "${BLUE}╠════════════════════════════════════════════════════════════════╣${NC}"
echo -e "${BLUE}║${NC} Database queries WITHOUT coalescing:  ~$TOTAL_REQUESTS_MADE"
echo -e "${BLUE}║${NC} Database queries WITH coalescing:     ~$((TOTAL - HITS))"
echo -e "${BLUE}║${NC} Queries prevented:                    $HITS"
echo -e "${BLUE}║${NC} Hit rate:                             $HIT_RATE"
echo -e "${BLUE}║${NC}"
echo -e "${BLUE}║${NC} 💡 Request coalescing reduced DB load by ~${HIT_RATE}!"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"

# Clean up
rm -rf "$TEMP_DIR"
