#!/bin/bash

# =================================================================
# ERP System Docker Startup Script
# Domain: manage.fikra.solutions
# =================================================================

set -e

echo "🚀 Starting ERP System Production Container..."

# Function to wait for services
wait_for_service() {
    local host=$1
    local port=$2
    local service=$3
    local max_attempts=30
    local attempt=1
    
    echo "⏳ Waiting for $service at $host:$port..."
    
    while [ $attempt -le $max_attempts ]; do
        if nc -z "$host" "$port" > /dev/null 2>&1; then
            echo "✅ $service is ready!"
            return 0
        fi
        
        echo "⏳ Attempt $attempt/$max_attempts - $service not ready yet..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "❌ $service failed to start after $max_attempts attempts"
    return 1
}

# Wait for database
if [ -n "$DATABASE_URL" ]; then
    echo "🔗 Waiting for database connection..."
    wait_for_service "db" "5432" "PostgreSQL"
fi

# Wait for Redis
if [ -n "$REDIS_URL" ]; then
    echo "🔗 Waiting for Redis connection..."
    wait_for_service "redis" "6379" "Redis"
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p /app/logs
mkdir -p /app/uploads
mkdir -p /app/backups
mkdir -p /app/static
mkdir -p /app/templates

# Set proper permissions
echo "🔒 Setting permissions..."
chown -R appuser:appuser /app/logs
chown -R appuser:appuser /app/uploads
chown -R appuser:appuser /app/backups
chmod 755 /app/logs
chmod 755 /app/uploads
chmod 755 /app/backups

# Initialize database if needed
echo "🗄️ Initializing database..."
if [ "$FLASK_ENV" = "production" ]; then
    python -c "
from app import create_app
from extensions import db
import os

app = create_app()
with app.app_context():
    try:
        db.create_all()
        print('✅ Database tables created successfully')
    except Exception as e:
        print(f'⚠️ Database initialization: {e}')
"
fi

# Run database migrations
echo "🔄 Running database migrations..."
python -c "
from flask_migrate import upgrade
from app import create_app

app = create_app()
with app.app_context():
    try:
        upgrade()
        print('✅ Database migrations completed')
    except Exception as e:
        print(f'⚠️ Migration warning: {e}')
"

# Create admin user if not exists
echo "👤 Creating admin user..."
python -c "
from app import create_app
from models.user import User
from extensions import db, bcrypt

app = create_app()
with app.app_context():
    try:
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@fikra.solutions',
                password=bcrypt.generate_password_hash('admin123').decode('utf-8'),
                role='admin',
                is_active=True
            )
            db.session.add(admin)
            db.session.commit()
            print('✅ Admin user created: admin/admin123')
        else:
            print('ℹ️ Admin user already exists')
    except Exception as e:
        print(f'⚠️ Admin user creation: {e}')
"

# Health check function
health_check() {
    echo "🏥 Running health check..."
    if curl -f http://localhost:8005/health > /dev/null 2>&1; then
        echo "✅ Health check passed"
        return 0
    else
        echo "❌ Health check failed"
        return 1
    fi
}

# Start Nginx if configured
if [ -f "/etc/nginx/nginx.conf" ]; then
    echo "🌐 Starting Nginx..."
    nginx -t && nginx -g "daemon off;" &
    NGINX_PID=$!
fi

# Start the Flask application
echo "🚀 Starting Flask application on port 8005..."
echo "📍 Domain: manage.fikra.solutions"
echo "🔗 Environment: $FLASK_ENV"

# Use Gunicorn for production
if [ "$FLASK_ENV" = "production" ]; then
    echo "🏭 Starting Gunicorn production server..."
    exec gunicorn \
        --bind 0.0.0.0:8005 \
        --workers 4 \
        --worker-class gevent \
        --worker-connections 1000 \
        --max-requests 1000 \
        --max-requests-jitter 50 \
        --preload \
        --timeout 120 \
        --keep-alive 2 \
        --access-logfile /app/logs/gunicorn_access.log \
        --error-logfile /app/logs/gunicorn_error.log \
        --log-level info \
        --capture-output \
        --enable-stdio-inheritance \
        app:app
else
    echo "🔧 Starting Flask development server..."
    exec python app.py
fi 