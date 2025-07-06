from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from flask_wtf.csrf import CSRFProtect
import os

# Initialize extensions
db = SQLAlchemy()
jwt = JWTManager()
bcrypt = Bcrypt()
migrate = Migrate()
mail = Mail()

# Shared CSRF protection instance (initialized in app factory)
csrf = CSRFProtect()

# Enhanced Rate Limiter for production
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000 per hour", "50 per minute"],
    headers_enabled=True
)

# Cache for better performance
cache = Cache()

# Initialize Sentry for error tracking in production
def init_sentry(app):
    """Initialize Sentry for error tracking"""
    sentry_dsn = os.environ.get('SENTRY_DSN')
    if sentry_dsn and not app.debug:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.flask import FlaskIntegration
            from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
            
            sentry_sdk.init(
                dsn=sentry_dsn,
                integrations=[
                    FlaskIntegration(),
                    SqlalchemyIntegration()
                ],
                traces_sample_rate=0.1,
                environment=os.environ.get('FLASK_ENV', 'production')
            )
            app.logger.info("Sentry initialized for error tracking")
        except ImportError:
            app.logger.warning("Sentry SDK not installed, skipping error tracking setup")
        except Exception as e:
            app.logger.error(f"Failed to initialize Sentry: {e}")

# Security headers middleware
def setup_security_headers(app):
    """Setup comprehensive security headers for production"""
    
    @app.after_request
    def set_security_headers(response):
        # Get security headers from config
        security_headers = app.config.get('SECURITY_HEADERS', {})
        
        # Default security headers
        default_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'SAMEORIGIN',
            'X-XSS-Protection': '1; mode=block',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'X-Permitted-Cross-Domain-Policies': 'none',
            'Cross-Origin-Embedder-Policy': 'require-corp',
            'Cross-Origin-Opener-Policy': 'same-origin'
        }
        
        # Apply headers
        for header, value in default_headers.items():
            response.headers[header] = value
        
        # Apply custom headers from config
        for header, value in security_headers.items():
            response.headers[header] = value
        
        # HSTS header for HTTPS
        if app.config.get('SECURE_SSL_REDIRECT'):
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        # Content Security Policy
        if not response.headers.get('Content-Security-Policy'):
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
                "style-src-elem 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
                "font-src 'self' https://cdn.jsdelivr.net https://fonts.gstatic.com; "
                "img-src 'self' data: https:; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )
            response.headers['Content-Security-Policy'] = csp
        
        # Remove server information
        response.headers.pop('Server', None)
        response.headers.pop('X-Powered-By', None)
        
        return response

# Request ID middleware for better logging
def setup_request_id(app):
    """Setup request ID for better log tracking"""
    import uuid
    
    @app.before_request
    def add_request_id():
        from flask import g
        g.request_id = str(uuid.uuid4())[:8]
    
    @app.after_request
    def log_request_info(response):
        from flask import g, request
        if hasattr(g, 'request_id'):
            app.logger.info(
                f"Request {g.request_id}: {request.method} {request.path} "
                f"- Status: {response.status_code}"
            )
        return response 