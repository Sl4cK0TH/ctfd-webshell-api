#!/bin/bash
# Deployment script for Webshell API
# Run this on your Digital Ocean droplet

set -e

echo "🚀 Webshell API Deployment Script"
echo "=================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo ./deploy.sh)"
    exit 1
fi

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "📦 Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    systemctl enable docker
    systemctl start docker
    echo "✅ Docker installed"
fi

# Install Docker Compose if not present
if ! command -v docker-compose &> /dev/null; then
    echo "📦 Installing Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose installed"
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    
    # Generate random API secret
    API_SECRET=$(openssl rand -hex 32)
    sed -i "s/change-me-to-a-secure-random-string/$API_SECRET/" .env
    
    echo "⚠️  Please edit .env file with your configuration!"
    echo "   Especially update:"
    echo "   - CTFD_URL"
    echo "   - WEBSHELL_BASE_URL"
    echo "   - ACME_EMAIL (for SSL certificates)"
    exit 0
fi

# Build webshell instance image
echo "🔨 Building webshell instance image..."
cd webshell-instance
docker build -t webshell-instance:latest .
cd ..

# Build and start services
echo "🔨 Building and starting services..."
docker-compose build
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check health
echo "🏥 Checking service health..."
if curl -s http://localhost:5000/health | grep -q "healthy"; then
    echo "✅ Webshell API is healthy!"
else
    echo "❌ Webshell API health check failed"
    docker-compose logs webshell-api
fi

echo ""
echo "=================================="
echo "🎉 Deployment complete!"
echo ""
echo "Services running:"
echo "  - Webshell API: http://localhost:5000"
echo "  - Traefik: https://localhost (ports 80/443)"
echo ""
echo "Next steps:"
echo "1. Configure DNS to point to this server"
echo "2. Update .env with correct domain names"
echo "3. Test the API with: curl http://localhost:5000/health"
echo ""
