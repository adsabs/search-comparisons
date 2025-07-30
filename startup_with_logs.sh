#!/bin/bash

# Script to start servers and show logs for troubleshooting, then exit cleanly

# Set environment to local
export APP_ENVIRONMENT=local
export DEBUG=true

# Load local environment variables if .env.local exists
if [ -f .env.local ]; then
  echo "Loading environment variables from .env.local"
  # Use safer env loading to avoid command execution
  while IFS='=' read -r key value; do
    # Skip comments and empty lines
    [[ $key =~ ^[[:space:]]*# ]] && continue
    [[ -z $key ]] && continue
    # Only export valid variable names
    if [[ $key =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
      export "$key=$value"
    fi
  done < .env.local
else
  echo "Warning: .env.local not found, using default environment"
fi

# Start backend in background
echo "Starting backend server..."
cd backend
nohup bash -c "source venv/bin/activate && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001" > ../backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > ../backend.pid
cd ..

# Give backend time to start
echo "Waiting for backend to start..."
sleep 5

# Test backend connection with retry
echo "Testing backend connection..."
for i in {1..5}; do
  if curl -s http://localhost:8001/health > /dev/null; then
    echo "✅ Backend is running on port 8001 (PID: $BACKEND_PID)"
    break
  else
    echo "Attempt $i/5: Backend not ready, waiting..."
    sleep 2
  fi
  if [ $i -eq 5 ]; then
    echo "❌ Backend failed to start on port 8001"
    echo "Backend logs:"
    cat backend.log | tail -20
    exit 1
  fi
done

# Ensure frontend environment is set
echo "Setting up frontend environment..."
cd frontend
if [ ! -f .env ]; then
  echo "REACT_APP_API_URL=http://localhost:8001" > .env
  echo "Created frontend/.env with API URL"
fi

# Start frontend in background 
echo "Starting frontend server..."
nohup bash -c "PORT=3001 npm start" > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../frontend.pid
cd ..

echo ""
echo "🚀 Search Comparisons Tool starting up:"
echo "   Backend:  http://localhost:8001 (PID: $BACKEND_PID)"
echo "   Frontend: http://localhost:3001 (PID: $FRONTEND_PID)"
echo "   API Docs: http://localhost:8001/docs"
echo ""
echo "Showing startup logs for 60 seconds (both servers will keep running)..."
echo "To stop servers later: ./stop_servers.sh"
echo "=============================================================================="

# Show logs for 60 seconds, then exit
timeout 60s tail -f backend.log frontend.log 2>/dev/null || true

echo ""
echo "=============================================================================="
echo "Startup complete! Servers are running in background."

# Final check on both services
echo ""
echo "Final status check:"
if curl -s http://localhost:8001/health > /dev/null; then
  echo "✅ Backend is healthy at http://localhost:8001"
else
  echo "❌ Backend may have issues - check backend.log"
fi

if curl -s http://localhost:3001 > /dev/null; then
  echo "✅ Frontend is accessible at http://localhost:3001"
else
  echo "⚠️  Frontend may still be starting - check frontend.log"
fi

echo ""
echo "To view logs later:"
echo "   Backend:  tail -f backend.log"
echo "   Frontend: tail -f frontend.log"
echo "   Both:     tail -f backend.log frontend.log"
echo ""
echo "To stop servers: ./stop_servers.sh"
