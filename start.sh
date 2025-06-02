#!/bin/bash

# ======================
# AI Travel Itinerary Planner Startup Script
# ======================
# This script sets up and runs the complete local development environment:
# - Loads environment variables
# - Ensures ports are free
# - Starts MongoDB (if caching enabled)
# - Validates Ollama LLM service and model
# - Launches backend services: Python API, Node.js, React frontend
# - Verifies health of all components
# - Supports Ctrl+C for clean shutdown
# ======================

set -e  # Exit on error

# ========== Color Setup ==========
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'  # No color

# ========== Utility Logging Functions ==========
print_status()   { echo -e "${GREEN}$1${NC}"; }
print_info()     { echo -e "${BLUE}  $1${NC}"; }
print_warning()  { echo -e "${YELLOW}  $1${NC}"; }
print_error()    { echo -e "${RED}$1${NC}"; }
print_header()   { echo -e "${PURPLE}$1${NC}"; }

# ========== Port Checking ==========
check_port() {
    local port=$1
    ! lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1
}

# ========== Wait for a URL to respond ==========
wait_for_service() {
    local url=$1
    local service_name=$2
    for i in {1..30}; do
        curl -s "$url" >/dev/null && print_status "$service_name is ready!" && return 0
        sleep 2
    done
    print_error "$service_name failed to respond in time"
    return 1
}

# ========== MongoDB Setup ==========
setup_mongodb() {
    print_header "Setting up MongoDB..."

    if pgrep -x "mongod" > /dev/null; then
        print_status "MongoDB already running"
        return 0
    fi

    if command -v brew &>/dev/null; then
        brew services start mongodb-community || mongod --config /usr/local/etc/mongod.conf --fork || return 1
    elif command -v systemctl &>/dev/null; then
        sudo systemctl start mongod || return 1
    elif command -v service &>/dev/null; then
        sudo service mongod start || return 1
    elif command -v docker &>/dev/null; then
        docker start mongodb-travel 2>/dev/null || docker run -d --name mongodb-travel -p 27017:27017 mongo:latest || return 1
    else
        print_error "No method found to start MongoDB. Install it manually."
        return 1
    fi

    wait_for_service "http://localhost:27017" "MongoDB"
}

# ========== Ollama Setup ==========
check_ollama() {
    print_header "Checking Ollama..."
    command -v ollama >/dev/null || {
        print_error "Ollama not installed. Install from https://ollama.ai/install"; return 1; }

    curl -s http://localhost:11434/api/version >/dev/null || ollama serve &
    wait_for_service "http://localhost:11434/api/version" "Ollama"

    ollama list | grep -q llama3 || ollama pull llama3 || return 1
    print_status "Llama3 model ready"
    return 0
}

# ========== Main Entry ==========
main() {
    print_header "\n🌍 Launching AI Travel Itinerary Planner"

    # Load environment
    [ -f .env ] || { print_error ".env not found"; exit 1; }
    export $(grep -v '^#' .env | xargs)
    CACHE_ENABLED=${CACHE_ENABLED:-true}

    # Check ports
    for port in 8000 5000 5173; do
        check_port $port || { print_error "Port $port in use"; exit 1; }
    done

    # MongoDB
    [ "$CACHE_ENABLED" = true ] && setup_mongodb || print_info "Caching disabled"

    # Ollama
    check_ollama || { print_error "Ollama setup failed"; exit 1; }

    # === Python AI service ===
    cd ai-services-new || { print_error "Missing ai-services-new"; exit 1; }
    [ -d venv ] || python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    [ -f requirements.txt ] && pip install -r requirements.txt
    [ "$CACHE_ENABLED" = true ] && python -c "import pymongo" 2>/dev/null || pip install pymongo
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
    PY_PID=$!
    cd ..

    # === Node backend ===
    cd backend || { print_error "Missing backend"; exit 1; }
    npm install && npm start &
    NODE_PID=$!
    cd ..

    # === React frontend ===
    cd frontend || { print_error "Missing frontend"; exit 1; }
    npm install && npm run dev &
    REACT_PID=$!
    cd ..

    # Wait and confirm health
    wait_for_service "http://localhost:8000/docs" "Python AI"
    wait_for_service "http://localhost:5000" "Node.js API"
    wait_for_service "http://localhost:5173" "Frontend"

    print_header "\n✅ All services started successfully!"
    echo -e "${CYAN}Visit your app at: http://localhost:5173${NC}"

    trap cleanup INT TERM
    wait
}

# ========== Cleanup on Exit ==========
cleanup() {
    print_info "Shutting down services..."
    for pid in $REACT_PID $NODE_PID $PY_PID; do
        kill $pid 2>/dev/null || true
    done
    print_status "All services stopped."
    exit 0
}

main "$@"
