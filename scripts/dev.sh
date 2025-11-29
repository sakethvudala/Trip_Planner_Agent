#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to display help
show_help() {
    echo "Usage: ./dev.sh [command] [options]"
    echo ""
    echo "Commands:"
    echo "  setup             Set up the development environment"
    echo "  test              Run tests"
    echo "  lint              Run linters"
    echo "  format            Format code with black"
    echo "  run               Run the application"
    echo "  docker:build      Build Docker image"
    echo "  docker:run        Run the application in Docker"
    echo "  docker:clean      Remove Docker containers and images"
    echo "  help              Show this help message"
    echo ""
    exit 1
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if running in a virtual environment
in_venv() {
    [[ -n "$VIRTUAL_ENV" ]]
}

# Function to set up the development environment
setup() {
    echo -e "${GREEN}Setting up development environment...${NC}"
    
    # Check if Python 3.9+ is installed
    if ! command_exists python3; then
        echo -e "${RED}Python 3.9+ is required but not installed.${NC}"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    if [[ "$(echo "$PYTHON_VERSION < 3.9" | bc -l)" -eq 1 ]]; then
        echo -e "${RED}Python 3.9 or higher is required. Found Python $PYTHON_VERSION${NC}"
        exit 1
    fi
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    elif [ -f "venv/Scripts/activate" ]; then
        source venv/Scripts/activate
    else
        echo -e "${RED}Failed to activate virtual environment.${NC}"
        exit 1
    fi
    
    # Upgrade pip
    echo -e "${YELLOW}Upgrading pip...${NC}"
    pip install --upgrade pip
    
    # Install dependencies
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -r requirements.txt
    
    # Install development dependencies
    echo -e "${YELLOW}Installing development dependencies...${NC}"
    pip install -r requirements-dev.txt
    
    # Create .env file if it doesn't exist
    if [ ! -f ".env" ]; then
        echo -e "${YELLOW}Creating .env file...${NC}"
        cp .env.example .env
        echo -e "${YELLOW}Please update the .env file with your configuration.${NC}"
    fi
    
    echo -e "${GREEN}Setup complete!${NC}"
    echo -e "To activate the virtual environment, run: source venv/bin/activate"
}

# Function to run tests
test() {
    if ! in_venv; then
        echo -e "${YELLOW}Activating virtual environment...${NC}"
        if [ -f "venv/bin/activate" ]; then
            source venv/bin/activate
        elif [ -f "venv/Scripts/activate" ]; then
            source venv/Scripts/activate
        else
            echo -e "${RED}Virtual environment not found. Run './dev.sh setup' first.${NC}"
            exit 1
        fi
    fi
    
    echo -e "${GREEN}Running tests...${NC}"
    python -m pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=xml
}

# Function to run linters
lint() {
    if ! in_venv; then
        echo -e "${YELLOW}Activating virtual environment...${NC}"
        if [ -f "venv/bin/activate" ]; then
            source venv/bin/activate
        elif [ -f "venv/Scripts/activate" ]; then
            source venv/Scripts/activate
        else
            echo -e "${RED}Virtual environment not found. Run './dev.sh setup' first.${NC}"
            exit 1
        fi
    fi
    
    echo -e "${GREEN}Running flake8...${NC}"
    flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
    flake8 . --count --max-complexity=10 --max-line-length=127 --statistics
    
    echo -e "\n${GREEN}Running black...${NC}"
    black --check --diff .
}

# Function to format code
format() {
    if ! in_venv; then
        echo -e "${YELLOW}Activating virtual environment...${NC}"
        if [ -f "venv/bin/activate" ]; then
            source venv/bin/activate
        elif [ -f "venv/Scripts/activate" ]; then
            source venv/Scripts/activate
        else
            echo -e "${RED}Virtual environment not found. Run './dev.sh setup' first.${NC}"
            exit 1
        fi
    fi
    
    echo -e "${GREEN}Formatting code with black...${NC}"
    black .
}

# Function to run the application
run() {
    if ! in_venv; then
        echo -e "${YELLOW}Activating virtual environment...${NC}"
        if [ -f "venv/bin/activate" ]; then
            source venv/bin/activate
        elif [ -f "venv/Scripts/activate" ]; then
            source venv/Scripts/activate
        else
            echo -e "${RED}Virtual environment not found. Run './dev.sh setup' first.${NC}"
            exit 1
        fi
    fi
    
    echo -e "${GREEN}Starting application...${NC}"
    uvicorn app.main:app --reload
}

# Function to build Docker image
docker_build() {
    if ! command_exists docker; then
        echo -e "${RED}Docker is not installed. Please install Docker and try again.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Building Docker image...${NC}"
    docker-compose build
}

# Function to run the application in Docker
docker_run() {
    if ! command_exists docker; then
        echo -e "${RED}Docker is not installed. Please install Docker and try again.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Starting application in Docker...${NC}"
    docker-compose up -d
    
    echo -e "\n${GREEN}Application is running at http://localhost:8000${NC}"
    echo -e "API documentation: http://localhost:8000/docs"
    echo -e "\nTo view logs, run: docker-compose logs -f"
    echo -e "To stop the application, run: ./dev.sh docker:clean"
}

# Function to clean up Docker resources
docker_clean() {
    if ! command_exists docker; then
        echo -e "${RED}Docker is not installed.${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}Stopping and removing containers...${NC}"
    docker-compose down --remove-orphans
    
    echo -e "\n${YELLOW}Removing unused Docker resources...${NC}"
    docker system prune -f
}

# Main script
case "$1" in
    setup)
        setup
        ;;
    test)
        test
        ;;
    lint)
        lint
        ;;
    format)
        format
        ;;
    run)
        run
        ;;
    docker:build)
        docker_build
        ;;
    docker:run)
        docker_run
        ;;
    docker:clean)
        docker_clean
        ;;
    help|*)
        show_help
        ;;
esac
