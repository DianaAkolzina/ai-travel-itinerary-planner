# #!/bin/bash

# echo "🔁 Starting services for AI Travel Itinerary Planner..."

# # Load environment variables from .env
# if [ -f .env ]; then
#   export $(grep -v '^#' .env | xargs)
#   echo "✅ Environment variables loaded"
#   echo "🔑 GOOGLE_API_KEY=${GOOGLE_MAPS_API_KEY:0:10}********"
#   echo "🔑 RAPIDAPI_KEY=${RAPIDAPI_KEY:0:5}********"
# else
#   echo "❌ .env file not found!"
#   exit 1
# fi

# # Start Python backend
# echo "🐍 Starting Python AI microservice on port 8000..."
# cd ai-service || exit
# source ../venv/bin/activate
# python3 main.py &
# cd ..

# # Start Node.js backend
# echo "🚀 Starting Node.js backend on port 5000..."
# cd backend || exit
# npm install
# npm start &
# cd ..

# # Start React frontend
# echo "🌐 Starting frontend on port 5173..."
# cd frontend || exit
# npm install
# npm run dev &
# cd ..

# echo ""
# echo "✅ All services started. Visit 👉 http://localhost:5173"



#!/bin/bash

echo "🔁 Starting services for AI Travel Itinerary Planner..."

# Load environment variables from .env
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
  echo "✅ Environment variables loaded"
  echo "🔑 GOOGLE_API_KEY=********"
  echo "🔑 RAPIDAPI_KEY=********"
else
  echo "❌ .env file not found!"
  exit 1
fi

# Start Python backend (refactored version)
echo "🐍 Starting Python AI microservice on port 8000..."
cd ai-services-new || exit
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
cd ..

# Start Node.js backend
echo "🚀 Starting Node.js backend on port 5000..."
cd backend || exit
npm install
npm start &
cd ..

# Start React frontend
echo "🌐 Starting frontend on port 5173..."
cd frontend || exit
npm install
npm run dev &
cd ..

echo ""
echo "✅ All services started. Visit 👉 http://localhost:5173"
echo ""
echo "📊 Service URLs:"
echo "   • Frontend:  http://localhost:5173"
echo "   • Node.js:   http://localhost:5000"
echo "   • Python AI: http://localhost:8000"
echo "   • API Docs:  http://localhost:8000/docs"