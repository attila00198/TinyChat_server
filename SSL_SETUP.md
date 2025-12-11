# SSL/TLS Integration Guide for TinyChat Server

## Overview
The TinyChat WebSocket server now supports SSL/TLS encryption (secure WebSocket connections using `wss://` protocol instead of `ws://`).

## Quick Start

### 1. Generate Self-Signed Certificates (Testing Only)

For development and testing, generate a self-signed certificate:

```powershell
pip install cryptography
python generate_certs.py
```

This creates:
- `./certs/server.crt` - Public certificate
- `./certs/server.key` - Private key

### 2. Enable SSL in Configuration

Create or update `.env`:

```
USE_SSL=true
SSL_CERT_PATH=./certs/server.crt
SSL_KEY_PATH=./certs/server.key
```

### 3. Run the Server

```powershell
python main.py
```

Expected output:
```
12:00:00 [INFO]: [chat_server] SSL/TLS enabled: cert=./certs/server.crt, key=./certs/server.key
12:00:00 [INFO]: [chat_server] WebSocket server running: wss://0.0.0.0:8765
```

## Configuration Options

All options can be set via environment variables or `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_SSL` | `False` | Enable SSL/TLS (`true`/`false`) |
| `SSL_CERT_PATH` | `./certs/server.crt` | Path to certificate file |
| `SSL_KEY_PATH` | `./certs/server.key` | Path to private key file |

## Certificate Generation Options

Customize certificate generation:

```powershell
# Generate with custom validity (730 days)
python generate_certs.py --days 730

# Generate for specific hostname
python generate_certs.py --host example.com

# Generate to custom paths
python generate_certs.py --cert mycerts/cert.pem --key mycerts/key.pem
```

## Production Deployment

### Use Proper Certificates

For production, do **not** use self-signed certificates. Instead:

1. **Option A: Let's Encrypt with Certbot (Recommended)**
   
   ```bash
   # Install certbot
   sudo apt-get install certbot
   
   # Generate certificate (replace yourdomain.com with your actual domain)
   sudo certbot certonly --standalone -d yourdomain.com
   ```
   
   **Certbot generates standard PEM files that work directly:**
   - Certificate: `/etc/letsencrypt/live/yourdomain.com/fullchain.pem`
   - Private Key: `/etc/letsencrypt/live/yourdomain.com/privkey.pem`
   
   **Configuration in .env:**
   ```
   USE_SSL=true
   SSL_CERT_PATH=/etc/letsencrypt/live/yourdomain.com/fullchain.pem
   SSL_KEY_PATH=/etc/letsencrypt/live/yourdomain.com/privkey.pem
   ```
   
   **Auto-renewal with Certbot:**
   ```bash
   # Certbot automatically renews certificates before expiry
   # Verify renewal is working:
   sudo certbot renew --dry-run
   
   # After renewal, restart your TinyChat server to load new certificates:
   systemctl restart tinychat  # or however you manage the service
   ```
   
   **File Permissions Note:**
   - Certbot files are owned by `root` by default
   - Ensure your TinyChat server process can read the certificate files
   - If running as non-root user, adjust permissions:
     ```bash
     sudo chmod 644 /etc/letsencrypt/live/yourdomain.com/fullchain.pem
     sudo chmod 644 /etc/letsencrypt/live/yourdomain.com/privkey.pem
     ```

2. **Option B: Commercial CA**
   - Purchase a certificate from a trusted Certificate Authority
   - They typically provide PEM format files
   - Set paths in `.env` to point to their certificate and private key files

3. **Option C: Self-signed (High Risk)**
   - Only acceptable if:
     - You control both server and all clients
     - Clients explicitly accept self-signed certificates
     - Not internet-facing

### Security Best Practices

```python
# The server automatically:
✓ Creates SSL context with default secure settings
✓ Handles certificate loading errors gracefully
✓ Falls back to unencrypted mode if certificates are missing
✓ Logs SSL errors for debugging
```

### Client Connection Example

Python client using `websockets` library:

```python
import websockets
import ssl

async def connect_secure():
    # For self-signed certificates (testing only)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    async with websockets.connect(
        "wss://localhost:8765",
        ssl=ssl_context
    ) as websocket:
        await websocket.send('{"username": "user1", "type": "join"}')
        response = await websocket.recv()
        print(response)
```

For production with proper certificates:

```python
async def connect_secure():
    async with websockets.connect("wss://yourdomain.com:8765") as websocket:
        # Certificate will be automatically validated
        await websocket.send('{"username": "user1", "type": "join"}')
        response = await websocket.recv()
        print(response)
```

## Troubleshooting

### "SSL certificate not found" Error
```
SSL certificate not found: [Errno 2] No such file or directory: './certs/server.crt'
```
**Solution:**
- Run `python generate_certs.py` to generate certificates
- Or set correct paths in `.env`

### "SSL: CERTIFICATE_VERIFY_FAILED" (Client Error)
- Client is rejecting the certificate
- For self-signed certs: Configure client SSL context to skip verification (testing only)
- For production: Use proper certificates from a trusted CA

### Server Won't Connect with SSL
1. Check certificate file permissions (should be readable)
2. Verify paths in `.env` are correct
3. Ensure `cryptography` package is installed for cert generation
4. Check server logs for detailed SSL errors

## Environment Variables Examples

**.env for development:**
```
HOST=127.0.0.1
PORT=8765
MOD_PASSWORD=admin123
USE_SSL=false
```

**.env for testing with SSL:**
```
HOST=0.0.0.0
PORT=8765
MOD_PASSWORD=admin123
USE_SSL=true
SSL_CERT_PATH=./certs/server.crt
SSL_KEY_PATH=./certs/server.key
```

**.env for production:**
```
HOST=0.0.0.0
PORT=8765
MOD_PASSWORD=your_secure_password_here
USE_SSL=true
SSL_CERT_PATH=/etc/letsencrypt/live/yourdomain.com/fullchain.pem
SSL_KEY_PATH=/etc/letsencrypt/live/yourdomain.com/privkey.pem
```

## Certbot PEM Files - Complete Guide

### Direct Integration with Certbot Certificates

Your TinyChat server **fully supports** PEM files generated by Certbot. No conversion needed!

#### Setup Steps:

1. **Generate certificate with Certbot:**
   ```bash
   sudo certbot certonly --standalone -d yourdomain.com
   ```

2. **Update .env with Certbot paths:**
   ```
   USE_SSL=true
   SSL_CERT_PATH=/etc/letsencrypt/live/yourdomain.com/fullchain.pem
   SSL_KEY_PATH=/etc/letsencrypt/live/yourdomain.com/privkey.pem
   ```

3. **Run the server:**
   ```bash
   python main.py
   ```
   
   Expected output:
   ```
   [INFO]: SSL/TLS enabled: cert=/etc/letsencrypt/live/yourdomain.com/fullchain.pem, key=/etc/letsencrypt/live/yourdomain.com/privkey.pem
   [INFO]: WebSocket server running: wss://yourdomain.com:8765
   ```

#### Common Certbot File Paths

| Certbot File | TinyChat Config | Purpose |
|---|---|---|
| `fullchain.pem` | `SSL_CERT_PATH` | Server certificate + intermediate chain |
| `privkey.pem` | `SSL_KEY_PATH` | Private key |
| `cert.pem` | ❌ Don't use | Individual certificate only (missing chain) |

### Automatic Certificate Renewal

Certbot automatically renews certificates 30 days before expiry:

```bash
# Verify renewal is configured (runs automatically via cron)
sudo certbot renew --dry-run

# Manual renewal if needed
sudo certbot renew
```

**After renewal, restart your TinyChat server to load the new certificates:**

```bash
# If running as systemd service
sudo systemctl restart tinychat

# If running manually
# Kill the process and restart: python main.py
```

### Troubleshooting Certbot Integration

**Issue: "Permission denied" when reading certificate files**
```
SSL certificate not found: [Errno 13] Permission denied: '/etc/letsencrypt/live/yourdomain.com/fullchain.pem'
```

**Solution: Set appropriate file permissions**
```bash
# Make certificates readable by your application user
sudo chmod 644 /etc/letsencrypt/live/yourdomain.com/fullchain.pem
sudo chmod 644 /etc/letsencrypt/live/yourdomain.com/privkey.pem

# For enhanced security, create a dedicated group
sudo groupadd tinychat
sudo usermod -a -G tinychat youruser
sudo chown root:tinychat /etc/letsencrypt/live/yourdomain.com/*
sudo chmod 640 /etc/letsencrypt/live/yourdomain.com/fullchain.pem
sudo chmod 640 /etc/letsencrypt/live/yourdomain.com/privkey.pem
```

**Issue: Certificate not updating after renewal**

Certbot renews the actual files in place. If you're still getting old certificate errors:
1. Restart the TinyChat server to reload certificates from disk
2. Check file modification time: `ls -la /etc/letsencrypt/live/yourdomain.com/`
3. Verify the new certificate hasn't expired: `openssl x509 -in /etc/letsencrypt/live/yourdomain.com/fullchain.pem -noout -dates`

### Systemd Service Integration (Optional)

Create a systemd service file for auto-restart after certificate renewal:

**File: `/etc/systemd/system/tinychat.service`**
```ini
[Unit]
Description=TinyChat WebSocket Server
After=network.target

[Service]
Type=simple
User=tinychat
WorkingDirectory=/home/tinychat/chat_server
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable tinychat
sudo systemctl start tinychat
```

**Certbot renewal hook (optional auto-restart):**

Create `/etc/letsencrypt/renewal-hooks/post/tinychat.sh`:
```bash
#!/bin/bash
systemctl restart tinychat
```

Make it executable:
```bash
sudo chmod +x /etc/letsencrypt/renewal-hooks/post/tinychat.sh
```

Now your server will automatically restart whenever Certbot renews certificates!

## Additional Resources

- [websockets SSL documentation](https://websockets.readthedocs.io/en/stable/intro/index.html)
- [Let's Encrypt](https://letsencrypt.org/)
- [Certbot Documentation](https://certbot.eff.org/docs/)
- [Cryptography library](https://cryptography.io/)
- [OWASP TLS Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Protection_Cheat_Sheet.html)
