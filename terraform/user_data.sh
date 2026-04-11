#!/bin/bash
set -ex

# Update system
apt-get update
apt-get upgrade -y

# Install Docker
apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo \
  "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add ubuntu user to docker group
usermod -aG docker ubuntu

# Install git
apt-get install -y git

# Enable Docker daemon
systemctl enable docker
systemctl start docker

# Clone repository (required)
cd /tmp
git clone ${github_repo_url} -b ${repo_branch} selenium-docker

# Copy source code to /app
mkdir -p /app
cp -r /tmp/selenium-docker/* /app/
cd /app

# Create environment file for docker-compose
cat > .env << EOF
%{ for key, value in environment_vars ~}
${key}=${value}
%{ endfor ~}
EOF

# Create systemd service for docker-compose
cat > /etc/systemd/system/selenium-docker.service << 'SYSTEMD_EOF'
[Unit]
Description=Selenium WebDriver Docker Compose Service
After=docker.service
Requires=docker.service
StartLimitIntervalSec=60
StartLimitBurst=3

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/app
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/usr/bin/docker compose up --abort-on-container-exit
Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
SYSTEMD_EOF

# Set correct permissions
chmod 644 /etc/systemd/system/selenium-docker.service
chown -R ubuntu:ubuntu /app

# Enable and start the service
systemctl daemon-reload
systemctl enable selenium-docker.service
systemctl start selenium-docker.service

# Wait a bit for everything to start
sleep 30

# Log that setup is complete
echo "Selenium Docker deployment completed at $(date)" >> /var/log/setup-complete.log
