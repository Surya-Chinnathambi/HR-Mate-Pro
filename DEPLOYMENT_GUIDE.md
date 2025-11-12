# HRMS Production Deployment Guide

**Complete guide for deploying the HRMS system to production**

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Database Setup](#database-setup)
4. [Application Deployment](#application-deployment)
5. [Security Configuration](#security-configuration)
6. [Monitoring & Logging](#monitoring--logging)
7. [Backup & Recovery](#backup--recovery)
8. [Performance Optimization](#performance-optimization)
9. [Troubleshooting](#troubleshooting)

---

## 1. Prerequisites

### System Requirements

**Minimum (Development/Small Teams):**
- CPU: 2 cores
- RAM: 4 GB
- Storage: 50 GB SSD
- OS: Ubuntu 20.04 LTS or later

**Recommended (Production):**
- CPU: 4+ cores
- RAM: 16 GB
- Storage: 200 GB SSD
- OS: Ubuntu 22.04 LTS

### Required Software

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install additional tools
sudo apt-get install -y git curl wget vim ufw fail2ban
```

---

## 2. Environment Setup

### Clone Repository

```bash
cd /opt
sudo git clone <your-repo-url> hrms
cd hrms/hrms_backend
sudo chown -R $USER:$USER /opt/hrms
```

### Create Environment File

```bash
cp .env.example .env
vim .env
```

**Environment Variables (.env):**

```bash
# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================
POSTGRES_USER=hrms_user
POSTGRES_PASSWORD=<generate-strong-password>
POSTGRES_DB=hrms_production
DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}

# ============================================================================
# REDIS CONFIGURATION
# ============================================================================
REDIS_PASSWORD=<generate-strong-password>
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0

# ============================================================================
# SECURITY
# ============================================================================
SECRET_KEY=<generate-256-bit-secret-key>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Generate secret key with:
# python -c "import secrets; print(secrets.token_urlsafe(32))"

# ============================================================================
# APPLICATION
# ============================================================================
APP_NAME="HRMS Production"
APP_VERSION="1.0.0"
DEBUG=false
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# ============================================================================
# EMAIL CONFIGURATION
# ============================================================================
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=<app-specific-password>
EMAIL_FROM=noreply@yourdomain.com

# ============================================================================
# AI FEATURES (Optional)
# ============================================================================
OPENAI_API_KEY=sk-...your-openai-key

# ============================================================================
# WORKERS
# ============================================================================
WORKERS=4

# ============================================================================
# MONITORING (Optional)
# ============================================================================
SENTRY_DSN=<your-sentry-dsn>
```

### Generate Strong Passwords

```bash
# PostgreSQL password
openssl rand -base64 32

# Redis password
openssl rand -base64 32

# Secret key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 3. Database Setup

### Initialize Database

```bash
# Start PostgreSQL container
docker-compose -f docker-compose.prod.yml up -d postgres

# Wait for PostgreSQL to be ready
sleep 10

# Run database migrations
docker-compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

# (Optional) Load initial data
docker-compose -f docker-compose.prod.yml run --rm backend python _init_data.py
```

### Database Backup Configuration

```bash
# Create backup directory
mkdir -p backups

# Create backup script
cat > backup_db.sh <<'EOF'
#!/bin/bash
BACKUP_DIR="/opt/hrms/hrms_backend/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/hrms_backup_$TIMESTAMP.sql"

docker exec hrms_postgres pg_dump -U hrms_user hrms_production > "$BACKUP_FILE"
gzip "$BACKUP_FILE"

# Keep only last 30 days of backups
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE.gz"
EOF

chmod +x backup_db.sh

# Schedule daily backups (crontab)
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/hrms/hrms_backend/backup_db.sh") | crontab -
```

---

## 4. Application Deployment

### SSL Certificate Setup

**Option 1: Let's Encrypt (Recommended)**

```bash
# Install certbot
sudo apt-get install -y certbot

# Generate certificate
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Copy certificates
sudo mkdir -p nginx/ssl
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/key.pem
sudo chown -R $USER:$USER nginx/ssl

# Auto-renewal (crontab)
(crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet") | crontab -
```

**Option 2: Self-Signed Certificate (Development Only)**

```bash
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem \
  -out nginx/ssl/cert.pem \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=yourdomain.com"
```

### Build and Deploy

```bash
# Build images
docker-compose -f docker-compose.prod.yml build

# Start all services
docker-compose -f docker-compose.prod.yml up -d

# Check service status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f backend
```

### Verify Deployment

```bash
# Health check
curl http://localhost/health

# API documentation
curl http://localhost/api/docs

# WebSocket test
curl -i -N -H "Connection: Upgrade" \
     -H "Upgrade: websocket" \
     -H "Sec-WebSocket-Version: 13" \
     -H "Sec-WebSocket-Key: test" \
     http://localhost/ws/socket.io/
```

---

## 5. Security Configuration

### Firewall Setup

```bash
# Enable UFW
sudo ufw enable

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Check status
sudo ufw status
```

### Fail2Ban Configuration

```bash
# Install fail2ban
sudo apt-get install -y fail2ban

# Configure
sudo cat > /etc/fail2ban/jail.local <<EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log

[nginx-http-auth]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log
EOF

# Restart fail2ban
sudo systemctl restart fail2ban
```

### Security Headers

Already configured in `nginx.conf`:
- ✅ X-Frame-Options
- ✅ X-Content-Type-Options
- ✅ X-XSS-Protection
- ✅ Strict-Transport-Security
- ✅ Referrer-Policy

### Rate Limiting

Configured in `nginx.conf`:
- API: 10 requests/second (burst: 20)
- WebSocket: 5 connections/second (burst: 10)

---

## 6. Monitoring & Logging

### Centralized Logging

```bash
# View all logs
docker-compose -f docker-compose.prod.yml logs -f

# Backend logs only
docker-compose -f docker-compose.prod.yml logs -f backend

# PostgreSQL logs
docker-compose -f docker-compose.prod.yml logs -f postgres

# Nginx logs
docker-compose -f docker-compose.prod.yml logs -f nginx
```

### Log Rotation

```bash
# Configure log rotation
sudo cat > /etc/logrotate.d/hrms <<EOF
/opt/hrms/hrms_backend/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 hrms hrms
    sharedscripts
}
EOF
```

### Health Monitoring Script

```bash
cat > health_check.sh <<'EOF'
#!/bin/bash

SERVICES=("postgres" "redis" "backend" "nginx")
ALERT_EMAIL="admin@yourdomain.com"

for service in "${SERVICES[@]}"; do
    if ! docker-compose -f docker-compose.prod.yml ps | grep -q "$service.*Up"; then
        echo "Service $service is down!" | mail -s "HRMS Alert: Service Down" "$ALERT_EMAIL"
        docker-compose -f docker-compose.prod.yml restart "$service"
    fi
done
EOF

chmod +x health_check.sh

# Run every 5 minutes
(crontab -l 2>/dev/null; echo "*/5 * * * * /opt/hrms/hrms_backend/health_check.sh") | crontab -
```

### Prometheus & Grafana (Optional)

```yaml
# Add to docker-compose.prod.yml

  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    restart: unless-stopped

  grafana:
    image: grafana/grafana
    volumes:
      - grafana_data:/var/lib/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    restart: unless-stopped
```

---

## 7. Backup & Recovery

### Automated Backup Strategy

**Daily Backups:**
```bash
# Database backup (already configured in section 3)
0 2 * * * /opt/hrms/hrms_backend/backup_db.sh

# Uploaded files backup
0 3 * * * tar -czf /opt/hrms/backups/uploads_$(date +\%Y\%m\%d).tar.gz /opt/hrms/hrms_backend/uploads
```

**Weekly Full Backup:**
```bash
# Full system backup
0 4 * * 0 tar -czf /opt/hrms/backups/full_backup_$(date +\%Y\%m\%d).tar.gz /opt/hrms
```

### Recovery Procedure

**Database Recovery:**
```bash
# Stop backend
docker-compose -f docker-compose.prod.yml stop backend

# Restore database
gunzip < backups/hrms_backup_YYYYMMDD_HHMMSS.sql.gz | \
  docker exec -i hrms_postgres psql -U hrms_user -d hrms_production

# Restart services
docker-compose -f docker-compose.prod.yml start backend
```

**Full System Recovery:**
```bash
# Extract backup
tar -xzf backups/full_backup_YYYYMMDD.tar.gz -C /opt/

# Rebuild and start
cd /opt/hrms/hrms_backend
docker-compose -f docker-compose.prod.yml up -d --build
```

---

## 8. Performance Optimization

### Database Optimization

```sql
-- Connect to database
docker exec -it hrms_postgres psql -U hrms_user -d hrms_production

-- Create indexes
CREATE INDEX idx_employees_department ON employees(department_id);
CREATE INDEX idx_work_assignments_assignee ON work_assignments(assignee_id);
CREATE INDEX idx_work_assignments_status ON work_assignments(status);
CREATE INDEX idx_approval_steps_approver ON approval_steps(approver_id);
CREATE INDEX idx_approval_steps_status ON approval_steps(status);

-- Analyze tables
ANALYZE employees;
ANALYZE work_assignments;
ANALYZE approval_steps;
```

### Redis Caching

Update `app/config.py`:
```python
# Add Redis caching for frequently accessed data
from redis import Redis

redis_client = Redis.from_url(settings.REDIS_URL)

# Cache employee data (TTL: 1 hour)
def get_employee_cached(employee_id):
    cache_key = f"employee:{employee_id}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    employee = db.query(Employee).get(employee_id)
    redis_client.setex(cache_key, 3600, json.dumps(employee.dict()))
    return employee
```

### Uvicorn Workers

Adjust based on CPU cores:
```bash
# In .env or docker-compose.prod.yml
WORKERS=4  # (2 x CPU cores) + 1
```

### Nginx Optimization

Already optimized in `nginx.conf`:
- ✅ Gzip compression
- ✅ HTTP/2
- ✅ Keepalive connections
- ✅ Static file caching (30 days)
- ✅ Buffer optimization

---

## 9. Troubleshooting

### Common Issues

**1. Backend won't start**
```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs backend

# Common causes:
# - Database not ready: Wait for postgres health check
# - Environment variables missing: Check .env file
# - Port already in use: Change port in docker-compose.prod.yml
```

**2. Database connection error**
```bash
# Test database connection
docker exec hrms_postgres psql -U hrms_user -d hrms_production -c "SELECT 1"

# Check DATABASE_URL in .env
# Ensure postgres container is running
docker-compose -f docker-compose.prod.yml ps postgres
```

**3. WebSocket not connecting**
```bash
# Check nginx WebSocket proxy configuration
# Ensure /ws/ location block is present in nginx.conf
# Check browser console for errors
# Verify firewall allows WebSocket connections
```

**4. High memory usage**
```bash
# Check container stats
docker stats

# Reduce workers if needed
# Optimize database queries
# Enable Redis caching
```

**5. SSL certificate errors**
```bash
# Verify certificate files exist
ls -l nginx/ssl/

# Check certificate validity
openssl x509 -in nginx/ssl/cert.pem -text -noout

# Renew Let's Encrypt certificate
sudo certbot renew
```

### Debug Mode

```bash
# Enable debug mode (NOT for production)
# In .env:
DEBUG=true

# Restart backend
docker-compose -f docker-compose.prod.yml restart backend

# View detailed logs
docker-compose -f docker-compose.prod.yml logs -f backend
```

### Performance Debugging

```bash
# Check slow queries
docker exec hrms_postgres psql -U hrms_user -d hrms_production -c "
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;"

# Check connection count
docker exec hrms_postgres psql -U hrms_user -d hrms_production -c "
SELECT count(*) FROM pg_stat_activity;"
```

---

## 🎉 Deployment Checklist

- [ ] System requirements met
- [ ] Docker and Docker Compose installed
- [ ] Repository cloned
- [ ] Environment variables configured (.env)
- [ ] Strong passwords generated
- [ ] SSL certificates obtained
- [ ] Database initialized and migrated
- [ ] Firewall configured (UFW)
- [ ] Fail2Ban installed and configured
- [ ] Application deployed
- [ ] Health checks passing
- [ ] Backups configured and tested
- [ ] Monitoring set up
- [ ] Log rotation configured
- [ ] Performance optimizations applied
- [ ] Documentation reviewed by team

---

## 📞 Support

For issues or questions:
- Check logs: `docker-compose logs`
- Review documentation: `/docs`
- Contact: support@yourdomain.com

---

**Last Updated:** November 11, 2025
**Version:** 1.0.0
