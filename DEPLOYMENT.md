# Deployment Guide

This guide covers deploying the AI-Driven Genetic Disorder Detection API to production.

## 🚀 Quick Start with Docker Compose

### Prerequisites
- Docker and Docker Compose installed
- PostgreSQL database (or use the provided one)
- Google Gemini API key
- Tavily API key

### 1. Environment Setup

```bash
# Copy environment template
cp env.example .env

# Edit .env with your actual values
nano .env
```

Required environment variables:
```env
DATABASE_URL=postgresql://genetic_user:genetic_password@postgres:5432/genetic_db
GEMINI_API_KEY=your_actual_gemini_key
TAVILY_API_KEY=your_actual_tavily_key
SECRET_KEY=your-super-secret-production-key
```

### 2. Start Services

```bash
# Development (API + Database only)
docker-compose up -d postgres api

# Production (with Nginx)
docker-compose --profile production up -d
```

### 3. Verify Deployment

```bash
# Check health
curl http://localhost:8000/health

# Run tests
python test_api.py
```

## 🏗️ Manual Deployment

### 1. Server Requirements

- **OS**: Ubuntu 20.04+ or CentOS 8+
- **RAM**: Minimum 2GB, Recommended 4GB+
- **Storage**: 10GB+ available space
- **Python**: 3.11+
- **PostgreSQL**: 13+

### 2. Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3.11 python3.11-pip python3.11-venv

# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Install Nginx
sudo apt install nginx

# Install system dependencies
sudo apt install build-essential libpq-dev
```

### 3. Database Setup

```bash
# Create database user
sudo -u postgres createuser --interactive genetic_user

# Create database
sudo -u postgres createdb genetic_db

# Set password
sudo -u postgres psql -c "ALTER USER genetic_user PASSWORD 'your_secure_password';"
```

### 4. Application Setup

```bash
# Clone repository
git clone <your-repo-url>
cd ai-driven-genetic-disorder-detection

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp env.example .env
nano .env
```

### 5. Systemd Service

Create `/etc/systemd/system/genetic-api.service`:

```ini
[Unit]
Description=Genetic Disorder Detection API
After=network.target postgresql.service

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/path/to/your/app
Environment=PATH=/path/to/your/app/venv/bin
ExecStart=/path/to/your/app/venv/bin/gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 127.0.0.1:8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl enable genetic-api
sudo systemctl start genetic-api
sudo systemctl status genetic-api
```

### 6. Nginx Configuration

Create `/etc/nginx/sites-available/genetic-api`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

    # API endpoints
    location / {
        limit_req zone=api burst=20 nodelay;
        
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/genetic-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 7. SSL Certificate (Let's Encrypt)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## 🔒 Security Considerations

### 1. Environment Variables
- Never commit `.env` files to version control
- Use strong, unique secrets
- Rotate secrets regularly

### 2. Database Security
- Use strong passwords
- Limit database access to application server only
- Enable SSL connections
- Regular backups

### 3. API Security
- Implement rate limiting
- Use HTTPS only
- Validate all inputs
- Sanitize file uploads

### 4. Server Security
- Keep system updated
- Use firewall (UFW)
- Disable root SSH login
- Use SSH keys only

## 📊 Monitoring and Logging

### 1. Application Logs

```bash
# View application logs
sudo journalctl -u genetic-api -f

# View Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### 2. Health Monitoring

```bash
# Create monitoring script
cat > /usr/local/bin/monitor-genetic-api.sh << 'EOF'
#!/bin/bash
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
if [ $response -ne 200 ]; then
    echo "API health check failed: $response"
    systemctl restart genetic-api
fi
EOF

chmod +x /usr/local/bin/monitor-genetic-api.sh

# Add to crontab
echo "*/5 * * * * /usr/local/bin/monitor-genetic-api.sh" | sudo crontab -
```

### 3. Database Monitoring

```bash
# Check database connections
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity;"

# Check database size
sudo -u postgres psql -c "SELECT pg_size_pretty(pg_database_size('genetic_db'));"
```

## 🔄 Backup Strategy

### 1. Database Backups

```bash
# Create backup script
cat > /usr/local/bin/backup-db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/var/backups/genetic-db"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

sudo -u postgres pg_dump genetic_db > $BACKUP_DIR/genetic_db_$DATE.sql
gzip $BACKUP_DIR/genetic_db_$DATE.sql

# Keep only last 7 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
EOF

chmod +x /usr/local/bin/backup-db.sh

# Add to crontab (daily at 2 AM)
echo "0 2 * * * /usr/local/bin/backup-db.sh" | sudo crontab -
```

### 2. Application Backups

```bash
# Backup application files
tar -czf /var/backups/genetic-app-$(date +%Y%m%d).tar.gz /path/to/your/app
```

## 🚀 Scaling Considerations

### 1. Horizontal Scaling

For high traffic, consider:
- Load balancer (HAProxy, Nginx)
- Multiple application instances
- Database read replicas
- Redis for session storage

### 2. Vertical Scaling

- Increase server resources
- Optimize database queries
- Use connection pooling
- Implement caching

## 🐛 Troubleshooting

### Common Issues

1. **Service won't start**
   ```bash
   sudo systemctl status genetic-api
   sudo journalctl -u genetic-api -n 50
   ```

2. **Database connection errors**
   ```bash
   sudo -u postgres psql -c "SELECT * FROM pg_stat_activity;"
   ```

3. **File permission issues**
   ```bash
   sudo chown -R www-data:www-data /path/to/your/app
   sudo chmod -R 755 /path/to/your/app
   ```

4. **Nginx errors**
   ```bash
   sudo nginx -t
   sudo tail -f /var/log/nginx/error.log
   ```

### Performance Tuning

1. **Database optimization**
   ```sql
   -- Add indexes for better performance
   CREATE INDEX idx_messages_chat_id ON messages(chat_id);
   CREATE INDEX idx_messages_created_at ON messages(created_at);
   ```

2. **Application tuning**
   - Adjust worker processes in gunicorn
   - Optimize VCF parsing
   - Implement caching

## 📞 Support

For deployment issues:
- Check logs: `sudo journalctl -u genetic-api -f`
- Verify configuration: `python test_api.py`
- Monitor resources: `htop`, `df -h`
- Database status: `sudo systemctl status postgresql` 