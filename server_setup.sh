#!/bin/bash
# TinyChat Server Setup Script for Linux/Ubuntu
# Run this on your server: bash server_setup.sh

set -e

echo "=== TinyChat Server Setup with Supervisor ==="

# Variables
TINYCHAT_USER="tinychat"
TINYCHAT_HOME="/opt/tinychat"
PYTHON_VERSION="3.11"

# 1. Create service user
echo "Creating service user..."
if ! id "$TINYCHAT_USER" &>/dev/null; then
    sudo useradd -m -s /bin/bash -d "$TINYCHAT_HOME" "$TINYCHAT_USER"
    echo "✓ User $TINYCHAT_USER created"
else
    echo "✓ User $TINYCHAT_USER already exists"
fi

# 2. Clone/update project
echo "Setting up project directory..."
if [ ! -d "$TINYCHAT_HOME/chat_server" ]; then
    sudo mkdir -p "$TINYCHAT_HOME"
    cd "$TINYCHAT_HOME"
    sudo git clone https://github.com/attila00198/TinyChat_server.git chat_server
else
    cd "$TINYCHAT_HOME/chat_server"
    sudo git pull origin master
fi

sudo chown -R "$TINYCHAT_USER:$TINYCHAT_USER" "$TINYCHAT_HOME"

# 3. Install Python and dependencies
echo "Installing Python and system dependencies..."
sudo apt-get update
sudo apt-get install -y \
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

# 6. Create .env file
echo "Creating .env configuration..."
if [ ! -f ".env" ]; then
    cat > ".env" << 'EOF'
# TinyChat Server Configuration
HOST=0.0.0.0
PORT=8765
MOD_PASSWORD=admin123

# SSL/TLS
USE_SSL=true
SSL_CERT_PATH=/etc/letsencrypt/archive/krassus.ddns.net-0001/fullchain1.pem
SSL_KEY_PATH=/etc/letsencrypt/archive/krassus.ddns.net-0001/privkey1.pem
EOF
    sudo chown "$TINYCHAT_USER:$TINYCHAT_USER" ".env"
    echo "✓ Created .env - EDIT THIS FILE and change MOD_PASSWORD!"
else
    echo "✓ .env already exists"
fi

# 7. Install supervisor configuration
echo "Setting up supervisor..."
sudo cp supervisor_tinychat.conf /etc/supervisor/conf.d/tinychat.conf
sudo systemctl restart supervisor
sudo supervisorctl reread
sudo supervisorctl update

# 8. Set up Certbot renewal hook
echo "Setting up Certbot renewal hook..."
sudo mkdir -p /etc/letsencrypt/renewal-hooks/post
sudo tee /etc/letsencrypt/renewal-hooks/post/tinychat.sh > /dev/null << 'EOF'
#!/bin/bash
# Restart TinyChat after certificate renewal
supervisorctl restart tinychat
EOF
sudo chmod +x /etc/letsencrypt/renewal-hooks/post/tinychat.sh

# 9. Start the service
echo "Starting TinyChat service..."
sudo supervisorctl start tinychat

# 10. Check status
echo ""
echo "=== Setup Complete! ==="
echo ""
echo "✓ Service user created: $TINYCHAT_USER"
echo "✓ Project cloned to: $TINYCHAT_HOME/chat_server"
echo "✓ Virtual environment created"
echo "✓ Python packages installed"
echo "✓ Supervisor configured"
echo "✓ Certbot hook installed"
echo ""
echo "=== Next Steps ==="
echo "1. Edit $TINYCHAT_HOME/chat_server/.env and change MOD_PASSWORD"
echo "2. Check status: sudo supervisorctl status tinychat"
echo "3. View logs: sudo tail -f $TINYCHAT_HOME/chat_server/tinychat.log"
echo "4. Start/stop: sudo supervisorctl start/stop/restart tinychat"
echo ""
echo "Server will auto-restart on reboot and after Certbot renewal."
