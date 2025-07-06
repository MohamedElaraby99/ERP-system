#!/bin/bash

# ERP System Deployment Script
# This script handles the complete deployment of the ERP system

set -e  # Exit on any error

# Configuration
PROJECT_NAME="erp-system"
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"
}

show_banner() {
    echo -e "${GREEN}"
    cat << "EOF"
    ╔══════════════════════════════════════════════╗
    ║           ERP System Deployment              ║
    ║         نظام إدارة الموارد للشركات           ║
    ╚══════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

check_prerequisites() {
    log "🔍 Checking prerequisites..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        error "❌ Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error "❌ Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if required files exist
    if [ ! -f "${COMPOSE_FILE}" ]; then
        error "❌ ${COMPOSE_FILE} not found. Please ensure you're in the project root directory."
        exit 1
    fi
    
    log "✅ Prerequisites check passed"
}

create_env_file() {
    log "⚙️ Setting up environment configuration..."
    
    if [ ! -f "${ENV_FILE}" ]; then
        warning "📝 Creating default environment file..."
        
        # Generate secure random passwords
        DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
        REDIS_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
        SECRET_KEY=$(openssl rand -base64 64 | tr -d "=+/" | cut -c1-50)
        JWT_SECRET_KEY=$(openssl rand -base64 64 | tr -d "=+/" | cut -c1-50)
        
        cat > "${ENV_FILE}" << EOF
# Database Configuration
DB_PASSWORD=${DB_PASSWORD}
DATABASE_URL=postgresql://erp_user:${DB_PASSWORD}@db:5432/erp_system

# Redis Configuration
REDIS_PASSWORD=${REDIS_PASSWORD}
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0

# Flask Configuration
SECRET_KEY=${SECRET_KEY}
JWT_SECRET_KEY=${JWT_SECRET_KEY}
FLASK_ENV=production

# Security Configuration
ADMIN_EMAIL=admin@yourcompany.com
ADMIN_PASSWORD=ChangeThisPassword123!

# Email Configuration (Optional)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password

# Company Information
COMPANY_NAME=شركة فكرة للبرمجيات
COMPANY_EMAIL=info@yourcompany.com
COMPANY_PHONE=+966 11 234 5678

# Domain Configuration
DOMAIN=yourdomain.com
FRONTEND_URL=https://yourdomain.com

# Monitoring (Optional)
SENTRY_DSN=

# Feature Flags
ENABLE_USER_REGISTRATION=false
ENABLE_EMAIL_VERIFICATION=true
ENABLE_TWO_FACTOR_AUTH=false
CREATE_SAMPLE_DATA=true
EOF

        log "✅ Environment file created: ${ENV_FILE}"
        warning "⚠️ Please review and update the environment variables in ${ENV_FILE}"
        warning "⚠️ Especially change the default passwords and email settings!"
        
        # Pause for user to review
        echo ""
        read -p "Press Enter to continue after reviewing the environment file..."
        
    else
        log "✅ Environment file already exists: ${ENV_FILE}"
    fi
}

setup_ssl_certificates() {
    log "🔒 Setting up SSL certificates..."
    
    mkdir -p nginx/ssl
    
    if [ ! -f "nginx/ssl/cert.pem" ] || [ ! -f "nginx/ssl/key.pem" ]; then
        warning "📜 SSL certificates not found. Creating self-signed certificates for development..."
        
        # Create self-signed certificate
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout nginx/ssl/key.pem \
            -out nginx/ssl/cert.pem \
            -subj "/C=SA/ST=Riyadh/L=Riyadh/O=YourCompany/CN=localhost" 2>/dev/null
        
        warning "⚠️ Self-signed certificates created for development only!"
        warning "⚠️ For production, please replace with valid SSL certificates!"
    else
        log "✅ SSL certificates found"
    fi
}

build_application() {
    log "🏗️ Building application..."
    
    # Build Docker images
    if command -v docker-compose &> /dev/null; then
        docker-compose build --no-cache
    else
        docker compose build --no-cache
    fi
    
    log "✅ Application built successfully"
}

start_services() {
    log "🚀 Starting services..."
    
    # Start services
    if command -v docker-compose &> /dev/null; then
        docker-compose up -d
    else
        docker compose up -d
    fi
    
    log "⏳ Waiting for services to start..."
    sleep 30
    
    # Check service health
    check_service_health
}

check_service_health() {
    log "🏥 Checking service health..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost/health &> /dev/null; then
            log "✅ All services are healthy and running"
            return 0
        fi
        
        info "⏳ Attempt $attempt/$max_attempts - Services still starting..."
        sleep 10
        ((attempt++))
    done
    
    error "❌ Services failed to start properly"
    show_logs
    exit 1
}

initialize_database() {
    log "🗄️ Initializing database..."
    
    # Wait for database to be ready
    if command -v docker-compose &> /dev/null; then
        docker-compose exec -T app python scripts/init_db.py
    else
        docker compose exec -T app python scripts/init_db.py
    fi
    
    log "✅ Database initialized successfully"
}

show_deployment_info() {
    log "📋 Deployment Information:"
    echo ""
    echo -e "${GREEN}🎉 ERP System deployed successfully!${NC}"
    echo ""
    echo -e "${BLUE}Access URLs:${NC}"
    echo "  🌐 Web Interface: http://localhost"
    echo "  🌐 HTTPS: https://localhost (with self-signed cert)"
    echo "  🏥 Health Check: http://localhost/health"
    echo ""
    echo -e "${BLUE}Default Login:${NC}"
    echo "  📧 Email: admin@yourcompany.com"
    echo "  🔑 Password: ChangeThisPassword123!"
    echo ""
    echo -e "${YELLOW}⚠️ Important Notes:${NC}"
    echo "  • Change default passwords immediately"
    echo "  • Review environment configuration in ${ENV_FILE}"
    echo "  • Replace self-signed SSL certificates for production"
    echo "  • Configure email settings for notifications"
    echo ""
    echo -e "${BLUE}Useful Commands:${NC}"
    echo "  📊 View logs: docker-compose logs -f"
    echo "  ⏹️ Stop services: docker-compose down"
    echo "  🔄 Restart: docker-compose restart"
    echo "  💾 Backup database: ./scripts/backup.sh"
    echo ""
}

show_logs() {
    warning "📜 Showing recent logs..."
    
    if command -v docker-compose &> /dev/null; then
        docker-compose logs --tail=50
    else
        docker compose logs --tail=50
    fi
}

cleanup_on_error() {
    error "❌ Deployment failed. Cleaning up..."
    
    if command -v docker-compose &> /dev/null; then
        docker-compose down -v 2>/dev/null || true
    else
        docker compose down -v 2>/dev/null || true
    fi
}

main() {
    show_banner
    
    # Set up error handling
    trap cleanup_on_error ERR
    
    # Deployment steps
    check_prerequisites
    create_env_file
    setup_ssl_certificates
    build_application
    start_services
    initialize_database
    show_deployment_info
    
    log "🎉 Deployment completed successfully!"
}

# Parse command line arguments
case "${1:-deploy}" in
    deploy)
        main
        ;;
    stop)
        log "⏹️ Stopping services..."
        if command -v docker-compose &> /dev/null; then
            docker-compose down
        else
            docker compose down
        fi
        log "✅ Services stopped"
        ;;
    restart)
        log "🔄 Restarting services..."
        if command -v docker-compose &> /dev/null; then
            docker-compose restart
        else
            docker compose restart
        fi
        log "✅ Services restarted"
        ;;
    logs)
        show_logs
        ;;
    status)
        log "📊 Service status:"
        if command -v docker-compose &> /dev/null; then
            docker-compose ps
        else
            docker compose ps
        fi
        ;;
    backup)
        log "💾 Running database backup..."
        ./scripts/backup.sh
        ;;
    *)
        echo "Usage: $0 {deploy|stop|restart|logs|status|backup}"
        echo ""
        echo "Commands:"
        echo "  deploy  - Full deployment (default)"
        echo "  stop    - Stop all services"
        echo "  restart - Restart all services"
        echo "  logs    - Show service logs"
        echo "  status  - Show service status"
        echo "  backup  - Run database backup"
        exit 1
        ;;
esac 
main 