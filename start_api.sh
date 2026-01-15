#!/bin/bash
# Startup script for OmniSense API

set -e

echo "========================================="
echo "Starting OmniSense API Services"
echo "========================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "Please edit .env with your configuration"
fi

# Check Docker installation
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Error: Docker Compose is not installed"
    exit 1
fi

# Create required directories
echo "Creating required directories..."
mkdir -p data logs cache

# Start services
echo "Starting Docker services..."
docker-compose -f docker-compose.api.yml up -d

# Wait for services to be healthy
echo "Waiting for services to start..."
sleep 10

# Check service health
echo "Checking service health..."

# Check Redis
if docker-compose -f docker-compose.api.yml exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo "✓ Redis is running"
else
    echo "✗ Redis is not responding"
fi

# Check API
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✓ API is running"
else
    echo "✗ API is not responding"
fi

# Check Celery worker
if docker-compose -f docker-compose.api.yml ps | grep celery_worker | grep Up > /dev/null; then
    echo "✓ Celery worker is running"
else
    echo "✗ Celery worker is not running"
fi

echo ""
echo "========================================="
echo "OmniSense API Services Started"
echo "========================================="
echo ""
echo "Access points:"
echo "  - API Documentation: http://localhost:8000/docs"
echo "  - Alternative Docs:  http://localhost:8000/redoc"
echo "  - Health Check:      http://localhost:8000/health"
echo "  - Flower (Celery):   http://localhost:5555"
echo "  - Prometheus:        http://localhost:9090"
echo "  - Grafana:           http://localhost:3000 (admin/admin)"
echo ""
echo "View logs:"
echo "  docker-compose -f docker-compose.api.yml logs -f"
echo ""
echo "Stop services:"
echo "  docker-compose -f docker-compose.api.yml down"
echo ""
