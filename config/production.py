import os
from datetime import timedelta
from .config import Config

class ProductionConfig(Config):
    """Production configuration with enhanced security"""
    
    # Flask Environment
    DEBUG = False
    TESTING = False
    
    # Database Configuration - Use PostgreSQL for production
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://erp_user:secure_password@localhost:5432/erp_system_production'
    
    # Enhanced Security
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'CHANGE-THIS-IN-PRODUCTION-IMMEDIATELY'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'CHANGE-JWT-SECRET-IN-PRODUCTION'
    
    # JWT Configuration with enhanced security
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)  # Shorter for production
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)   # Shorter refresh window
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ['access', 'refresh']
    
    # Security Headers
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
    
    # CORS Configuration for production
    CORS_ORIGINS = [
        'https://manage.fikra.solutions',
        'https://www.manage.fikra.solutions',
        'http://manage.fikra.solutions',
        'http://localhost:8005'
    ]
    
    # Rate Limiting with Redis
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    RATELIMIT_DEFAULT = "1000 per hour"
    RATELIMIT_HEADERS_ENABLED = True
    
    # Email Configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@yourcompany.com'
    
    # File Upload Security
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or '/app/uploads'
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'}
    
    # Logging Configuration
    LOG_LEVEL = 'INFO'
    LOG_FILE = '/app/logs/erp_system.log'
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 10
    
    # Database Connection Pool for production
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,
        'pool_timeout': 20,
        'pool_recycle': 1800,
        'max_overflow': 0,
        'pool_pre_ping': True
    }
    
    # Company Information
    COMPANY_NAME = os.environ.get('COMPANY_NAME') or 'شركة فكرة للحلول التقنية'
    COMPANY_EMAIL = os.environ.get('COMPANY_EMAIL') or 'info@fikra.solutions'
    COMPANY_PHONE = os.environ.get('COMPANY_PHONE') or '+966 11 234 5678'
    
    # Domain Configuration
    DOMAIN = os.environ.get('DOMAIN') or 'manage.fikra.solutions'
    ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'manage.fikra.solutions,www.manage.fikra.solutions').split(',')
    
    # Server Configuration
    PORT = int(os.environ.get('PORT', 8005))
    HOST = os.environ.get('HOST', '0.0.0.0')
    
    # Cache Configuration
    CACHE_TYPE = 'redis'
    CACHE_REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/1'
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Celery Configuration for background tasks
    CELERY_BROKER_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/2'
    CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL') or 'redis://localhost:6379/2'
    
    # Monitoring
    SENTRY_DSN = os.environ.get('SENTRY_DSN')
    
    # Backup Configuration
    BACKUP_INTERVAL_HOURS = int(os.environ.get('BACKUP_INTERVAL_HOURS', 24))
    BACKUP_RETENTION_DAYS = int(os.environ.get('BACKUP_RETENTION_DAYS', 30)) 