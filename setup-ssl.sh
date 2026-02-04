#!/bin/bash
# Setup SSL certificates using Certbot
# Run this after initial deployment

set -e

DOMAIN_API=${1:-api.nullbytez.live}
DOMAIN_SHELL=${2:-webshell.nullbytez.live}
EMAIL=${3:-admin@nullbytez.live}

echo "🔐 Setting up SSL certificates"
echo "API Domain: $DOMAIN_API"
echo "Shell Domain: $DOMAIN_SHELL"
echo "Email: $EMAIL"

# Stop nginx temporarily
docker-compose stop nginx 2>/dev/null || true

# Get certificates
docker run --rm -it \
    -v "$(pwd)/letsencrypt:/etc/letsencrypt" \
    -v "$(pwd)/certbot-www:/var/www/certbot" \
    -p 80:80 \
    certbot/certbot certonly \
    --standalone \
    --agree-tos \
    --no-eff-email \
    --email "$EMAIL" \
    -d "$DOMAIN_API" \
    -d "$DOMAIN_SHELL"

# Restart nginx
docker-compose up -d nginx

echo "✅ SSL certificates obtained successfully!"
