#!/bin/bash

echo "Stopping servers..."

# Kill by PID files if they exist
if [ -f backend.pid ]; then
  BACKEND_PID=$(cat backend.pid)
  if kill -0 $BACKEND_PID 2>/dev/null; then
    kill $BACKEND_PID
    echo "Stopped backend (PID: $BACKEND_PID)"
  fi
  rm backend.pid
fi

if [ -f frontend.pid ]; then
  FRONTEND_PID=$(cat frontend.pid)
  if kill -0 $FRONTEND_PID 2>/dev/null; then
    kill $FRONTEND_PID
    echo "Stopped frontend (PID: $FRONTEND_PID)"
  fi
  rm frontend.pid
fi

# Fallback: kill by process name
pkill -f "uvicorn.*app.main:app"
pkill -f "react-scripts start"

# Kill by port
lsof -ti:8001 | xargs -r kill
lsof -ti:3001 | xargs -r kill

echo "Servers stopped."
