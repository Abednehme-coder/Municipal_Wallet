# Municipal Wallet System - Deployment Guide

This guide covers deploying the Municipal Wallet System to production environments.

## Prerequisites

- Docker and Docker Compose
- PostgreSQL 12+ database
- Redis server
- SMTP server for email notifications
- Twilio account for SMS notifications (optional)
- Domain name and SSL certificate

## Production Environment Setup

### 1. Environment Configuration

Create a production `.env` file:

```env
# Security
SECRET_KEY=your-super-secret-production-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DATABASE_URL=postgresql://username:password@db-host:5432/municipal_wallet

# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=your-smtp-server.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@domain.com
EMAIL_HOST_PASSWORD=your-email-password
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# SMS Configuration (Twilio)
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=+1234567890

# Celery Configuration
CELERY_BROKER_URL=redis://redis-host:6379/0
CELERY_RESULT_BACKEND=redis://redis-host:6379/0

# Approval Settings
DEPOSIT_APPROVALS_REQUIRED=3
WITHDRAWAL_APPROVALS_REQUIRED=5
APPROVAL_TIMEOUT_HOURS=72

# Security Settings
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
SECURE_CONTENT_TYPE_NOSNIFF=True
SECURE_BROWSER_XSS_FILTER=True
X_FRAME_OPTIONS=DENY
```

### 2. Docker Production Setup

Create a `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: municipal_wallet
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

  web:
    build: .
    command: gunicorn municipal_wallet.wsgi:application --bind 0.0.0.0:8000
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - CELERY_BROKER_URL=${CELERY_BROKER_URL}
      - CELERY_RESULT_BACKEND=${CELERY_RESULT_BACKEND}
    depends_on:
      - db
      - redis
    restart: unless-stopped

  celery:
    build: .
    command: celery -A municipal_wallet worker -l info
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - CELERY_BROKER_URL=${CELERY_BROKER_URL}
      - CELERY_RESULT_BACKEND=${CELERY_RESULT_BACKEND}
    depends_on:
      - db
      - redis
    restart: unless-stopped

  celery-beat:
    build: .
    command: celery -A municipal_wallet beat -l info
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - CELERY_BROKER_URL=${CELERY_BROKER_URL}
      - CELERY_RESULT_BACKEND=${CELERY_RESULT_BACKEND}
    depends_on:
      - db
      - redis
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - static_volume:/app/staticfiles
      - media_volume:/app/media
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - web
    restart: unless-stopped

volumes:
  postgres_data:
  static_volume:
  media_volume:
```

### 3. Nginx Configuration

Create `nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    upstream django {
        server web:8000;
    }

    server {
        listen 80;
        server_name yourdomain.com www.yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name yourdomain.com www.yourdomain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;

        client_max_body_size 20M;

        location / {
            proxy_pass http://django;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header Host $host;
            proxy_redirect off;
        }

        location /static/ {
            alias /app/staticfiles/;
        }

        location /media/ {
            alias /app/media/;
        }
    }
}
```

### 4. Deployment Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd municipal-wallet
   ```

2. **Set up environment**
   ```bash
   cp env.example .env
   # Edit .env with production values
   ```

3. **Build and start services**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d --build
   ```

4. **Run migrations**
   ```bash
   docker-compose -f docker-compose.prod.yml exec web python manage.py migrate
   ```

5. **Create superuser**
   ```bash
   docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
   ```

6. **Collect static files**
   ```bash
   docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
   ```

### 5. SSL Certificate Setup

1. **Install Certbot**
   ```bash
   sudo apt-get install certbot
   ```

2. **Obtain certificate**
   ```bash
   sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com
   ```

3. **Copy certificates to nginx directory**
   ```bash
   sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ./ssl/cert.pem
   sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ./ssl/key.pem
   ```

### 6. Monitoring and Logging

#### Health Checks

Create a health check script:

```bash
#!/bin/bash
# health_check.sh

# Check web service
curl -f http://localhost:8000/health || exit 1

# Check database
docker-compose -f docker-compose.prod.yml exec db pg_isready || exit 1

# Check Redis
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping || exit 1

echo "All services healthy"
```

#### Log Management

Set up log rotation:

```bash
# /etc/logrotate.d/municipal-wallet
/var/log/municipal-wallet/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 root root
    postrotate
        docker-compose -f /path/to/docker-compose.prod.yml restart web
    endscript
}
```

### 7. Backup Strategy

#### Database Backup

Create a backup script:

```bash
#!/bin/bash
# backup_db.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/municipal-wallet"
mkdir -p $BACKUP_DIR

docker-compose -f docker-compose.prod.yml exec -T db pg_dump -U postgres municipal_wallet > $BACKUP_DIR/db_backup_$DATE.sql

# Keep only last 30 days of backups
find $BACKUP_DIR -name "db_backup_*.sql" -mtime +30 -delete
```

#### File Backup

```bash
#!/bin/bash
# backup_files.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/municipal-wallet"

# Backup media files
tar -czf $BACKUP_DIR/media_backup_$DATE.tar.gz media/

# Backup configuration
cp .env $BACKUP_DIR/env_backup_$DATE
cp docker-compose.prod.yml $BACKUP_DIR/
```

### 8. Security Considerations

1. **Firewall Configuration**
   ```bash
   sudo ufw allow 22
   sudo ufw allow 80
   sudo ufw allow 443
   sudo ufw enable
   ```

2. **Regular Security Updates**
   ```bash
   # Update system packages
   sudo apt update && sudo apt upgrade -y
   
   # Update Docker images
   docker-compose -f docker-compose.prod.yml pull
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **Database Security**
   - Use strong passwords
   - Enable SSL connections
   - Regular security audits

### 9. Performance Optimization

1. **Database Optimization**
   - Add appropriate indexes
   - Regular VACUUM and ANALYZE
   - Connection pooling

2. **Caching**
   - Redis for session storage
   - Database query caching
   - Static file caching

3. **Load Balancing**
   - Multiple web server instances
   - Database read replicas
   - CDN for static files

### 10. Troubleshooting

#### Common Issues

1. **Database Connection Issues**
   ```bash
   # Check database logs
   docker-compose -f docker-compose.prod.yml logs db
   
   # Test connection
   docker-compose -f docker-compose.prod.yml exec web python manage.py dbshell
   ```

2. **Celery Issues**
   ```bash
   # Check Celery logs
   docker-compose -f docker-compose.prod.yml logs celery
   
   # Restart Celery
   docker-compose -f docker-compose.prod.yml restart celery
   ```

3. **Static Files Issues**
   ```bash
   # Collect static files
   docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
   ```

#### Monitoring Commands

```bash
# Check service status
docker-compose -f docker-compose.prod.yml ps

# Check resource usage
docker stats

# Check logs
docker-compose -f docker-compose.prod.yml logs -f web
```

### 11. Maintenance

#### Regular Tasks

1. **Daily**
   - Check service health
   - Monitor logs for errors
   - Verify backups

2. **Weekly**
   - Update dependencies
   - Review security logs
   - Performance analysis

3. **Monthly**
   - Security updates
   - Database maintenance
   - Backup verification

#### Update Procedure

1. **Backup current state**
2. **Pull latest changes**
3. **Update environment if needed**
4. **Rebuild and restart services**
5. **Run migrations**
6. **Verify functionality**

This deployment guide provides a comprehensive approach to deploying the Municipal Wallet System in a production environment with proper security, monitoring, and maintenance procedures.
