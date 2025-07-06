#!/bin/bash

# =================================================================
# ERP System Production Deployment Script
# Domain: manage.fikra.solutions
# Port: 8005
# =================================================================

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOMAIN="manage.fikra.solutions"
PORT="8005"
PROJECT_DIR="/opt/erp-system"
BACKUP_DIR="/opt/erp-system/backups"
LOG_DIR="/opt/erp-system/logs"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root"
        exit 1
    fi
}

# Install dependencies
install_dependencies() {
    print_header "Installing System Dependencies"
    
    # Update system
    apt-get update -y
    apt-get upgrade -y
    
    # Install required packages
    apt-get install -y \
        docker.io \
        docker-compose \
        nginx \
        certbot \
        python3-certbot-nginx \
        git \
        curl \
        wget \
        unzip \
        htop \
        nano \
        ufw \
        fail2ban \
        logrotate \
        cron
    
    # Start and enable Docker
    systemctl start docker
    systemctl enable docker
    
    # Add user to docker group
    usermod -aG docker $SUDO_USER
    
    print_status "System dependencies installed successfully"
}

# Setup firewall
setup_firewall() {
    print_header "Configuring Firewall"
    
    # Reset UFW
    ufw --force reset
    
    # Default policies
    ufw default deny incoming
    ufw default allow outgoing
    
    # Allow SSH
    ufw allow ssh
    
    # Allow HTTP and HTTPS
    ufw allow 80/tcp
    ufw allow 443/tcp
    
    # Allow application port
    ufw allow $PORT/tcp
    
    # Allow PostgreSQL (only from localhost)
    ufw allow from 127.0.0.1 to any port 5432
    
    # Allow Redis (only from localhost)
    ufw allow from 127.0.0.1 to any port 6379
    
    # Enable firewall
    ufw --force enable
    
    print_status "Firewall configured successfully"
}

# Setup SSL certificate
setup_ssl() {
    print_header "Setting up SSL Certificate"
    
    # Stop nginx if running
    systemctl stop nginx || true
    
    # Get SSL certificate
    certbot certonly --standalone \
        --non-interactive \
        --agree-tos \
        --email admin@fikra.solutions \
        -d $DOMAIN \
        -d www.$DOMAIN
    
    # Setup auto-renewal
    (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | crontab -
    
    print_status "SSL certificate obtained successfully"
}

# Setup project directory
setup_project() {
    print_header "Setting up Project Directory"
    
    # Create project directory
    mkdir -p $PROJECT_DIR
    cd $PROJECT_DIR
    
    # Create necessary directories
    mkdir -p $BACKUP_DIR
    mkdir -p $LOG_DIR
    mkdir -p ssl
    mkdir -p nginx/sites
    
    # Copy SSL certificates
    cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem ssl/
    cp /etc/letsencrypt/live/$DOMAIN/privkey.pem ssl/
    
    # Set permissions
    chmod 600 ssl/*
    
    print_status "Project directory setup completed"
}

# Deploy application
deploy_application() {
    print_header "Deploying Application"
    
    # Stop existing containers
    docker-compose down || true
    
    # Build and start containers
    docker-compose build --no-cache
        docker-compose up -d
    
    # Wait for services to start
    sleep 30
    
    # Check if services are running
    if docker-compose ps | grep -q "Up"; then
        print_status "Application deployed successfully"
    else
        print_error "Application deployment failed"
        docker-compose logs
        exit 1
    fi
}

# Setup monitoring
setup_monitoring() {
    print_header "Setting up Monitoring"
    
    # Create monitoring script
    cat > /usr/local/bin/erp-monitor.sh << 'EOF'
#!/bin/bash
# ERP System Monitoring Script

LOG_FILE="/var/log/erp-monitor.log"
DATE=$(date "+%Y-%m-%d %H:%M:%S")

# Check if containers are running
if ! docker-compose -f /opt/erp-system/docker-compose.yml ps | grep -q "Up"; then
    echo "[$DATE] ERROR: ERP containers are not running" >> $LOG_FILE
    # Restart containers
    cd /opt/erp-system
    docker-compose restart
fi

# Check if application is responding
if ! curl -f http://localhost:8005/health > /dev/null 2>&1; then
    echo "[$DATE] ERROR: ERP application is not responding" >> $LOG_FILE
    # Restart web container
    cd /opt/erp-system
    docker-compose restart web
fi

# Check disk space
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "[$DATE] WARNING: Disk usage is at $DISK_USAGE%" >> $LOG_FILE
fi

# Check memory usage
MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
if [ $MEMORY_USAGE -gt 85 ]; then
    echo "[$DATE] WARNING: Memory usage is at $MEMORY_USAGE%" >> $LOG_FILE
fi

echo "[$DATE] INFO: System check completed" >> $LOG_FILE
EOF

    chmod +x /usr/local/bin/erp-monitor.sh
    
    # Add to crontab
    (crontab -l 2>/dev/null; echo "*/5 * * * * /usr/local/bin/erp-monitor.sh") | crontab -
    
    print_status "Monitoring setup completed"
}

# Setup backup
setup_backup() {
    print_header "Setting up Backup System"
    
    # Create backup script
    cat > /usr/local/bin/erp-backup.sh << 'EOF'
#!/bin/bash
# ERP System Backup Script

BACKUP_DIR="/opt/erp-system/backups"
DATE=$(date "+%Y%m%d_%H%M%S")
DB_BACKUP_FILE="$BACKUP_DIR/database_$DATE.sql"
FILES_BACKUP_FILE="$BACKUP_DIR/files_$DATE.tar.gz"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
docker exec erp_postgres pg_dump -U erp_user erp_system_production > $DB_BACKUP_FILE

# Backup files
cd /opt/erp-system
tar -czf $FILES_BACKUP_FILE uploads/ logs/ ssl/

# Remove old backups (keep last 7 days)
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

    chmod +x /usr/local/bin/erp-backup.sh
    
    # Add to crontab (daily backup at 2 AM)
    (crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/erp-backup.sh") | crontab -
    
    print_status "Backup system setup completed"
}

# Main deployment function
main() {
    print_header "ERP System Production Deployment"
    print_status "Domain: $DOMAIN"
    print_status "Port: $PORT"
    print_status "Starting deployment..."
    
    check_root
    install_dependencies
    setup_firewall
    setup_ssl
    setup_project
    deploy_application
    setup_monitoring
    setup_backup
    
    print_header "Deployment Completed Successfully!"
    print_status "Application is now running at: https://$DOMAIN"
    print_status "Monitoring: http://localhost:9000 (Portainer)"
    print_status "Supervisor: http://localhost:9001 (Supervisor)"
    print_status ""
    print_status "Default admin credentials:"
    print_status "Username: admin"
    print_status "Password: admin123"
    print_status ""
    print_warning "IMPORTANT: Change default passwords immediately!"
    print_warning "Update SSL certificates every 90 days"
    print_warning "Monitor system resources regularly"
}

# Run main function
main "$@" 