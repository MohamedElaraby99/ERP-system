import os
from datetime import timedelta

# Load environment variables if .env file exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class Config:
    """Base configuration class"""
    
    # Basic Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///erp_system.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    
    # JWT configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-change-in-production'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ['access', 'refresh']
    
    # Security Configuration
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # Mail configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'localhost'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@erpsystem.com'
    
    # File upload configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'uploads'
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'}
    
    # Rate limiting
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL') or 'memory://'
    RATELIMIT_DEFAULT = "1000 per hour"
    RATELIMIT_HEADERS_ENABLED = True
    
    # Pagination
    ITEMS_PER_PAGE = 20
    
    # Logging Configuration
    LOG_LEVEL = 'DEBUG'
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')
    
    # Company information
    COMPANY_NAME = os.environ.get('COMPANY_NAME') or 'شركة فكرة للبرمجيات'
    COMPANY_EMAIL = os.environ.get('COMPANY_EMAIL') or 'info@fikra-software.com'
    COMPANY_PHONE = os.environ.get('COMPANY_PHONE') or '+966 11 234 5678'
    
    # Cache Configuration
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///erp_dev.db'
    SQLALCHEMY_ECHO = True
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """Production configuration with enhanced security"""
    DEBUG = False
    TESTING = False
    
    # Database Configuration - Use PostgreSQL for production
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://erp_user:secure_password@localhost:5432/erp_system'
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_RECORD_QUERIES = False
    
    # Enhanced Security - Use environment variables for secrets
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(32)
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or os.urandom(32)
    
    # JWT Configuration with enhanced security
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)  # Shorter for production
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)   # Shorter refresh window
    JWT_ALGORITHM = 'HS256'
    
    # Security Headers and Configuration
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
    
    # Additional security headers
    SECURITY_HEADERS = {
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'SAMEORIGIN',
        'X-XSS-Protection': '1; mode=block',
        'Referrer-Policy': 'strict-origin-when-cross-origin'
    }
    
    # Rate Limiting with Redis
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    RATELIMIT_DEFAULT = "1000 per hour"
    RATELIMIT_HEADERS_ENABLED = True
    
    # Enhanced rate limits for specific endpoints
    RATELIMIT_PER_ENDPOINT = {
        'auth.login': '5 per minute',
        'auth.register': '3 per hour',
        'auth.change_password': '3 per minute'
    }
    
    # Database Connection Pool for production
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,
        'pool_timeout': 20,
        'pool_recycle': 1800,
        'max_overflow': 0,
        'pool_pre_ping': True
    }
    
    # Logging Configuration
    LOG_LEVEL = 'INFO'
    LOG_FILE = os.environ.get('LOG_FILE') or 'logs/erp_system.log'
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 10
    
    # Cache Configuration with Redis
    CACHE_TYPE = 'redis'
    CACHE_REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/1'
    CACHE_DEFAULT_TIMEOUT = 300
    CACHE_KEY_PREFIX = 'erp_cache:'
    
    # Security Configuration
    BCRYPT_LOG_ROUNDS = 12  # Higher cost for production
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION = timedelta(minutes=15)
    STRONG_PASSWORD_POLICY = True
    
    # File Upload Security
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = '/app/uploads'
    
    # Monitoring and Error Tracking
    SENTRY_DSN = os.environ.get('SENTRY_DSN')
    SENTRY_ENVIRONMENT = 'production'
    
    # CORS Configuration for production
    CORS_ORIGINS = [
        os.environ.get('FRONTEND_URL', 'https://yourdomain.com'),
        'https://www.yourdomain.com'
    ]
    CORS_SUPPORTS_CREDENTIALS = True
    
    # Email Configuration for production
    MAIL_SUPPRESS_SEND = False
    MAIL_DEBUG = False
    
    # Company Configuration
    COMPANY_NAME = os.environ.get('COMPANY_NAME') or 'نظام إدارة الموارد للشركات'
    COMPANY_EMAIL = os.environ.get('COMPANY_EMAIL') or 'info@yourcompany.com'
    COMPANY_PHONE = os.environ.get('COMPANY_PHONE') or '+966 11 234 5678'
    
    # Feature Flags
    ENABLE_USER_REGISTRATION = os.environ.get('ENABLE_USER_REGISTRATION', 'false').lower() == 'true'
    ENABLE_EMAIL_VERIFICATION = os.environ.get('ENABLE_EMAIL_VERIFICATION', 'true').lower() == 'true'
    ENABLE_TWO_FACTOR_AUTH = os.environ.get('ENABLE_TWO_FACTOR_AUTH', 'false').lower() == 'true'

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=1)  # Short for testing

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
} 