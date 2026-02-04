# Webshell API Deployment Guide

Complete deployment guide for the Webshell Instance Spawner API on a Digital Ocean Droplet with Cloudflare DNS/SSL.

## Prerequisites

- Digital Ocean Droplet (Ubuntu 22.04 recommended, minimum 2GB RAM)
- Cloudflare account with your domain configured
- CTFd instance running at `https://2k26-rsuctf.nulbytez.live`

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│                           CLOUDFLARE                                    │
│   (DNS + SSL Termination + DDoS Protection)                            │
│                                                                         │
│   api.nullbytez.live ──────┐                                           │
│   webshell.nullbytez.live ─┼──▶ Droplet IP (Proxied, SSL: Flexible)   │
└────────────────────────────┴───────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        DIGITAL OCEAN DROPLET                            │
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │                         NGINX (:80)                              │  │
│   │   api.nullbytez.live ──▶ webshell-api:5000                      │  │
│   │   webshell.nullbytez.live/{team} ──▶ webshell-{team}:7681       │  │
│   └─────────────────────────────────────────────────────────────────┘  │
│                                      │                                  │
│   ┌──────────────────────┐    ┌──────┴───────────────────────────────┐ │
│   │   webshell-api       │    │   webshell-{team} containers         │ │
│   │   (Flask + Docker)   │    │   (Ubuntu + ttyd + CTF tools)        │ │
│   │   :5000              │    │   :7681 each                         │ │
│   └──────────────────────┘    └──────────────────────────────────────┘ │
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │                    Docker Network: webshell-network              │  │
│   └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

## Step 1: Create Digital Ocean Droplet

1. **Create Droplet:**
   - Image: Ubuntu 22.04 LTS
   - Size: Basic, 2GB RAM / 1 vCPU minimum (4GB recommended for many containers)
   - Region: Choose closest to your players
   - Authentication: SSH Key (recommended)

2. **Initial Server Setup:**
   ```bash
   # Update system
   apt update && apt upgrade -y
   
   # Install essential packages
   apt install -y curl git ufw
   
   # Configure firewall
   ufw allow OpenSSH
   ufw allow 80/tcp
   ufw --force enable
   ```

## Step 2: Configure Cloudflare DNS

1. **Add DNS Records:**
   
   | Type | Name | Content | Proxy Status |
   |------|------|---------|--------------|
   | A | api | `<DROPLET_IP>` | Proxied (Orange) |
   | A | webshell | `<DROPLET_IP>` | Proxied (Orange) |

2. **SSL/TLS Settings:**
   - Go to SSL/TLS → Overview
   - Set encryption mode to **Flexible**
   - This allows Cloudflare to handle HTTPS while your server runs HTTP

3. **Recommended Cloudflare Settings:**
   - SSL/TLS → Edge Certificates → Always Use HTTPS: **ON**
   - SSL/TLS → Edge Certificates → Automatic HTTPS Rewrites: **ON**
   - Security → Settings → Security Level: **Medium**
   - Speed → Optimization → Auto Minify: **OFF** (for WebSocket compatibility)

4. **WebSocket Support (Important!):**
   - Network → WebSockets: **ON**
   - This is required for ttyd terminal to work

## Step 3: Deploy Webshell API

1. **Clone or Copy Files to Server:**
   ```bash
   # Option A: Clone from git (if you have a repo)
   git clone https://your-repo.git /opt/webshell-api
   
   # Option B: SCP from local machine
   scp -r webshell-api/ root@<DROPLET_IP>:/opt/
   ```

2. **SSH into Droplet:**
   ```bash
   ssh root@<DROPLET_IP>
   cd /opt/webshell-api
   ```

3. **Install Docker:**
   ```bash
   curl -fsSL https://get.docker.com | sh
   systemctl enable docker
   systemctl start docker
   ```

4. **Install Docker Compose:**
   ```bash
   curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   chmod +x /usr/local/bin/docker-compose
   ```

5. **Configure Environment:**
   ```bash
   cp .env.example .env
   nano .env
   ```
   
   Update these values:
   ```env
   CTFD_URL=https://2k26-rsuctf.nulbytez.live
   WEBSHELL_BASE_URL=https://webshell.nullbytez.live
   API_SECRET=<generate-random-string>
   ```
   
   Generate a random API secret:
   ```bash
   openssl rand -hex 32
   ```

6. **Build Webshell Instance Image:**
   ```bash
   cd webshell-instance
   docker build -t webshell-instance:latest .
   cd ..
   ```

7. **Start Services:**
   ```bash
   docker-compose -f docker-compose.nginx.yml up -d
   ```

## Step 4: Verify Deployment

1. **Check Services Are Running:**
   ```bash
   docker-compose -f docker-compose.nginx.yml ps
   ```
   
   Expected output:
   ```
   NAME              STATUS
   webshell-api      Up (healthy)
   nginx             Up
   webshell-cleanup  Up
   ```

2. **Check API Health:**
   ```bash
   curl http://localhost:5000/health
   ```
   
   Expected: `{"status":"healthy","service":"webshell-api"}`

3. **Test from External (via Cloudflare):**
   ```bash
   curl https://api.nullbytez.live/health
   ```

4. **Check Logs if Issues:**
   ```bash
   docker-compose -f docker-compose.nginx.yml logs -f webshell-api
   docker-compose -f docker-compose.nginx.yml logs -f nginx
   ```

## Step 5: Add CTFd Page

1. **Login to CTFd Admin Panel:**
   - Go to `https://2k26-rsuctf.nulbytez.live/admin/pages`

2. **Create New Page:**
   - Title: `Webshell`
   - Route: `/webshell`
   - Content: Paste contents of `webshell-page-template.html`
   - Format: HTML

3. **Update API URL in Template:**
   - Find: `const API_URL = 'https://api.nullbytez.live';`
   - Ensure it matches your actual API domain

4. **Add to Navigation (Optional):**
   - Go to Config → Theme
   - Add link to `/webshell` in navigation

## Troubleshooting

### Container won't start
```bash
# Check Docker logs
docker logs webshell-api

# Check if image exists
docker images | grep webshell-instance

# Rebuild if needed
cd webshell-instance && docker build -t webshell-instance:latest .
```

### WebSocket connection fails
- Ensure Cloudflare WebSocket is enabled (Network → WebSockets)
- Check nginx logs: `docker logs nginx`
- Verify proxy headers are being passed

### Token validation fails
```bash
# Test CTFd API directly
curl -H "Authorization: Token YOUR_CTFD_TOKEN" \
     https://2k26-rsuctf.nulbytez.live/api/v1/users/me
```

### CORS errors in browser
- Check nginx CORS headers are present
- Verify API_URL in frontend matches actual domain

### Container cleanup not working
```bash
# Manual cleanup
curl -X POST -H "X-API-Secret: YOUR_SECRET" \
     http://localhost:5000/api/admin/cleanup

# Check cleanup service logs
docker logs webshell-cleanup
```

## Maintenance Commands

### View All Running Webshell Containers
```bash
docker ps --filter "name=webshell-"
```

### Stop All Webshell Containers
```bash
docker stop $(docker ps -q --filter "name=webshell-")
```

### Remove All Webshell Containers
```bash
docker rm $(docker ps -aq --filter "name=webshell-")
```

### Update and Restart Services
```bash
cd /opt/webshell-api
git pull  # if using git
docker-compose -f docker-compose.nginx.yml build --no-cache
docker-compose -f docker-compose.nginx.yml up -d
```

### View Resource Usage
```bash
docker stats --no-stream
```

### Backup Container Data (if needed)
```bash
# Note: By default, containers are ephemeral
# Add volume mounts to docker_manager.py if persistence is needed
```

## Security Checklist

- [ ] Firewall only allows ports 22 (SSH) and 80 (HTTP)
- [ ] API_SECRET is a strong random string
- [ ] Cloudflare proxy is enabled (orange cloud)
- [ ] SSH uses key authentication (no passwords)
- [ ] Regular system updates scheduled
- [ ] Container resource limits are appropriate

## Scaling Considerations

For larger CTF events (100+ teams):

1. **Increase Droplet Size:**
   - 8GB RAM / 4 vCPU for ~50 concurrent containers
   - 16GB RAM / 8 vCPU for ~100 concurrent containers

2. **Reduce Container Resources:**
   ```env
   CONTAINER_MEMORY_LIMIT=256m
   CONTAINER_CPU_LIMIT=0.25
   ```

3. **Shorter Timeout:**
   ```env
   CONTAINER_TIMEOUT_HOURS=12
   ```

4. **Monitor Resource Usage:**
   ```bash
   htop
   docker stats
   ```

## Support

For issues specific to this deployment:
1. Check logs: `docker-compose -f docker-compose.nginx.yml logs`
2. Verify Cloudflare settings
3. Test API endpoints individually
4. Check CTFd token validity
