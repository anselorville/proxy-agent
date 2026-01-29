#!/bin/bash

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "=== Deploying China Stock Proxy ==="

if [ ! -f .env ]; then
    echo "Error: .env file not found"
    echo "Please run ./deploy/setup.sh first"
    exit 1
fi

echo "Stopping existing containers..."
docker-compose down

echo "Pulling latest images..."
docker-compose pull postgres redis || true

echo "Building application image..."
docker-compose build app celery_worker celery_beat

echo "Starting services..."
docker-compose up -d postgres redis

echo "Waiting for database to be ready..."
sleep 10

echo "Starting application services..."
docker-compose up -d app celery_worker celery_beat

echo "Checking service status..."
docker-compose ps

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Services:"
echo "  - FastAPI: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo "  - Health: http://localhost:8000/health"
echo "  - Metrics: http://localhost:8000/metrics"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f"
echo ""
echo "To stop services:"
echo "  docker-compose down"
