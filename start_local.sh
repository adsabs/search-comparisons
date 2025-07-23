#!/bin/bash

# Script to start both frontend and backend development servers

# Set environment to local
export APP_ENVIRONMENT=local
export DEBUG=true

# Load local environment variables if .env.local exists
if [ -f .env.local ]; then
  echo "Loading environment variables from .env.local"
  set -a
  source .env.local
  set +a
else
  echo "Warning: .env.local not found, using default environment"
fi

# Start backend in background
echo "Starting backend server..."
cd backend
source venv/bin/activate && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001 &
BACKEND_PID=$!
cd ..

# Give backend time to start
echo "Waiting for backend to start..."
sleep 3

# Test backend connection
echo "Testing backend connection..."
if curl -s http://localhost:8001/health > /dev/null; then
  echo "✅ Backend is running on port 8001"
else
  echo "❌ Backend failed to start on port 8001"
  exit 1
fi

# Ensure frontend environment is set
echo "Setting up frontend environment..."
cd frontend
if [ ! -f .env ]; then
  echo "REACT_APP_API_URL=http://localhost:8001" > .env
  echo "Created frontend/.env with API URL"
fi

# Start frontend in foreground 
echo "Starting frontend server..."
PORT=3001 npm start &
FRONTEND_PID=$!
cd ..

# Function to handle exit
function cleanup {
  echo "Shutting down servers..."
  kill $BACKEND_PID
  kill $FRONTEND_PID
  exit 0
}

# Register cleanup function on SIGINT (Ctrl+C)
trap cleanup SIGINT

# Keep script running
echo ""
echo "🚀 Search Comparisons Tool is running:"
echo "   Frontend: http://localhost:3001"
echo "   Backend:  http://localhost:8001"
echo "   API Docs: http://localhost:8001/docs"
echo ""
echo "Press Ctrl+C to stop both servers."
wait 