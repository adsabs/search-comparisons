#!/bin/bash

# Stop Ollama Server for Search Comparisons Tool

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[OLLAMA]${NC} $1"
}

# Function to check if Ollama server is running
check_ollama_running() {
    if curl -s "http://localhost:11434/api/tags" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to stop Ollama server
stop_server() {
    print_header "Stopping Ollama Server"
    
    # Check if server is running
    if ! check_ollama_running; then
        print_warning "Ollama server is not running"
        return 0
    fi
    
    print_status "Stopping Ollama server..."
    
    # Try to stop gracefully first
    if pgrep -f ollama > /dev/null; then
        print_status "Sending termination signal to Ollama processes..."
        pkill -TERM -f ollama
        
        # Wait a bit for graceful shutdown
        sleep 3
        
        # Check if still running
        if pgrep -f ollama > /dev/null; then
            print_warning "Graceful shutdown failed, force killing..."
            pkill -9 -f ollama
            sleep 1
        fi
        
        # Final check
        if ! pgrep -f ollama > /dev/null; then
            print_status "Ollama server stopped successfully"
        else
            print_error "Failed to stop Ollama server"
            return 1
        fi
    else
        print_warning "No Ollama processes found"
    fi
    
    # Clean up log file if it exists
    if [ -f "ollama.log" ]; then
        print_status "Cleaning up log file..."
        rm -f ollama.log
    fi
}

# Main execution
stop_server
