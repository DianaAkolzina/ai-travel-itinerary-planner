#!/bin/bash



set -e  

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' 

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo -e "${PURPLE}🚀 $1${NC}"
}

check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 1  
    else
        return 0  
    fi
}

wait_for_service() {
    local url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1
    
    print_info "Waiting for $service_name to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" >/dev/null 2>&1; then
            print_status "$service_name is ready!"
            return 0
        fi
        
        echo -n "."
        sleep 2
        ((attempt++))
    done
    
    print_error "$service_name failed to start within $(($max_attempts * 2)) seconds"
    return 1
}

setup_mongodb() {
    print_header "Setting up MongoDB..."
    
    if pgrep -x "mongod" > /dev/null; then
        print_status "MongoDB is already running"
        return 0
    fi
    
    
    if command -v brew >/dev/null 2>&1; then
        
        print_info "Starting MongoDB with Homebrew..."
        if brew services list | grep mongodb-community | grep started >/dev/null; then
            print_status "MongoDB service already started"
        else
            brew services start mongodb-community || {
                print_error "Failed to start MongoDB with Homebrew"
                print_info "Trying to start MongoDB manually..."
                mongod --config /usr/local/etc/mongod.conf --fork || {
                    print_error "Failed to start MongoDB manually"
                    return 1
                }
            }
        fi
    elif command -v systemctl >/dev/null 2>&1; then
      
        print_info "Starting MongoDB with systemctl..."
        sudo systemctl start mongod || {
            print_error "Failed to start MongoDB service"
            return 1
        }
    elif command -v service >/dev/null 2>&1; then
     
        print_info "Starting MongoDB with service command..."
        sudo service mongod start || {
            print_error "Failed to start MongoDB service"
            return 1
        }
    else
     
        print_info "Trying to start MongoDB with Docker..."
        if command -v docker >/dev/null 2>&1; then
            docker run -d --name mongodb-travel -p 27017:27017 mongo:latest || {
               
                if docker ps -a | grep mongodb-travel >/dev/null; then
                    print_info "Starting existing MongoDB container..."
                    docker start mongodb-travel
                else
                    print_error "Failed to start MongoDB with Docker"
                    return 1
                fi
            }
        else
            print_error "MongoDB not found and no installation method available"
            print_info "Please install MongoDB manually:"
            print_info "  - macOS: brew install mongodb-community"
            print_info "  - Ubuntu: sudo apt-get install mongodb"
            print_info "  - Docker: docker run -d -p 27017:27017 mongo:latest"
            return 1
        fi
    fi
    
    print_info "Waiting for MongoDB to be ready..."
    local attempt=1
    local max_attempts=15
    
    while [ $attempt -le $max_attempts ]; do
        if mongo --eval "db.adminCommand('ismaster')" >/dev/null 2>&1; then
            print_status "MongoDB is ready!"
            return 0
        fi
        
        echo -n "."
        sleep 2
        ((attempt++))
    done
    
    print_error "MongoDB failed to start within $(($max_attempts * 2)) seconds"
    return 1
}

check_ollama() {
    print_header "Checking Ollama service..."
    
    if ! command -v ollama >/dev/null 2>&1; then
        print_error "Ollama not found. Please install Ollama:"
        print_info "Visit: https://ollama.ai/install"
        return 1
    fi
    
    if ! curl -s http://localhost:11434/api/version >/dev/null 2>&1; then
        print_info "Starting Ollama service..."
        ollama serve &
        
        wait_for_service "http://localhost:11434/api/version" "Ollama"
    else
        print_status "Ollama service is already running"
    fi
    
    if ollama list | grep llama3 >/dev/null 2>&1; then
        print_status "Llama3 model is available"
    else
        print_info "Downloading Llama3 model (this may take a while)..."
        ollama pull llama3 || {
            print_error "Failed to download Llama3 model"
            return 1
        }
        print_status "Llama3 model downloaded successfully"
    fi
    
    return 0
}

main() {
    print_header "🌍 AI Travel Itinerary Planner with Database Caching"
    echo ""
    
    print_header "Loading Environment Configuration..."
    if [ -f .env ]; then
        export $(grep -v '^#' .env | grep -v '^$' | xargs)
        print_status "Environment variables loaded from .env"
        
        if [ -n "$GOOGLE_MAPS_API_KEY" ]; then
            print_info "🔑 Google Maps API Key: ${GOOGLE_MAPS_API_KEY:0:10}********"
        else
            print_warning "Google Maps API Key not set"
        fi
        
        if [ -n "$RAPIDAPI_KEY" ]; then
            print_info "🔑 RapidAPI Key: ${RAPIDAPI_KEY:0:5}********"
        else
            print_warning "RapidAPI Key not set"
        fi
        
        CACHE_ENABLED=${CACHE_ENABLED:-true}
        CACHE_EXPIRY_HOURS=${CACHE_EXPIRY_HOURS:-24}
        MONGODB_URI=${MONGODB_URI:-mongodb://localhost:27017/travel-planner}
        
        print_info "💾 Cache Enabled: $CACHE_ENABLED"
        print_info "⏰ Cache Expiry: $CACHE_EXPIRY_HOURS hours"
        print_info "🗄️ MongoDB URI: ${MONGODB_URI:0:30}..."
        
    else
        print_error ".env file not found!"
        print_info "Please create a .env file with the following variables:"
        print_info "  GOOGLE_MAPS_API_KEY=your_api_key"
        print_info "  RAPIDAPI_KEY=your_api_key"
        print_info "  CACHE_ENABLED=true"
        print_info "  CACHE_EXPIRY_HOURS=24"
        print_info "  MONGODB_URI=mongodb://localhost:27017/travel-planner"
        exit 1
    fi
    
    echo ""
    
    print_header "Checking Port Availability..."
    
    if ! check_port 8000; then
        print_error "Port 8000 is already in use (Python AI service)"
        print_info "Kill the process using: lsof -ti:8000 | xargs kill -9"
        exit 1
    fi
    
    if ! check_port 5000; then
        print_error "Port 5000 is already in use (Node.js backend)"
        print_info "Kill the process using: lsof -ti:5000 | xargs kill -9"
        exit 1
    fi
    
    if ! check_port 5173; then
        print_error "Port 5173 is already in use (React frontend)"
        print_info "Kill the process using: lsof -ti:5173 | xargs kill -9"
        exit 1
    fi
    
    print_status "All required ports are available"
    echo ""
    
    if [ "$CACHE_ENABLED" = "true" ]; then
        if ! setup_mongodb; then
            print_warning "MongoDB setup failed. Caching will be disabled."
            export CACHE_ENABLED=false
        fi
        echo ""
    else
        print_info "Caching is disabled, skipping MongoDB setup"
        echo ""
    fi
    
    if ! check_ollama; then
        print_error "Ollama setup failed. The AI service may not work properly."
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    echo ""
    
    print_header "🐍 Setting up Python AI Service..."
    
    if [ ! -d "ai-services-new" ]; then
        print_error "ai-services-new directory not found!"
        exit 1
    fi
    
    cd ai-services-new
    
    if [ ! -d "venv" ]; then
        print_info "Creating Python virtual environment..."
        python3 -m venv venv || {
            print_error "Failed to create virtual environment"
            exit 1
        }
    fi
    
    source venv/bin/activate || {
        print_error "Failed to activate virtual environment"
        exit 1
    }
    
    print_info "Installing Python dependencies..."
    pip install --upgrade pip >/dev/null 2>&1
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt || {
            print_error "Failed to install Python dependencies"
            exit 1
        }
    else
        print_warning "requirements.txt not found, skipping Python dependency installation"
    fi
    
    if [ "$CACHE_ENABLED" = "true" ]; then
        print_info "Verifying cache dependencies..."
        python -c "import pymongo; print('✅ pymongo installed')" || {
            print_info "Installing pymongo for database caching..."
            pip install pymongo==4.6.1 || {
                print_error "Failed to install pymongo"
                exit 1
            }
        }
    fi
    
    print_status "Python environment ready"
    
    print_info "Starting Python AI service on port 8000..."
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
    PYTHON_PID=$!
    
    cd ..
    echo ""
    
    print_header "🚀 Setting up Node.js Backend..."
    
    if [ ! -d "backend" ]; then
        print_error "backend directory not found!"
        exit 1
    fi
    
    cd backend
    
    print_info "Installing Node.js dependencies..."
    npm install || {
        print_error "Failed to install Node.js dependencies"
        exit 1
    }
    
    print_status "Node.js dependencies installed"
    
    print_info "Starting Node.js backend on port 5000..."
    npm start &
    NODEJS_PID=$!
    
    cd ..
    echo ""
    
    print_header "🌐 Setting up React Frontend..."
    
    if [ ! -d "frontend" ]; then
        print_error "frontend directory not found!"
        exit 1
    fi
    
    cd frontend
    
    print_info "Installing React dependencies..."
    npm install || {
        print_error "Failed to install React dependencies"
        exit 1
    }
    
    print_status "React dependencies installed"
    
    print_info "Starting React frontend on port 5173..."
    npm run dev &
    REACT_PID=$!
    
    cd ..
    echo ""
    
    print_header "🔍 Verifying Service Health..."
   
    if wait_for_service "http://localhost:8000/docs" "Python AI Service"; then
     
        if [ "$CACHE_ENABLED" = "true" ]; then
            print_info "Testing cache functionality..."
            if curl -s "http://localhost:8000/cache/stats" >/dev/null 2>&1; then
                print_status "Cache service is working"
            else
                print_warning "Cache service may not be working properly"
            fi
        fi
    else
        print_error "Python AI service failed to start"
    fi
    
    wait_for_service "http://localhost:5000" "Node.js Backend" || {
        print_error "Node.js backend failed to start"
    }
    
    wait_for_service "http://localhost:5173" "React Frontend" || {
        print_error "React frontend failed to start"
    }
    
    echo ""
    print_header "🎉 All Services Started Successfully!"
    echo ""
    echo -e "${CYAN}📊 Service URLs:${NC}"
    echo -e "   ${GREEN}• Frontend:${NC}     http://localhost:5173"
    echo -e "   ${GREEN}• Node.js API:${NC}  http://localhost:5000"
    echo -e "   ${GREEN}• Python AI:${NC}    http://localhost:8000"
    echo -e "   ${GREEN}• API Docs:${NC}     http://localhost:8000/docs"
    if [ "$CACHE_ENABLED" = "true" ]; then
        echo -e "   ${GREEN}• Cache Stats:${NC}  http://localhost:8000/cache/stats"
    fi
    echo ""
    echo -e "${YELLOW}🔧 Management Commands:${NC}"
    echo -e "   ${BLUE}• Cache Stats:${NC}   curl http://localhost:8000/cache/stats"
    echo -e "   ${BLUE}• Clear Cache:${NC}   curl -X DELETE http://localhost:8000/cache/clear"
    echo -e "   ${BLUE}• Health Check:${NC}  curl http://localhost:8000/health"
    echo ""
    echo -e "${GREEN}✨ Ready to plan amazing trips! Visit: http://localhost:5173${NC}"
    echo ""
    
    cleanup() {
        echo ""
        print_info "Shutting down services..."
        
        if [ ! -z "$REACT_PID" ]; then
            kill $REACT_PID 2>/dev/null || true
        fi
        
        if [ ! -z "$NODEJS_PID" ]; then
            kill $NODEJS_PID 2>/dev/null || true
        fi
        
        if [ ! -z "$PYTHON_PID" ]; then
            kill $PYTHON_PID 2>/dev/null || true
        fi
        
        lsof -ti:5173 | xargs kill -9 2>/dev/null || true
        lsof -ti:5000 | xargs kill -9 2>/dev/null || true
        lsof -ti:8000 | xargs kill -9 2>/dev/null || true
        
        print_status "All services stopped"
        exit 0
    }
    
    trap cleanup SIGINT SIGTERM
    
    print_info "Press Ctrl+C to stop all services"
    wait
}

main "$@"
