# Webshell Instance Spawner API

A secure API service for CTFd that allows players to spawn personal Linux webshell containers using their CTFd tokens.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│                 │     │                  │     │                 │
│  CTFd Platform  │────▶│  Webshell API    │────▶│  Docker Engine  │
│  (validates     │     │  (manages        │     │  (spawns        │
│   tokens)       │     │   containers)    │     │   containers)   │
│                 │     │                  │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │    Traefik       │
                        │  (reverse proxy, │
                        │   SSL, routing)  │
                        └──────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │ Webshell Instance│
                        │ (ttyd + tools)   │
                        └──────────────────┘
```

## Features

- **CTFd Token Authentication**: Validates player tokens against your CTFd instance
- **Per-Team Containers**: Each team gets their own isolated Linux environment
- **Pre-installed CTF Tools**: Python, pwntools, nmap, gdb, and more
- **Automatic Cleanup**: Expired containers are removed after 24 hours
- **Resource Limits**: Memory and CPU limits prevent resource abuse
- **SSL/TLS**: Automatic HTTPS via Let's Encrypt

## Quick Start

### 1. Clone and Configure

```bash
cd webshell-api
cp .env.example .env
nano .env  # Edit configuration
```

### 2. Deploy

```bash
chmod +x deploy.sh
sudo ./deploy.sh
```

### 3. Configure DNS

Point these domains to your droplet:
- `api.nullbytez.live` → Webshell API
- `webshell.nullbytez.live` → Webshell instances (via Traefik)

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CTFD_URL` | Your CTFd instance URL | `https://2k26-rsuctf.nulbytez.live` |
| `WEBSHELL_BASE_URL` | Base URL for webshell access | `https://webshell.nullbytez.live` |
| `CONTAINER_MEMORY_LIMIT` | Memory limit per container | `512m` |
| `CONTAINER_CPU_LIMIT` | CPU limit (0.5 = 50%) | `0.5` |
| `CONTAINER_TIMEOUT_HOURS` | Container expiry time | `24` |
| `API_SECRET` | Admin API authentication | (generate random) |
| `ACME_EMAIL` | Email for Let's Encrypt | `admin@nulbytez.live` |

## API Endpoints

### Public Endpoints

#### `POST /api/validate-token`
Validate a CTFd token and get user/team info.

```json
// Request
{ "token": "ctfd_..." }

// Response
{
  "success": true,
  "user_id": 123,
  "username": "player1",
  "team_id": 45,
  "team_name": "HackerSquad"
}
```

#### `POST /api/status`
Check if a team has an active container.

```json
// Request
{ "team_name": "HackerSquad" }

// Response
{
  "success": true,
  "has_container": true,
  "status": "running",
  "webshell_url": "https://webshell.nullbytez.live/hackersquad"
}
```

#### `POST /api/create`
Create a new webshell container.

```json
// Request
{
  "team_name": "HackerSquad",
  "username": "player1"
}

// Response
{
  "success": true,
  "message": "Container created successfully",
  "webshell_url": "https://webshell.nullbytez.live/hackersquad"
}
```

#### `POST /api/delete`
Stop and remove a container.

```json
// Request
{ "team_name": "HackerSquad" }

// Response
{
  "success": true,
  "message": "Container stopped successfully"
}
```

### Admin Endpoints

Requires `X-API-Secret` header.

#### `GET /api/admin/list`
List all active containers.

#### `POST /api/admin/cleanup`
Remove expired containers.

## Webshell Container

Each container includes:

- **Languages**: Python 3, GCC, G++
- **CTF Tools**: pwntools, pycryptodome, z3-solver, angr, ropper
- **Network**: nmap, netcat, socat, tcpdump, curl, wget
- **Binary**: gdb, binutils, file, xxd, hexedit
- **Editors**: vim, nano
- **Utilities**: tmux, git, jq, unzip

## Security Considerations

1. **Container Isolation**: Each container runs with dropped capabilities
2. **Resource Limits**: Memory, CPU, and PID limits prevent DoS
3. **Network Isolation**: Containers are on a separate Docker network
4. **No Privileged Mode**: Containers cannot access host resources
5. **Token Validation**: All requests require valid CTFd tokens

## Customization

### Adding Tools to Webshell

Edit `webshell-instance/Dockerfile`:

```dockerfile
RUN apt-get install -y your-package
```

### Changing Resource Limits

Edit `.env`:

```
CONTAINER_MEMORY_LIMIT=1g
CONTAINER_CPU_LIMIT=1.0
```

## Troubleshooting

### Check logs

```bash
docker-compose logs -f webshell-api
docker-compose logs -f traefik
```

### Restart services

```bash
docker-compose restart
```

### Rebuild after changes

```bash
docker-compose build --no-cache
docker-compose up -d
```

## License

MIT License - RSU CTF 2026
