#!/bin/bash

# Script to start both frontend and backend development servers
# This version builds the frontend once instead of using hot reload

# Set environment to local
export APP_ENVIRONMENT=local
export DEBUG=true

# Load NVM and Node.js
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# Load local environment variables if .env.local exists
if [ -f .env.local ]; then
  echo "Loading environment variables from .env.local"
  set -a
  source .env.local
  set +a
else
  echo "Warning: .env.local not found, using default environment"
fi

# Build frontend
echo "Building frontend..."
cd frontend
npm run build
cd ..

# Start backend in background
echo "Starting backend server..."
cd backend
source venv/bin/activate && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Give backend time to start
sleep 2

# Start frontend build server
echo "Starting frontend build server..."
cd frontend
npx serve -s build -l 3000 &
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
echo "Servers are running:"
echo "- Backend: http://localhost:8000"
echo "- Frontend: http://localhost:3000"
echo "Press Ctrl+C to stop."
wait
