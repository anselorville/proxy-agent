#!/bin/bash

set -e

echo "=== Setup China Stock Proxy ==="

if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit .env file with your configuration"
fi

echo "Creating necessary directories..."
mkdir -p logs
mkdir -p data/postgres
mkdir -p data/redis

echo "Installing Python dependencies..."
if [ -d "venv" ]; then
    echo "Virtual environment already exists"
else
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
fi

echo "Setting up database migrations..."
if [ -d "migrations" ]; then
    echo "Migrations directory exists"
else
    mkdir -p migrations
fi

echo "Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "Building Docker images..."
docker-compose build

echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration"
echo "2. Run './deploy/deploy.sh' to start the application"
echo "3. Visit http://localhost:8000/docs for API documentation"
