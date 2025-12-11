#!/bin/bash
# TinyChat Server Setup Script for Linux/Ubuntu
# Run this on your server: sudo bash server_setup.sh

set -e

echo "=== TinyChat Server Setup with Supervisor ==="

# Variables
TINYCHAT_USER="tinychat"
TINYCHAT_HOME="/opt/tinychat"
PYTHON_VERSION="3.11"
CERT_DIR="$TINYCHAT_HOME/certs"

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root. Use sudo." >&2
    exit 1
fi

# 1. Create service user
echo "Creating service user..."
if ! id "$TINYCHAT_USER" &>/dev/null; then
    useradd -m -s /bin/bash -d "$TINYCHAT_HOME" "$TINYCHAT_USER"
    echo "✓ User $TINYCHAT_USER created"
else
    echo "✓ User $TINYCHAT_USER already exists"
fi

# 2. Clone/update project
echo "Setting up project directory..."
if [ ! -d "$TINYCHAT_HOME/chat_server" ]; then
    mkdir -p "$TINYCHAT_HOME"
    cd "$TINYCHAT_HOME"
    git clone https://github.com/attila00198/TinyChat_server.git chat_server
else
    cd "$TINYCHAT_HOME/chat_server"
    git pull origin master || echo "⚠ Git pull failed, continuing..."
fi

chown -R "$TINYCHAT_USER:$TINYCHAT_USER" "$TINYCHAT_HOME"

# 3. Install Python and dependencies
echo "Installing Python and system dependencies..."
apt-get update
apt-get install -y \
    python$PYTHON_VERSION \
    python$PYTHON_VERSION-venv \
    python$PYTHON_VERSION-dev \
    git \
    supervisor \
    certbot \
    build-essential \
    libssl-dev \
    libffi-dev

# 4. Create virtual environment
echo "Creating Python virtual environment..."
cd "$TINYCHAT_HOME/chat_server"
if [ ! -d "venv" ]; then
    sudo -u "$TINYCHAT_USER" python$PYTHON_VERSION -m venv venv
    echo "✓ Virtual environment created"
fi

# 5. Install Python dependencies
echo "Installing Python packages..."
sudo -u "$TINYCHAT_USER" ./venv/bin/pip install --upgrade pip setuptools wheel
sudo -u "$TINYCHAT_USER" ./venv/bin/pip install -r requirements.txt

# 6. Create certificates directory
echo "Creating certificates directory..."
mkdir -p "$CERT_DIR"
chown root:root "$CERT_DIR"
chmod 755 "$CERT_DIR"

# 7. Create .env file
echo "Creating .env configuration..."
if [ ! -f ".env" ]; then
    cat > ".env" << EOF
# TinyChat Server Configuration
HOST=0.0.0.0
PORT=8765
MOD_PASSWORD=admin123

# SSL/TLS
USE_SSL=true
SSL_CERT_PATH=$CERT_DIR/fullchain.pem
SSL_KEY_PATH=$CERT_DIR/privkey.pem
EOF
    chown "$TINYCHAT_USER:$TINYCHAT_USER" ".env"
    echo "✓ Created .env - EDIT THIS FILE and change MOD_PASSWORD!"
else
    echo "✓ .env already exists"
fi

# 8. Create supervisor configuration
echo "Setting up supervisor..."
cat > /etc/supervisor/conf.d/tinychat.conf << EOF
[program:tinychat]
command=$TINYCHAT_HOME/chat_server/venv/bin/python $TINYCHAT_HOME/chat_server/main.py
directory=$TINYCHAT_HOME/chat_server
user=$TINYCHAT_USER
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=$TINYCHAT_HOME/chat_server/tinychat.log
stderr_logfile=$TINYCHAT_HOME/chat_server/tinychat_error.log
environment=PATH="$TINYCHAT_HOME/chat_server/venv/bin"
EOF

systemctl restart supervisor
supervisorctl reread
supervisorctl update

# 9. Check for existing certificates
echo ""
echo "Checking for Let's Encrypt certificates..."
CERT_ARCHIVE="/etc/letsencrypt/archive"
if [ -d "$CERT_ARCHIVE" ] && [ -n "$(ls -A $CERT_ARCHIVE 2>/dev/null)" ]; then
    echo "✓ Found existing certificates"
    
    # Find the certificate directory
    CERT_DOMAIN=$(ls -1 "$CERT_ARCHIVE" | head -n1)
    
    if [ -n "$CERT_DOMAIN" ]; then
        echo "Using certificates for: $CERT_DOMAIN"
        
        # Copy latest certs
        FULL=$(ls -1 "$CERT_ARCHIVE/$CERT_DOMAIN"/fullchain*.pem 2>/dev/null | sort -V | tail -n1)
        KEY=$(ls -1 "$CERT_ARCHIVE/$CERT_DOMAIN"/privkey*.pem 2>/dev/null | sort -V | tail -n1)
        
        if [ -n "$FULL" ] && [ -n "$KEY" ]; then
            cp -f "$FULL" "$CERT_DIR/fullchain.pem"
            cp -f "$KEY" "$CERT_DIR/privkey.pem"
            chown "$TINYCHAT_USER:$TINYCHAT_USER" "$CERT_DIR"/*.pem
            chmod 644 "$CERT_DIR/fullchain.pem"
            chmod 640 "$CERT_DIR/privkey.pem"
            echo "✓ Certificates copied"
            
            # Install renewal hook
            HOOK_PATH="/etc/letsencrypt/renewal-hooks/post/tinychat.sh"
            mkdir -p "$(dirname "$HOOK_PATH")"
            cat > "$HOOK_PATH" << HOOK
#!/bin/bash
set -e
ARCHIVE_DIR="$CERT_ARCHIVE/$CERT_DOMAIN"
DEST_DIR="$CERT_DIR"
SERVICE_USER="$TINYCHAT_USER"

# Find latest certs
FULL=\$(ls -1 "\$ARCHIVE_DIR"/fullchain*.pem 2>/dev/null | sort -V | tail -n1)
KEY=\$(ls -1 "\$ARCHIVE_DIR"/privkey*.pem 2>/dev/null | sort -V | tail -n1)

if [ -n "\$FULL" ] && [ -n "\$KEY" ]; then
    cp -f "\$FULL" "\$DEST_DIR/fullchain.pem"
    cp -f "\$KEY" "\$DEST_DIR/privkey.pem"
    chown "\$SERVICE_USER:\$SERVICE_USER" "\$DEST_DIR"/*.pem
    chmod 644 "\$DEST_DIR/fullchain.pem"
    chmod 640 "\$DEST_DIR/privkey.pem"
    
    # Restart service
    if command -v supervisorctl >/dev/null 2>&1; then
        supervisorctl restart tinychat
    fi
    
    logger "TinyChat: certificates renewed and service restarted"
fi
HOOK
            chmod +x "$HOOK_PATH"
            echo "✓ Certbot renewal hook installed"
        fi
    fi
else
    echo "⚠ No Let's Encrypt certificates found"
    echo "  Run: sudo certbot certonly --standalone -d your-domain.com"
    echo "  Then run this setup script again"
fi

# 10. Start the service
echo ""
echo "Starting TinyChat service..."
supervisorctl start tinychat || supervisorctl restart tinychat

# 11. Check status
sleep 2
echo ""
echo "=== Setup Complete! ==="
echo ""
echo "✓ Service user created: $TINYCHAT_USER"
echo "✓ Project installed to: $TINYCHAT_HOME/chat_server"
echo "✓ Virtual environment created"
echo "✓ Python packages installed"
echo "✓ Supervisor configured"
echo "✓ Certificates directory: $CERT_DIR"
echo ""
echo "=== Service Status ==="
supervisorctl status tinychat
echo ""
echo "=== Next Steps ==="
echo "1. Edit $TINYCHAT_HOME/chat_server/.env and change MOD_PASSWORD"
echo "2. If no SSL certs, run: sudo certbot certonly --standalone -d your-domain.com"
echo "3. View logs: sudo tail -f $TINYCHAT_HOME/chat_server/tinychat.log"
echo "4. Manage service: sudo supervisorctl start/stop/restart tinychat"
echo ""
echo "Server will auto-restart on reboot and after Certbot renewal."