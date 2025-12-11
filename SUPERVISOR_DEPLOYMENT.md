# TinyChat Server - Supervisor Deployment Guide

**Run Python directly with Supervisor, no Docker required!**

## Quick Start (5 minutes)

### 1. SSH into your server and clone the project:

```bash
ssh your-server
cd /tmp
git clone https://github.com/attila00198/TinyChat_server.git
cd TinyChat_server
```

### 2. Run the setup script:

```bash
sudo bash server_setup.sh
```

This script will:
- Create a `tinychat` system user
- Clone the project to `/opt/tinychat/chat_server`
- Create Python virtual environment
- Install dependencies (websockets, python-dotenv, cryptography)
- Configure supervisor
- Set up Certbot renewal hooks
- Start the service

### 3. Configure the server:

```bash
sudo nano /opt/tinychat/chat_server/.env
```

Edit these values:
```bash
MOD_PASSWORD=your_secure_password_here
USE_SSL=true
SSL_CERT_PATH=/etc/letsencrypt/archive/krassus.ddns.net-0001/fullchain1.pem
SSL_KEY_PATH=/etc/letsencrypt/archive/krassus.ddns.net-0001/privkey1.pem
```

### 4. Start the service:

```bash
sudo supervisorctl start tinychat
```

## Managing the Service

### View status:
```bash
sudo supervisorctl status tinychat
```

### View live logs:
```bash
sudo tail -f /opt/tinychat/chat_server/tinychat.log
```

### View last 50 lines:
```bash
sudo tail -50 /opt/tinychat/chat_server/tinychat.log
```

### Restart the service:
```bash
sudo supervisorctl restart tinychat
```

### Stop the service:
```bash
sudo supervisorctl stop tinychat
```

### Start the service:
```bash
sudo supervisorctl start tinychat
```

### Reload supervisor config (after editing tinychat.conf):
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl restart tinychat
```

## SSL/TLS Certificate Configuration

### Current certificate path:
The setup script uses Certbot archive folder (actual cert files):
```
/etc/letsencrypt/archive/krassus.ddns.net-0001/
  ├── fullchain1.pem (or higher number)
  └── privkey1.pem (or higher number)
```

### Finding the latest certificate numbers:

```bash
ls -la /etc/letsencrypt/archive/krassus.ddns.net-0001/
```

If you see `fullchain2.pem` instead of `fullchain1.pem`, update `.env`:

```bash
sudo nano /opt/tinychat/chat_server/.env
# Change:
# SSL_CERT_PATH=/etc/letsencrypt/archive/krassus.ddns.net-0001/fullchain2.pem
# SSL_KEY_PATH=/etc/letsencrypt/archive/krassus.ddns.net-0001/privkey2.pem

sudo supervisorctl restart tinychat
```

### Certbot auto-renewal:

The setup script installs a renewal hook that automatically restarts the service when certificates are renewed. Certbot will renew 30 days before expiration:

```bash
# View renewal status:
sudo certbot renew --dry-run

# Check hook execution:
sudo tail -f /var/log/letsencrypt/renewal.log
```

## Troubleshooting

### Service won't start

Check logs:
```bash
sudo tail -50 /opt/tinychat/chat_server/tinychat_error.log
```

Common issues:
- **Port 8765 already in use**: Kill the process or change PORT in `.env`
- **Missing .env file**: Create it as shown above
- **Cert files not found**: Verify paths in `.env` match your actual cert locations
- **Permission denied**: Check file ownership: `ls -la /opt/tinychat/chat_server/`

### Permissions issue:

```bash
sudo chown -R tinychat:tinychat /opt/tinychat/chat_server
```

### Service keeps crashing:

Check supervisor status:
```bash
sudo supervisorctl tail tinychat
sudo supervisorctl tail tinychat stderr
```

### Can't connect to server:

Check if service is running:
```bash
sudo supervisorctl status tinychat
ps aux | grep main.py
```

Test connection locally:
```bash
# On server:
curl -I http://localhost:8765

# From client:
websocat wss://krassus.ddns.net:8765
```

## Updating the application

```bash
cd /opt/tinychat/chat_server
sudo -u tinychat git pull origin master
sudo supervisorctl restart tinychat
sudo tail -f tinychat.log
```

## Disabling SSL (plain WebSocket):

Edit `.env`:
```bash
USE_SSL=false
```

Then restart:
```bash
sudo supervisorctl restart tinychat
```

## Systemd integration (optional):

If supervisor itself doesn't auto-start, add to systemd:

```bash
sudo systemctl enable supervisor
sudo systemctl restart supervisor
```

Check status:
```bash
sudo systemctl status supervisor
```

## Backup and monitoring

### Backup logs:
```bash
sudo cp /opt/tinychat/chat_server/tinychat.log ~/tinychat-$(date +%Y%m%d).log
```

### Monitor resource usage:
```bash
watch 'ps aux | grep main.py'
```

### Check disk space:
```bash
du -sh /opt/tinychat/
df -h
```

## Uninstall (if needed):

```bash
sudo supervisorctl stop tinychat
sudo rm /etc/supervisor/conf.d/tinychat.conf
sudo supervisorctl reread
sudo supervisorctl update
sudo userdel -r tinychat
```

## Security Notes

1. **Change MOD_PASSWORD** - Default is `admin123`
2. **Use HTTPS** - Set `USE_SSL=true` in production
3. **Firewall** - Only expose port 8765 to trusted networks if possible
4. **Monitor logs** - Regularly check for errors or suspicious activity
5. **Keep updated** - Run `git pull` periodically for security patches

## Support

If you encounter issues:
1. Check logs: `sudo tail -f /opt/tinychat/chat_server/tinychat.log`
2. Verify configuration: `cat /opt/tinychat/chat_server/.env`
3. Check supervisor status: `sudo supervisorctl status tinychat`
4. Review certificate paths: `ls -la /etc/letsencrypt/archive/krassus.ddns.net-0001/`
