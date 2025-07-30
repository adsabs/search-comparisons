#!/bin/bash

# Start Ollama Server for Search Comparisons Tool
# This script starts Ollama and optionally pulls a specific model

# Default configuration
DEFAULT_MODEL="qwen2:7b"
OLLAMA_HOST="0.0.0.0"
OLLAMA_PORT="11434"

# Available models based on config.py
AVAILABLE_MODELS=(
    "qwen2:7b"           # Default - Efficient model with strong reasoning
    "llama2:7b-chat"     # Optimized for dialogue and instruction following  
    "mistral:7b-instruct-v0.2"  # Efficient model with good reasoning
    "gemma:2b-it"        # Lightweight model with good performance
)

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

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -m, --model MODEL    Specify model to use (default: $DEFAULT_MODEL)"
    echo "  -l, --list          List available models"
    echo "  -s, --status        Check Ollama server status"
    echo "  -k, --kill          Stop Ollama server"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "Available models:"
    for model in "${AVAILABLE_MODELS[@]}"; do
        echo "  - $model"
    done
    echo ""
    echo "Examples:"
    echo "  $0                           # Start with default model ($DEFAULT_MODEL)"
    echo "  $0 -m mistral:7b-instruct-v0.2  # Start with Mistral model"
    echo "  $0 -s                        # Check server status"
    echo "  $0 -k                        # Stop server"
}

# Function to check if Ollama is installed
check_ollama_installed() {
    if ! command -v ollama &> /dev/null; then
        print_error "Ollama is not installed!"
        echo ""
        echo "Please install Ollama from: https://ollama.ai/download"
        echo ""
        echo "For Ubuntu/Debian:"
        echo "  curl -fsSL https://ollama.ai/install.sh | sh"
        echo ""
        exit 1
    fi
}

# Function to check if Ollama server is running
check_ollama_running() {
    if curl -s "http://localhost:$OLLAMA_PORT/api/tags" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to get Ollama server status
get_status() {
    print_header "Checking Ollama Server Status"
    
    if check_ollama_running; then
        print_status "Ollama server is running on port $OLLAMA_PORT"
        
        # Get list of installed models
        print_status "Installed models:"
        ollama list 2>/dev/null | grep -v "NAME" | while read -r model_line; do
            model_name=$(echo "$model_line" | awk '{print $1}')
            if [ -n "$model_name" ]; then
                echo "  - $model_name"
            fi
        done
    else
        print_warning "Ollama server is not running"
    fi
}

# Function to stop Ollama server
stop_server() {
    print_header "Stopping Ollama Server"
    
    # Try to stop gracefully first
    if pgrep -f ollama > /dev/null; then
        print_status "Stopping Ollama processes..."
        pkill -f ollama
        sleep 2
        
        # Force kill if still running
        if pgrep -f ollama > /dev/null; then
            print_warning "Force killing remaining Ollama processes..."
            pkill -9 -f ollama
        fi
        
        print_status "Ollama server stopped"
    else
        print_warning "Ollama server was not running"
    fi
}

# Function to pull model if not available
ensure_model_available() {
    local model="$1"
    
    print_status "Checking if model '$model' is available..."
    
    if ollama list | grep -q "^$model"; then
        print_status "Model '$model' is already available"
    else
        print_warning "Model '$model' not found locally"
        print_status "Pulling model '$model'... (this may take several minutes)"
        
        if ollama pull "$model"; then
            print_status "Successfully pulled model '$model'"
        else
            print_error "Failed to pull model '$model'"
            exit 1
        fi
    fi
}

# Function to start Ollama server
start_server() {
    local model="$1"
    
    print_header "Starting Ollama Server for Search Comparisons"
    print_status "Model: $model"
    print_status "Host: $OLLAMA_HOST"
    print_status "Port: $OLLAMA_PORT"
    echo ""
    
    # Check if already running
    if check_ollama_running; then
        print_warning "Ollama server is already running on port $OLLAMA_PORT"
        print_status "You can check status with: $0 -s"
        return 0
    fi
    
    # Set environment variables
    export OLLAMA_HOST="$OLLAMA_HOST:$OLLAMA_PORT"
    
    # Start Ollama server in background
    print_status "Starting Ollama server..."
    nohup ollama serve > ollama.log 2>&1 &
    local ollama_pid=$!
    
    # Wait for server to start
    print_status "Waiting for server to start..."
    local attempts=0
    local max_attempts=30
    
    while [ $attempts -lt $max_attempts ]; do
        if check_ollama_running; then
            print_status "Ollama server started successfully (PID: $ollama_pid)"
            break
        fi
        
        sleep 1
        attempts=$((attempts + 1))
        
        if [ $attempts -eq $max_attempts ]; then
            print_error "Failed to start Ollama server after $max_attempts seconds"
            exit 1
        fi
    done
    
    # Ensure the specified model is available
    ensure_model_available "$model"
    
    echo ""
    print_status "Ollama server is ready!"
    print_status "API endpoint: http://localhost:$OLLAMA_PORT"
    print_status "Model: $model"
    print_status "Log file: ollama.log"
    echo ""
    print_status "You can now run query intent searches in the Search Comparisons tool"
    print_status "To stop the server, run: $0 -k"
}

# Parse command line arguments
MODEL="$DEFAULT_MODEL"

while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--model)
            MODEL="$2"
            shift 2
            ;;
        -l|--list)
            echo "Available models:"
            for model in "${AVAILABLE_MODELS[@]}"; do
                echo "  - $model"
            done
            exit 0
            ;;
        -s|--status)
            check_ollama_installed
            get_status
            exit 0
            ;;
        -k|--kill)
            stop_server
            exit 0
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate model selection
if [[ ! " ${AVAILABLE_MODELS[@]} " =~ " ${MODEL} " ]]; then
    print_error "Invalid model: $MODEL"
    echo ""
    echo "Available models:"
    for model in "${AVAILABLE_MODELS[@]}"; do
        echo "  - $model"
    done
    exit 1
fi

# Main execution
check_ollama_installed
start_server "$MODEL"
