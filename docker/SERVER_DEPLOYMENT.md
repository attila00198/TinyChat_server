# Server Deployment Guide for TinyChat

## Quick Start on Your Server

### Prerequisites
- Docker and Docker Compose installed
- Certbot certificates available at `/etc/letsencrypt/live/krassus.ddns.net-0001/`

### Step 1: Copy the docker-compose.prod.yml to your server

```bash
# On your server, create a directory for TinyChat
mkdir -p /opt/tinychat/docker
cd /opt/tinychat/docker

# Copy the production compose file
# (You can either copy the file directly or create it manually)
```

### Step 2: Pull and run the container

```bash
# Pull the latest image from Docker Hub
docker pull attila00198/tinychat-server:latest

# Start the server in the background
docker-compose -f docker-compose.prod.yml up -d

# Check logs
docker-compose -f docker-compose.prod.yml logs -f
```

### Step 3: Verify it's running

```bash
# Check container status
docker ps | grep tinychat

# Test WebSocket connection (requires websocat or wscat)
# For secure connection:
# websocat wss://krassus.ddns.net:8765 --ssl-no-verify

# Or check logs for confirmation
docker logs tinychat-server
```

## Managing the Container

### View logs
```bash
docker logs -f tinychat-server
docker logs --tail 50 tinychat-server
```

### Stop the server
```bash
docker-compose -f docker-compose.prod.yml down
```

### Restart the server
```bash
docker-compose -f docker-compose.prod.yml restart
```

### Update to latest image
```bash
docker pull attila00198/tinychat-server:latest
docker-compose -f docker-compose.prod.yml up -d
```

### Check resource usage
```bash
docker stats tinychat-server
```

## Configuration

### Change Moderator Password
Edit `docker-compose.prod.yml` and update:
```yaml
environment:
  - MOD_PASSWORD=your_secure_password
```

Then restart:
```bash
docker-compose -f docker-compose.prod.yml restart
```

### Disable SSL (use plain WebSocket)
Edit `docker-compose.prod.yml`:
```yaml
environment:
  - USE_SSL=false
```

Then restart.

### Change Port
Edit the port mapping in `docker-compose.prod.yml`:
```yaml
ports:
  - "9000:8765"  # Change 9000 to your desired port
```

Then restart.

## Troubleshooting

### SSL certificate not found
```
[ERROR]: SSL tanúsítvány nem található: [Errno 2] No such file or directory
[WARNING]: Visszavonás: SSL nélkül futtatás
```

**Solution:** Verify certificate path and Certbot renewal:
```bash
ls -la /etc/letsencrypt/live/krassus.ddns.net-0001/
# Should show: fullchain.pem and privkey.pem
```

### Container won't start
Check logs:
```bash
docker logs tinychat-server
```

Common issues:
- Port already in use: Change port mapping
- Certificates missing: Ensure Certbot is configured
- Not enough disk space: Check with `df -h`

### Connection refused
Verify container is running:
```bash
docker ps | grep tinychat
```

Check if it's listening:
```bash
docker exec tinychat-server netstat -tlnp | grep 8765
```

## Automatic Updates (Optional)

To automatically update the image when a new version is released, use Watchtower:

```bash
docker run -d \
  --name watchtower \
  --volume /var/run/docker.sock:/var/run/docker.sock \
  containrrr/watchtower \
  --interval 3600 \
  tinychat-server
```

This checks for updates every hour and automatically restarts containers with newer images.

## Systemd Service (Optional)

To manage the container with systemd, create `/etc/systemd/system/tinychat.service`:

```ini
[Unit]
Description=TinyChat WebSocket Server
After=docker.service
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=/opt/tinychat/docker
ExecStart=/usr/bin/docker-compose -f docker-compose.prod.yml up
ExecStop=/usr/bin/docker-compose -f docker-compose.prod.yml down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable tinychat
sudo systemctl start tinychat
sudo systemctl status tinychat
```

## Backup & Recovery

### Backup logs
```bash
docker logs tinychat-server > tinychat-backup-$(date +%Y%m%d).log
```

### Container data persistence
If you need persistent data storage, add to `docker-compose.prod.yml`:
```yaml
volumes:
  - /opt/tinychat/data:/app/data
```

## Security Notes

1. **Always change `MOD_PASSWORD`** from the default `admin123`
2. **Use HTTPS/SSL** in production (`USE_SSL=true`)
3. **Keep Docker and the image updated**
4. **Run with resource limits** to prevent DoS
5. **Use a reverse proxy** (nginx) for additional security if needed
