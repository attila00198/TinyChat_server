# Docker Setup for TinyChat Server

This guide explains how to build and run the TinyChat server using Docker.

## Prerequisites

- Docker and Docker Compose installed
- (Optional) SSL certificates for TLS mode (Certbot, self-signed, or other)

## Quick Start with Docker Compose

The easiest way to run the server:

```bash
docker-compose up -d
```

This starts the server on `ws://0.0.0.0:8765` without TLS. To view logs:

```bash
docker-compose logs -f tinychat
```

To stop:

```bash
docker-compose down
```

## Building the Image

Build manually with:

```bash
docker build -t tinychat-server:latest .
```

## Running with Docker Run

### Without TLS (Plain WebSocket)

```bash
docker run -d \
  --name tinychat-server \
  -p 8765:8765 \
  -e MOD_PASSWORD=your_secure_password \
  tinychat-server:latest
```

View logs:

```bash
docker logs -f tinychat-server
```

### With TLS (Secure WebSocket)

If you have SSL certificates (e.g., from Certbot), mount them into the container:

```bash
docker run -d \
  --name tinychat-server-tls \
  -p 8765:8765 \
  -e USE_SSL=true \
  -e SSL_CERT_PATH=/certs/fullchain.pem \
  -e SSL_KEY_PATH=/certs/privkey.pem \
  -e MOD_PASSWORD=your_secure_password \
  -v /path/to/certs:/certs:ro \
  tinychat-server:latest
```

Replace `/path/to/certs` with your actual certificate path. The `:ro` flag mounts as read-only.

**Example with Certbot:**

```bash
docker run -d \
  --name tinychat-server-tls \
  -p 8765:8765 \
  -e USE_SSL=true \
  -e SSL_CERT_PATH=/certs/fullchain.pem \
  -e SSL_KEY_PATH=/certs/privkey.pem \
  -e MOD_PASSWORD=your_secure_password \
  -v /etc/letsencrypt/live/yourdomain.com:/certs:ro \
  tinychat-server:latest
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8765` | Server port |
| `MOD_PASSWORD` | `admin123` | Moderator login password (change this!) |
| `USE_SSL` | `false` | Enable TLS/SSL (`true` or `false`) |
| `SSL_CERT_PATH` | (none) | Path to SSL certificate (PEM) inside container |
| `SSL_KEY_PATH` | (none) | Path to SSL key (PEM) inside container |

## Docker Compose Configuration

The `docker-compose.yml` includes:

- Service definition with build context
- Port mapping (`8765:8765`)
- Environment variables for configuration
- Optional volume mount for certificates (commented out)
- Healthcheck to monitor server status
- Logging configuration (10MB max per file, 3 files retained)
- Restart policy (`unless-stopped`)

To enable TLS in `docker-compose.yml`, uncomment the relevant sections:

```yaml
environment:
  - USE_SSL=true
  - SSL_CERT_PATH=/certs/fullchain.pem
  - SSL_KEY_PATH=/certs/privkey.pem

volumes:
  - /etc/letsencrypt/live/yourdomain.com:/certs:ro
```

Then run:

```bash
docker-compose up -d
```

## Testing the Server

Once running, connect a WebSocket client:

```python
import asyncio
import websockets

async def test():
    uri = "ws://localhost:8765"  # or wss:// for TLS
    async with websockets.connect(uri) as websocket:
        await websocket.send("Hello, TinyChat!")
        response = await websocket.recv()
        print(f"Received: {response}")

asyncio.run(test())
```

Or test with curl (requires websocat):

```bash
websocat ws://localhost:8765
```

## Cleaning Up

Remove containers and images:

```bash
# Stop and remove containers
docker-compose down

# Or manually
docker stop tinychat-server
docker rm tinychat-server

# Remove image
docker rmi tinychat-server:latest
```

## Troubleshooting

- **Port already in use**: Change the host port in the docker run command or docker-compose.yml (e.g., `9000:8765`).
- **SSL certificate not found**: Ensure the certificate path is correct and the volume mount is configured.
- **Permission denied on certs**: Ensure the certificate files are readable and use `:ro` (read-only) mount flag.
- **Check logs**: Always run `docker logs <container-id>` for detailed error messages.

## Additional Resources

- See `SSL_SETUP.md` for SSL/TLS setup with Certbot.
- See `main.py` for server code and available commands (`/login`, `/to`, etc.).
