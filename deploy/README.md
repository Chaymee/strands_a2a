# AWS EC2 Deployment Guide

This guide walks you through deploying the Strands A2A server to AWS EC2 with automatic startup using AWS Secrets Manager for secure credential management.

## Prerequisites

- AWS CLI installed and configured locally
- AWS account with permissions to:
  - Create EC2 instances
  - Create IAM roles and policies
  - Create Secrets Manager secrets
  - Create Security Groups
- Your LiteLLM API key and desired API password

## Step 1: Create Secrets in AWS Secrets Manager

Create a secret to store your sensitive credentials:

```bash
aws secretsmanager create-secret \
    --name strands-a2a/credentials \
    --description "Credentials for Strands A2A Server" \
    --secret-string '{
        "API_PASSWORD":"your_secure_password_here",
        "LLM_SERVICE_API_KEY":"your_litellm_api_key_here",
        "LLM_SERVICE_ENDPOINT":"https://lite-llm.mymaas.net"
    }' \
    --region us-east-2
```

**Note the ARN** of the created secret - you'll need it for the IAM policy.

To update the secret later:

```bash
aws secretsmanager update-secret \
    --secret-id strands-a2a/credentials \
    --secret-string '{
        "API_PASSWORD":"new_password",
        "LLM_SERVICE_API_KEY":"new_key",
        "LLM_SERVICE_ENDPOINT":"https://lite-llm.mymaas.net"
    }' \
    --region us-east-2
```

## Step 2: Create IAM Role and Policy

### Create the IAM Policy

```bash
aws iam create-policy \
    --policy-name StrandsA2ASecretsAccess \
    --policy-document file://deploy/ec2-iam-policy.json \
    --description "Allow EC2 instance to read Strands A2A secrets"
```

**Note the Policy ARN** from the output.

### Create IAM Role for EC2

Create a trust policy file:

```bash
cat > /tmp/ec2-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
```

Create the role:

```bash
aws iam create-role \
    --role-name StrandsA2AServerRole \
    --assume-role-policy-document file:///tmp/ec2-trust-policy.json \
    --description "IAM role for Strands A2A EC2 instance"
```

Attach the policy to the role (replace with your policy ARN):

```bash
aws iam attach-role-policy \
    --role-name StrandsA2AServerRole \
    --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/StrandsA2ASecretsAccess
```

Create instance profile:

```bash
aws iam create-instance-profile \
    --instance-profile-name StrandsA2AServerProfile

aws iam add-role-to-instance-profile \
    --instance-profile-name StrandsA2AServerProfile \
    --role-name StrandsA2AServerRole
```

## Step 3: Create Security Group

Create a security group for SSH access. Agent port access (9000/9001) is controlled by the
Codespaces security group `sg-09b94e454a6a4f3c8`, which auto-registers allowed IP addresses
and must be attached to every agent instance (see Step 5).

```bash
aws ec2 create-security-group \
    --group-name strands-a2a-sg \
    --description "Security group for Strands A2A Server (SSH only - agent ports via sg-09b94e454a6a4f3c8)" \
    --vpc-id YOUR_VPC_ID \
    --region us-east-2

# Get the security group ID from the output
SG_ID="sg-xxxxxxxxx"

# Allow SSH access (restrict to your admin IP in production)
aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol tcp \
    --port 22 \
    --cidr 0.0.0.0/0 \
    --region us-east-2
```

**Note:** Do not add inbound rules for ports 9000/9001 here. Those are managed by the
Codespaces security group `sg-09b94e454a6a4f3c8`, which restricts access to registered
Codespaces IP addresses only.

## Step 4: Create User Data Script

Create a user data script for EC2 initialization:

```bash
cat > /tmp/user-data.sh <<'EOF'
#!/bin/bash

# Update system
apt-get update && apt-get upgrade -y

# Install dependencies
apt-get install -y python3 python3-pip git jq awscli

# Create application directory
cd /home/ubuntu

# Clone or copy your repository
# Option A: Clone from Git
git clone https://github.com/YOUR_USERNAME/strands_a2a.git

# Option B: If using a tarball or zip, download it
# wget https://your-repo/strands_a2a.tar.gz
# tar -xzf strands_a2a.tar.gz

cd strands_a2a

# Install requirements system-wide
pip3 install -r requirements.txt

# Make start script executable
chmod +x deploy/start_server.sh

# Set ownership
chown -R ubuntu:ubuntu /home/ubuntu/strands_a2a

# Copy systemd service file
cp deploy/strands-a2a.service /etc/systemd/system/

# Enable and start service
systemctl daemon-reload
systemctl enable strands-a2a.service
systemctl start strands-a2a.service

echo "Strands A2A Server deployment complete!"
EOF
```

## Step 5: Launch EC2 Instance

Launch an Ubuntu EC2 instance with the IAM role and user data:

Both the base security group and the Codespaces security group must be attached. The Codespaces
group (`sg-09b94e454a6a4f3c8`) controls which IP addresses can reach the agent ports.

```bash
aws ec2 run-instances \
    --image-id ami-0c7217cdde317cfec \
    --instance-type t3.medium \
    --key-name YOUR_KEY_PAIR \
    --security-group-ids $SG_ID sg-09b94e454a6a4f3c8 \
    --iam-instance-profile Name=StrandsA2AServerProfile \
    --user-data file:///tmp/user-data.sh \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=Strands-A2A-Server}]' \
    --region us-east-2
```

**Note:** Replace `ami-0c7217cdde317cfec` with the latest Ubuntu AMI for your region.

## Step 6: Verify Deployment

### SSH into the instance:

```bash
ssh -i your-key.pem ubuntu@YOUR_INSTANCE_PUBLIC_IP
```

### Check service status:

```bash
sudo systemctl status strands-a2a.service
```

### View logs:

```bash
# Real-time logs
sudo journalctl -u strands-a2a.service -f

# Recent logs
sudo journalctl -u strands-a2a.service -n 100
```

### Test the agents:

```bash
# Test Calculator Agent
curl -X POST http://localhost:9000/.well-known/agent-card.json

# Test Factor Agent
curl -X POST http://localhost:9001/.well-known/agent-card.json
```

## Step 7: Access from External Clients

Your agents are now accessible at:

- **Calculator Agent:** `http://YOUR_INSTANCE_PUBLIC_IP:9000`
- **Factor Agent:** `http://YOUR_INSTANCE_PUBLIC_IP:9001`

## Troubleshooting

### Service fails to start

1. Check logs:
   ```bash
   sudo journalctl -u strands-a2a.service -n 50
   ```

2. Verify secrets are accessible:
   ```bash
   aws secretsmanager get-secret-value \
       --secret-id strands-a2a/credentials \
       --region us-east-2
   ```

3. Check IAM role is attached:
   ```bash
   aws ec2 describe-instances --instance-ids YOUR_INSTANCE_ID \
       --query 'Reservations[0].Instances[0].IamInstanceProfile'
   ```

### Cannot access from external network

1. Confirm both security groups are attached to the instance:
   ```bash
   aws ec2 describe-instances --instance-ids YOUR_INSTANCE_ID \
       --query 'Reservations[0].Instances[0].SecurityGroups' \
       --region us-east-2
   ```
   You should see both `$SG_ID` (SSH) and `sg-09b94e454a6a4f3c8` (Codespaces IP allowlist).

2. Confirm your Codespace IP is registered in `sg-09b94e454a6a4f3c8`:
   ```bash
   aws ec2 describe-security-groups --group-ids sg-09b94e454a6a4f3c8 \
       --query 'SecurityGroups[0].IpPermissions' \
       --region us-east-2
   ```

2. Verify ports are listening:
   ```bash
   sudo netstat -tlnp | grep -E '9000|9001'
   ```

### Secrets not loading

1. Ensure IAM role has correct permissions
2. Verify the secret name matches exactly: `strands-a2a/credentials`
3. Check AWS region matches in both secret and EC2 instance

## Updating the Application

To update the code on a running instance:

```bash
# SSH into the instance
ssh -i your-key.pem ubuntu@YOUR_INSTANCE_PUBLIC_IP

# Navigate to the application directory
cd /home/ubuntu/strands_a2a

# Pull latest changes
git pull

# Update dependencies if needed
pip3 install -r requirements.txt

# Restart the service
sudo systemctl restart strands-a2a.service

# Check status
sudo systemctl status strands-a2a.service
```

## Updating Secrets

To update API passwords or keys:

```bash
aws secretsmanager update-secret \
    --secret-id strands-a2a/credentials \
    --secret-string '{
        "API_PASSWORD":"new_password",
        "LLM_SERVICE_API_KEY":"new_key",
        "LLM_SERVICE_ENDPOINT":"https://lite-llm.mymaas.net"
    }' \
    --region us-east-2

# Restart the service to pick up new secrets
ssh ubuntu@YOUR_INSTANCE_PUBLIC_IP 'sudo systemctl restart strands-a2a.service'
```

## Monitoring

### Set up CloudWatch Logs (Optional)

Install CloudWatch agent:

```bash
sudo apt-get install -y amazon-cloudwatch-agent
```

Configure it to send systemd journal logs to CloudWatch for centralized monitoring.

### Service Management Commands

```bash
# Start service
sudo systemctl start strands-a2a.service

# Stop service
sudo systemctl stop strands-a2a.service

# Restart service
sudo systemctl restart strands-a2a.service

# Check status
sudo systemctl status strands-a2a.service

# View logs
sudo journalctl -u strands-a2a.service -f
```

## Cost Optimization

- Use **t3.small** or **t3.medium** instances for development
- Consider **Reserved Instances** for production to save costs
- Use **Auto Stop/Start** schedules for non-production environments
- Consider **Spot Instances** for cost savings (with proper handling of interruptions)

## Security Best Practices

1. **IP Restriction via Codespaces SG:** Agent ports (9000/9001) are restricted to registered Codespaces IP addresses via `sg-09b94e454a6a4f3c8`. Always attach this group when launching instances.
2. **Rotate Secrets:** Regularly update API passwords and keys
3. **Use VPC:** Deploy in a private subnet with NAT gateway for production
4. **Enable CloudTrail:** Monitor API access to Secrets Manager
5. **Regular Updates:** Keep system and dependencies updated
6. **Monitoring:** Set up CloudWatch alarms for service failures

## Next Steps

- Set up Application Load Balancer for high availability
- Configure Auto Scaling for handling variable load
- Implement backup and disaster recovery procedures
- Set up monitoring and alerting with CloudWatch
- Configure custom domain with Route 53
