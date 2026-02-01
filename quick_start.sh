#!/bin/bash
# Quick start script for Padel Booking System

set -e

echo "🎾 Padel Court Booking System - Quick Start"
echo "============================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "📝 Creating .env from example..."
    cp .env.example .env
    echo ""
    echo "⚠️  Please edit .env with your credentials:"
    echo "   - ESTELLE_USERNAME"
    echo "   - ESTELLE_PASSWORD"
    echo "   - DISCORD_WEBHOOK_URL"
    echo ""
    echo "Then run this script again."
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running!"
    echo "Please start Docker and try again."
    exit 1
fi

echo "✅ Docker is running"
echo "✅ .env file found"
echo ""

# Build and start
echo "🏗️  Building Docker image..."
docker-compose build

echo ""
echo "🚀 Starting application..."
docker-compose up -d

echo ""
echo "⏳ Waiting for application to start..."
sleep 5

# Check health
echo "🏥 Checking health..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Application is healthy!"
else
    echo "⚠️  Application may not be ready yet"
    echo "   Check logs with: docker-compose logs -f"
fi

echo ""
echo "📊 Application is running!"
echo ""
echo "🔗 API Endpoints:"
echo "   http://localhost:8000          - API docs"
echo "   http://localhost:8000/health   - Health check"
echo "   http://localhost:8000/stats    - Statistics"
echo ""
echo "📝 Common Commands:"
echo "   docker-compose logs -f         - View logs"
echo "   docker-compose ps              - Check status"
echo "   docker-compose down            - Stop application"
echo ""
echo "📤 Upload bookings:"
echo "   curl -X POST http://localhost:8000/bookings/upload \\"
echo "     -F 'file=@example_bookings.csv'"
echo ""
echo "🧪 Test notification:"
echo "   curl -X POST http://localhost:8000/test/notification"
echo ""

# Show logs
read -p "Show logs? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker-compose logs -f
fi
