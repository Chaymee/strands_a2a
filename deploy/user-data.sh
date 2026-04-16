#!/bin/bash

# EC2 User Data Script for Strands A2A Server - Amazon Linux
# This script runs automatically when the EC2 instance launches

set -e

# Log everything
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "Starting Strands A2A Server deployment..."
echo "Timestamp: $(date)"

# Update system
echo "Updating system packages..."
yum update -y

# Install dependencies
echo "Installing dependencies..."
yum install -y python3.11 python3.11-pip git jq aws-cli

# Create application directory
echo "Setting up application directory..."
cd /home/ec2-user

# Clone repository
echo "Cloning repository..."
git clone https://github.com/Chaymee/strands_a2a.git

cd strands_a2a

# Create virtual environment (pip is available via python3.11-pip from yum)
echo "Creating virtual environment..."
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip

# Install requirements
echo "Installing Python requirements..."
pip install -r requirements.txt

# Make start script executable
chmod +x deploy/start_server.sh

# Set ownership
echo "Setting file ownership..."
chown -R ec2-user:ec2-user /home/ec2-user/strands_a2a

# Copy systemd service file
echo "Installing systemd service..."
cp deploy/strands-a2a.service /etc/systemd/system/

# Enable and start service
systemctl daemon-reload
systemctl enable strands-a2a.service
systemctl start strands-a2a.service

echo "Strands A2A Server deployment complete!"
echo "Service status:"
systemctl status strands-a2a.service --no-pager || true