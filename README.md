# 🌍 AI Travel Itinerary Planner

An intelligent travel planning application that generates personalized itineraries based on your destination, travel dates, and interests. Powered by AI and enhanced with real-time weather forecasts.

![AI Travel Planner](https://img.shields.io/badge/AI-Travel%20Planner-blue?style=for-the-badge&logo=airplane)
![Python](https://img.shields.io/badge/Python-3.10+-green?style=flat&logo=python)
![React](https://img.shields.io/badge/React-18+-blue?style=flat&logo=react)
![FastAPI](https://img.shields.io/badge/FastAPI-Latest-teal?style=flat&logo=fastapi)

## ✨ Features

### 🎯 **Intelligent Planning**
- **AI-Powered Itineraries**: Generate detailed travel plans using advanced language models
- **Date Range Selection**: Choose specific travel dates with an intuitive calendar interface
- **Location-Based Discovery**: Click on the map to select any destination worldwide
- **Interest Matching**: Customize plans based on your preferences (food, art, history, nature, etc.)

### 🌤️ **Weather Integration**
- **Real-Time Forecasts**: Get weather predictions for your exact travel dates
- **Multiple APIs**: Supports both OpenWeatherMap and free Open-Meteo APIs
- **Smart Filtering**: Only shows forecasts for your selected travel days

### 🗺️ **Smart Route Optimization**
- **Distance Calculation**: Optimizes travel routes to minimize total distance
- **Google Maps Integration**: Direct links to view routes and get directions
- **Location Validation**: Ensures all suggestions are within your specified radius

### 🔍 **Location Intelligence**
- **Nearby Cities Discovery**: Automatically finds relevant cities and regions
- **Geocoding Services**: Converts coordinates to meaningful location information
- **Cultural Context**: Provides region-specific cultural and historical context

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React.js      │    │   Node.js       │    │   Python        │
│   Frontend      │◄──►│   Backend       │◄──►│   AI Service    │
│   Port: 5173    │    │   Port: 5000    │    │   Port: 8000    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐
│   MapLibre GL   │
│   Interactive   │
│   Maps          │
└─────────────────┘
```

## 🚀 Tech Stack

### Frontend
- **React 18** - Modern UI framework
- **MapLibre GL** - Interactive maps
- **Lucide React** - Beautiful icons
- **Vite** - Fast development server

### AI Service (Python)
- **FastAPI** - High-performance API framework
- **Pydantic** - Data validation
- **Uvicorn** - ASGI server
- **Requests** - HTTP client for external APIs

### Backend (Node.js)
- **Express.js** - Web framework
- **MongoDB** - Database (optional)
- **Mongoose** - MongoDB ODM

### External APIs
- **OpenWeatherMap** - Weather forecasts
- **Open-Meteo** - Free weather alternative
- **Google Maps** - Geocoding and directions
- **GeoDB Cities** - Location discovery
- **Local LLM** - AI-powered itinerary generation (Ollama)

## 📦 Installation

### Prerequisites
- **Node.js** (v16+)
- **Python** (v3.10+) 
- **Ollama** with Llama3 model
- **Git**

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/ai-travel-itinerary-planner.git
cd ai-travel-itinerary-planner
```

### 2. Environment Setup
Create `.env` file in the root directory:
```env
# API Keys
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
RAPIDAPI_KEY=your_rapidapi_key
OPENWEATHER_API_KEY=your_openweather_api_key

# MongoDB (Optional)
MONGODB_URI=mongodb://localhost:27017/travel-planner
```

### 3. Install Dependencies

#### Python AI Service
```bash
cd ai-services-new
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### Node.js Backend
```bash
cd backend
npm install
```

#### React Frontend
```bash
cd frontend
npm install
```

### 4. Setup Ollama (Local LLM)
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull Llama3 model
ollama pull llama3

# Start Ollama service
ollama serve
```

## 🎮 Usage

### Start All Services
```bash
# Make the start script executable
chmod +x start.sh

# Start all services
./start.sh
```

This will start:
- **Frontend**: http://localhost:5173
- **Node.js Backend**: http://localhost:5000  
- **Python AI Service**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

### Manual Start (Alternative)
```bash
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
```

## 🎯 How to Use

1. **📍 Select Destination**: Click anywhere on the interactive map
2. **📅 Choose Dates**: Select your travel date range using the calendar
3. **🎨 Pick Interests**: Choose activities you enjoy (food, art, history, etc.)
4. **🎯 Set Radius**: Adjust how far you're willing to travel (10-200km)
5. **🚀 Generate**: Click "Generate Perfect Itinerary"
6. **🌤️ View Results**: See your personalized itinerary with weather forecasts

## 🛠️ API Documentation

### Generate Itinerary Endpoint
```http
POST /generate-itinerary
Content-Type: application/json

{
  "destination": "Lat: 52.5200, Lng: 13.4050",
  "travel_dates": ["2025-06-15", "2025-06-16", "2025-06-17"],
  "preferences": {
    "interests": ["Food", "History", "Architecture"]
  },
  "radius": 50
}
```

### Response Format
```json
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
        "Explore Pariser Platz"
      ],
      "lat": 52.5163,
      "lng": 13.3777,
      "distance_from_start": 2.1
    }
  ],
  "weather": {
    "location": "Berlin",
    "forecast": [...],
    "missing_dates": []
  },
  "nearby_cities": ["Potsdam", "Dresden"],
  "user_coordinates": {"lat": 52.52, "lng": 13.405}
}
```

## 🧪 Development

### Project Structure
```
ai-travel-itinerary-planner/
├── ai-services-new/           # Python AI Service
│   ├── app/
│   │   ├── api/              # FastAPI routes
│   │   ├── services/         # Business logic
│   │   ├── external/         # External API clients
│   │   ├── utils/            # Utility functions
│   │   └── models/           # Pydantic models
│   └── requirements.txt
├── backend/                   # Node.js Backend
│   ├── server.js
│   └── package.json
├── frontend/                  # React Frontend
│   ├── src/
│   ├── public/
│   └── package.json
├── start.sh                   # Startup script
└── README.md
```

### Running Tests
```bash
# Python tests
cd ai-services-new
python -m pytest

# Node.js tests
cd backend
npm test

# Frontend tests
cd frontend
npm test
```

### Adding New Features

#### Adding a New Interest Category
1. Update `INTEREST_OPTIONS` in `frontend/src/App.js`
2. Update the LLM prompt in `ai-services-new/app/services/llm_service.py`

#### Adding New External APIs
1. Create client in `ai-services-new/app/external/`
2. Add service wrapper in `ai-services-new/app/services/`
3. Update configuration in `ai-services-new/app/config.py`

## 🔧 Configuration

### Environment Variables
| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `GOOGLE_MAPS_API_KEY` | Google Maps API key for geocoding | Yes | - |
| `RAPIDAPI_KEY` | RapidAPI key for GeoDB Cities | Yes | - |
| `OPENWEATHER_API_KEY` | OpenWeatherMap API key | No | Uses free API |
| `MONGODB_URI` | MongoDB connection string | No | - |




### Common Issues

#### "LLM connection failed"
- Ensure Ollama is running: `ollama serve`
- Check if Llama3 is installed: `ollama list`
- Verify the model is responding: `ollama run llama3 "Hello"`

#### "API key errors"
- Check your `.env` file exists and has correct keys
- Verify API keys are valid and have sufficient quota
- Some features gracefully degrade without API keys







## 🙏 Acknowledgments

- **Ollama** - For providing local LLM capabilities
- **OpenWeatherMap & Open-Meteo** - For weather data
- **Google Maps** - For geocoding services
- **GeoDB Cities** - For location discovery
- **MapLibre** - For beautiful interactive maps

## 🚀 Deployment

### Docker Deployment (Recommended)
```bash
# Build and run with Docker Compose
docker-compose up --build
```

### Manual Deployment
1. Set up a VPS with Python 3.10+ and Node.js 16+
2. Install and configure Nginx as reverse proxy
3. Use PM2 for Node.js process management
4. Use systemd for Python service management
5. Set up SSL certificates with Let's Encrypt


## 🔮 Future Enhancements

- [ ] **Mobile App** - React Native implementation
- [ ] **User Accounts** - Save and share itineraries
- [ ] **Collaborative Planning** - Plan trips with friends
- [ ] **Offline Mode** - Download itineraries for offline use
- [ ] **Integration** - Connect with booking platforms
- [ ] **Multi-language** - Support for multiple languages
- [ ] **Advanced AI** - More sophisticated trip planning algorithms

---

