🌍 AI Travel Itinerary Planner
An intelligent travel planning application that generates personalized itineraries using AI, real-time weather data, and interactive maps. Click anywhere on the map, select your dates and interests, and get a comprehensive travel plan optimized for your preferences.

✨ Features
🤖 AI-Powered Planning
Smart Itinerary Generation: Uses local LLM (Llama3) to create detailed, personalized travel plans
Interest-Based Customization: Tailors recommendations based on your preferences (food, art, history, nature, etc.)
Cultural Context: Provides region-specific cultural and historical insights
Route Optimization: Calculates optimal travel routes to minimize distances between destinations
🗺️ Interactive Mapping
Click-to-Select Destinations: Simply click anywhere on the world map to choose your destination
MapLibre GL Integration: Beautiful, responsive interactive maps
Location Validation: Ensures all suggestions are within your specified radius
Google Maps Integration: Direct links for routes and directions
🌤️ Weather Integration
Real-Time Forecasts: Get weather predictions for your exact travel dates
Dual API Support: Uses both OpenWeatherMap and free Open-Meteo APIs
Smart Filtering: Shows weather only for your selected travel days
Weather-Aware Planning: Incorporates weather conditions into activity recommendations
📅 Date Management
Intuitive Calendar Interface: Easy date range selection
Multi-Day Planning: Supports trips of any duration
Date-Specific Activities: Plans different activities for each day
🏢 Technical Architecture
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ React.js        │ │ Node.js         │ │ Python          │
│ Frontend        │◄──►│ Backend         │◄──►│ AI Service      │
│ Port: 5173      │ │ Port: 5000      │ │ Port: 8000      │
└─────────────────┘ └─────────────────┘ └─────────────────┘
│
▼
┌─────────────────┐
│ MapLibre GL     │
│ Interactive     │
│ Maps            │
└─────────────────┘
🛠️ Technology Stack
Frontend (React)
React 18 - Modern UI framework with hooks
MapLibre GL - Interactive mapping library
Lucide React - Beautiful, consistent icons
Vite - Fast development server and build tool
Backend (Node.js)
Express.js - Web application framework
MongoDB - Database for storing itineraries (optional)
Mongoose - MongoDB ODM for data modeling
AI Service (Python)
FastAPI - High-performance API framework
Pydantic - Data validation and serialization
Uvicorn - ASGI server for FastAPI
Requests - HTTP client for external API calls
External APIs
Ollama + Llama3 - Local LLM for AI-powered itinerary generation
Google Maps API - Geocoding and directions
OpenWeatherMap API - Weather forecasts
Open-Meteo API - Free weather alternative
GeoDB Cities API - Location discovery and city information
📋 Prerequisites
Before you begin, ensure you have the following installed:

Node.js (v16 or higher)
Python (v3.10 or higher)
Git - For cloning the repository
Ollama - For local LLM functionality
🚀 Quick Start
1. Clone the Repository
bash
git clone https://github.com/DianaAkolzina/ai-travel-itinerary-planner.git
cd ai-travel-itinerary-planner
2. Environment Setup
Create a .env file in the root directory:

env
# Required API Keys
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
RAPIDAPI_KEY=your_rapidapi_key

# Optional API Keys
OPENWEATHER_API_KEY=your_openweather_api_key

# Optional Database
MONGODB_URI=mongodb://localhost:27017/travel-planner
3. Install Dependencies
Python AI Service
bash
cd ai-services-new
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ..
Node.js Backend
bash
cd backend
npm install
cd ..
React Frontend
bash
cd frontend
npm install
cd ..
4. Setup Ollama and LLM
bash
# Install Ollama (Linux/macOS)
curl -fsSL https://ollama.ai/install.sh | sh

# Pull the Llama3 model
ollama pull llama3

# Start Ollama service
ollama serve
5. Start the Application
Option A: Quick Start (All Services)
bash
# Make the start script executable
chmod +x start.sh

# Start all services at once
./start.sh
Option B: Manual Start (Separate Terminals)
bash
# Terminal 1: Python AI Service
cd ai-services-new
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Node.js Backend  
cd backend
npm start

# Terminal 3: React Frontend
cd frontend
npm run dev
6. Access the Application
Frontend: http://localhost:5173
Node.js Backend: http://localhost:5000
Python AI Service: http://localhost:8000
API Documentation: http://localhost:8000/docs
📖 How to Use
Step-by-Step Guide
🗺️ Select Your Destination
Open the application in your browser
Use the interactive map to click on any location worldwide
The coordinates will be automatically captured
📅 Choose Your Travel Dates
Click on the calendar interface
Select your start and end dates
The system supports multi-day trips
🎨 Pick Your Interests
Select from available interest categories:
🍕 Food & Cuisine
🎨 Art & Culture
🏛️ History & Heritage
🌳 Nature & Outdoors
🏢 Architecture
🛍️ Shopping
🎵 Music & Entertainment
📏 Set Your Travel Radius
Adjust the radius slider (10-200km)
This determines how far from your base location you're willing to travel
🚀 Generate Your Itinerary
Click "Generate Perfect Itinerary"
Wait for the AI to process your request
View your personalized travel plan with weather forecasts
Understanding the Results
Your generated itinerary includes:

Daily Plans: Detailed activities for each day
Weather Forecasts: Weather conditions for each travel day
Location Details: Coordinates and distances for each destination
Nearby Cities: Additional cities to explore in the region
Cultural Context: Historical and cultural information about the area
🔧 API Usage
Generate Itinerary Endpoint
Endpoint: POST /generate-itinerary

Request Body:

json
{
  "destination": "Lat: 52.5200, Lng: 13.4050",
  "travel_dates": ["2025-06-15", "2025-06-16", "2025-06-17"],
  "preferences": {
    "interests": ["Food", "History", "Architecture"]
  },
  "radius": 50
}
Response:

json
{
  "plan": [
    {
      "day": 1,
      "date": "2025-06-15",
      "formatted_date": "June 15, 2025",
      "town": "Berlin",
      "place": "Brandenburg Gate",
      "activities": [
        "Visit the iconic Brandenburg Gate",
        "Explore Pariser Platz",
        "Learn about German reunification history"
      ],
      "lat": 52.5163,
      "lng": 13.3777,
      "distance_from_start": 2.1
    }
  ],
  "weather": {
    "location": "Berlin",
    "forecast": [
      {
        "date": "2025-06-15",
        "temperature": 22,
        "description": "Partly cloudy",
        "humidity": 65
      }
    ],
    "missing_dates": []
  },
  "nearby_cities": ["Potsdam", "Dresden", "Leipzig"],
  "user_coordinates": {"lat": 52.52, "lng": 13.405}
}
📁 Project Structure
ai-travel-itinerary-planner/
├── ai-services-new/              # Python AI Service
│   ├── app/
│   │   ├── api/                  # FastAPI route handlers
│   │   │   └── itinerary.py      # Main itinerary endpoint
│   │   ├── services/             # Business logic
│   │   │   ├── llm_service.py    # LLM integration
│   │   │   ├── weather_service.py# Weather data fetching
│   │   │   └── location_service.py# Location utilities
│   │   ├── external/             # External API clients
│   │   │   ├── openweather.py    # OpenWeatherMap client
│   │   │   ├── open_meteo.py     # Open-Meteo client
│   │   │   └── geodb.py          # GeoDB Cities client
│   │   ├── utils/                # Utility functions
│   │   │   └── helpers.py        # Common helper functions
│   │   ├── models/               # Pydantic models
│   │   │   └── itinerary.py      # Data models
│   │   ├── config.py             # Configuration settings
│   │   └── main.py               # FastAPI application
│   └── requirements.txt          # Python dependencies
├── backend/                      # Node.js Backend
│   ├── server.js                 # Express server
│   ├── routes/                   # API routes
│   ├── models/                   # Data models
│   └── package.json              # Node.js dependencies
├── frontend/                     # React Frontend
│   ├── src/
│   │   ├── components/           # React components
│   │   ├── hooks/                # Custom React hooks
│   │   ├── utils/                # Frontend utilities
│   │   ├── styles/               # CSS styles
│   │   ├── App.js                # Main application component
│   │   └── main.jsx              # Application entry point
│   ├── public/                   # Static assets
│   └── package.json              # Frontend dependencies
├── start.sh                      # Startup script
├── docker-compose.yml            # Docker configuration
└── README.md                     # This file
🧪 Testing
Python Tests
bash
cd ai-services-new
python -m pytest tests/ -v
Node.js Tests
bash
cd backend
npm test
Frontend Tests
bash
cd frontend
npm test
⚙️ Configuration
Environment Variables
Variable	Description	Required	Default
GOOGLE_MAPS_API_KEY	Google Maps API key for geocoding	Yes	-
RAPIDAPI_KEY	RapidAPI key for GeoDB Cities	Yes	-
OPENWEATHER_API_KEY	OpenWeatherMap API key	No	Uses Open-Meteo
MONGODB_URI	MongoDB connection string	No	In-memory storage
Adding New Interests
To add new interest categories:

Update INTEREST_OPTIONS in frontend/src/App.js
Modify the LLM prompt in ai-services-new/app/services/llm_service.py
Test the new interests to ensure good AI responses
Adding New APIs
To integrate a new external API:

Create a client in ai-services-new/app/external/
Add a service wrapper in ai-services-new/app/services/
Update configuration in ai-services-new/app/config.py
Add API credentials to .env file
🐛 Troubleshooting
Common Issues
Ollama Not Running

bash
# Check if Ollama is running
ollama serve

# Verify Llama3 model is installed
ollama list

# Test the model
ollama run llama3 "Hello"
API Key Issues

Verify your .env file exists and contains valid API keys
Check that API keys have sufficient quota
Some features will gracefully degrade without optional API keys
Port Conflicts

Frontend: Default port 5173 (can be changed in frontend/package.json)
Backend: Default port 5000 (can be changed in backend/server.js)
AI Service: Default port 8000 (can be changed with --port flag)
Memory Issues

Ollama requires significant RAM for LLM processing
Consider using a smaller model if you have limited memory
Monitor system resources during operation
🚢 Deployment
Docker Deployment
bash
# Build and run with Docker Compose
docker-compose up --build
Manual Deployment
Server Setup
VPS with Python 3.10+ and Node.js 16+
Install Ollama and required models
Configure firewall for required ports
Reverse Proxy Setup
nginx
# Nginx configuration
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:5173;
    }
    
    location /api/ {
        proxy_pass http://localhost:5000;
    }
    
    location /ai/ {
        proxy_pass http://localhost:8000;
    }
}
Process Management
bash
# Use PM2 for Node.js services
pm2 start backend/server.js --name "travel-backend"

# Use systemd for Python service
sudo systemctl enable travel-ai-service
SSL Configuration
bash
# Install Let's Encrypt certificates
sudo certbot --nginx -d your-domain.com
🔮 Future Improvements
Short-term Enhancements
User Authentication & Profiles
User registration and login system
Save and manage multiple itineraries
Personal preferences and travel history
Social features for sharing itineraries
Enhanced AI Capabilities
Support for multiple LLM providers (OpenAI, Claude, etc.)
More sophisticated prompt engineering
Context-aware recommendations based on travel history
Real-time learning from user feedback
Mobile Experience
React Native mobile application
Offline functionality for downloaded itineraries
GPS integration for real-time location tracking
Push notifications for travel reminders
Medium-term Features
Collaborative Planning
Multi-user trip planning
Real-time collaboration features
Voting system for group decisions
Shared expense tracking
Advanced Integrations
Hotel and flight booking integration
Restaurant reservation systems
Public transportation schedules
Event and activity booking platforms
Enhanced Data & Analytics
Travel analytics and insights
Carbon footprint calculations
Budget optimization suggestions
Popular destination trends
Long-term Vision
AI-Powered Optimizations
Dynamic itinerary adjustments based on real-time conditions
Predictive modeling for optimal travel times
Personalized AI travel assistant
Natural language query processing
Global Expansion
Multi-language support (i18n)
Regional customizations
Local guide integrations
Cultural sensitivity enhancements
Advanced Features
VR/AR integration for destination previews
IoT integration for smart travel experiences
Blockchain-based travel rewards system
Machine learning for predictive travel planning
🤝 Contributing
We welcome contributions! Please follow these steps:

Fork the repository
Create a feature branch (git checkout -b feature/amazing-feature)
Commit your changes (git commit -m 'Add amazing feature')
Push to the branch (git push origin feature/amazing-feature)
Open a Pull Request
Development Guidelines
Follow existing code style and conventions
Add tests for new features
Update documentation for API changes
Ensure all tests pass before submitting PR
📄 License
This project is licensed under the MIT License - see the LICENSE file for details.

🙏 Acknowledgments
Ollama - For providing local LLM capabilities
OpenWeatherMap & Open-Meteo - For weather data APIs
Google Maps - For geocoding and mapping services
GeoDB Cities - For location discovery
MapLibre - For beautiful interactive maps
📞 Support
If you encounter any issues or have questions:

Check the Troubleshooting section
Search existing GitHub Issues
Create a new issue with detailed information
Join our community discussions
Happy Traveling! 🌍✈️

