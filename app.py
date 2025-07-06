#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, send_from_directory, redirect, url_for, session, request, jsonify
from flask_cors import CORS
from config.config import Config
from extensions import (
    db, jwt, bcrypt, migrate, mail, limiter, cache,
    init_sentry, setup_security_headers, setup_request_id
)
# Import security features
try:
    from security import security_manager, sanitize_input, validate_jwt_claims
except ImportError:
    security_manager = None
    sanitize_input = lambda x: x
    validate_jwt_claims = lambda f: f
from routes import register_blueprints
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request, create_access_token
from models.user import User
from models.project import Project
from models.client import Client
from models.employee import Employee
from models.task import Task, TaskComment, TaskTimeLog, TaskAssignment
from models.subscription import ClientSubscription, SubscriptionPayment
from models.expense import Expense
from models.timetrack import TimeTrack
from models.invoice import Invoice

def create_app(config_class=Config):
    """Factory function to create Flask application"""
    
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(config_class)
    
    # Initialize Sentry for error tracking (production only)
    init_sentry(app)
    
    # Setup enhanced logging
    setup_logging(app)
    
    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    limiter.init_app(app)
    cache.init_app(app)
    
    # Setup security headers and middleware
    setup_security_headers(app)
    setup_request_id(app)
    setup_security_middleware(app)
    
    # Configure CORS based on environment
    cors_origins = app.config.get('CORS_ORIGINS', ["http://localhost:3000", "http://127.0.0.1:3000"])
    CORS(app, origins=cors_origins)
    
    # Register blueprints
    register_blueprints(app)
    
    # Create database tables and default admin
    with app.app_context():
        db.create_all()
        
        # Create default admin user
        from routes.auth import create_default_admin
        create_default_admin()

    @app.route('/')
    def index():
        """الصفحة الرئيسية - توجيه إلى صفحة تسجيل الدخول"""
        app.logger.info('🏠 زيارة الصفحة الرئيسية')
        return render_template('login.html')

    @app.route('/login')
    def login_page():
        """صفحة تسجيل الدخول"""
        app.logger.info('🔐 زيارة صفحة تسجيل الدخول')
        return render_template('login.html')
    
    @app.route('/logout')
    def logout_page():
        """تسجيل الخروج وإعادة توجيه لصفحة تسجيل الدخول"""
        app.logger.info('👋 تسجيل خروج المستخدم')
        session.clear()
        return redirect(url_for('login_page'))

    @app.route('/dashboard')
    def dashboard_page():
        """صفحة لوحة التحكم"""
        app.logger.info('📊 زيارة لوحة التحكم')
        return render_template('dashboard.html')

    @app.route('/test')
    def api_test_page():
        """صفحة اختبار API"""
        app.logger.info('🧪 زيارة صفحة اختبار API')
        return render_template('api_test.html')

    @app.route('/projects')
    def projects_page():
        """صفحة إدارة المشاريع"""
        app.logger.info('📋 زيارة صفحة المشاريع')
        return render_template('projects.html')

    @app.route('/employees')
    def employees_page():
        """صفحة إدارة الموظفين"""
        app.logger.info('👥 زيارة صفحة الموظفين')
        return render_template('employees.html')

    @app.route('/clients')
    def clients_page():
        """صفحة إدارة العملاء"""
        app.logger.info('👤 زيارة صفحة العملاء')
        return render_template('clients.html')

    @app.route('/clients-enhanced')
    def clients_enhanced_page():
        """صفحة إدارة العملاء المحسنة مع دعم الشركات والأفراد"""
        app.logger.info('👤✨ زيارة صفحة العملاء المحسنة')
        return render_template('clients_enhanced.html')

    @app.route('/subscriptions')
    def subscriptions_page():
        """صفحة إدارة اشتراكات العملاء"""
        app.logger.info('💳 زيارة صفحة الاشتراكات')
        return render_template('subscriptions.html')

    @app.route('/tasks')
    def tasks_page():
        """صفحة إدارة المهام"""
        app.logger.info('✅ زيارة صفحة المهام')
        return render_template('tasks.html')

    @app.route('/reports')
    def reports_page():
        """صفحة التقارير والإحصائيات"""
        app.logger.info('📈 زيارة صفحة التقارير')
        return render_template('reports.html')

    @app.route('/settings')
    def settings_page():
        """صفحة الإعدادات"""
        app.logger.info('⚙️ زيارة صفحة الإعدادات')
        return render_template('index.html')  # placeholder until we create settings.html

    @app.route('/mobile_nav_test.html')
    def mobile_nav_test():
        """صفحة اختبار النافيجيشن للموبايل"""
        app.logger.info('📱 زيارة صفحة اختبار الموبايل')
        return send_from_directory('.', 'mobile_nav_test.html')

    @app.route('/health')
    @cache.cached(timeout=60)  # Cache health check for 1 minute
    def health_check():
        """Health check endpoint with detailed system status"""
        try:
            # Check database connection
            db.session.execute('SELECT 1')
            db_status = "OK"
        except Exception as e:
            app.logger.error(f"Database health check failed: {e}")
            db_status = "FAILED"
        
        # Check cache (if Redis is configured)
        cache_status = "OK"
        try:
            cache.set('health_check', 'test', timeout=1)
            cache.get('health_check')
        except Exception as e:
            app.logger.warning(f"Cache health check failed: {e}")
            cache_status = "WARNING"
        
        health_data = {
            'status': 'OK' if db_status == "OK" else 'FAILED',
            'message': 'Fikra Management System يعمل بنجاح',
            'version': '2.0.0',
            'timestamp': datetime.utcnow().isoformat(),
            'components': {
                'database': db_status,
                'cache': cache_status,
                'authentication': 'OK'
            },
            'environment': os.environ.get('FLASK_ENV', 'development')
        }
        
        status_code = 200 if health_data['status'] == 'OK' else 503
        return jsonify(health_data), status_code
    
    @app.route('/favicon.ico')
    def favicon():
        """Serve favicon"""
        try:
            return send_from_directory(app.static_folder, 'favicon.svg', mimetype='image/svg+xml')
        except:
            # Fallback: serve a simple response
            return '', 204  # No Content
    
    @app.route('/static/favicon.svg')
    def favicon_svg():
        """Serve SVG favicon directly"""
        return send_from_directory(app.static_folder, 'favicon.svg', mimetype='image/svg+xml')
    
    # Enhanced error handlers
    @app.errorhandler(404)
    def not_found(error):
        app.logger.warning(f'❌ 404: الصفحة غير موجودة - {request.url}')
        if request.path.startswith('/api/'):
            return jsonify({'error': 'API endpoint not found', 'message': 'المسار غير موجود'}), 404
        return render_template('login.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'💥 500: خطأ داخلي في الخادم - {error}')
        db.session.rollback()
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Internal server error', 'message': 'خطأ داخلي في الخادم'}), 500
        return render_template('login.html'), 500
    
    @app.errorhandler(403)
    def forbidden(error):
        app.logger.warning(f'🚫 403: وصول مرفوض - {request.url}')
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Access forbidden', 'message': 'وصول مرفوض'}), 403
        return render_template('login.html'), 403
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        app.logger.warning(f'⚠️ Rate limit exceeded: {request.remote_addr} - {request.url}')
        return jsonify({
            'error': 'Rate limit exceeded',
            'message': 'تم تجاوز الحد المسموح من الطلبات',
            'retry_after': str(e.retry_after)
        }), 429
    
    return app

def setup_logging(app):
    """Setup enhanced logging for production"""
    if not app.debug and not app.testing:
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        # File handler with rotation
        file_handler = RotatingFileHandler(
            app.config.get('LOG_FILE', 'logs/erp_system.log'), 
            maxBytes=app.config.get('LOG_MAX_BYTES', 10240000),
            backupCount=app.config.get('LOG_BACKUP_COUNT', 10)
        )
        
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        
        log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO'))
        file_handler.setLevel(log_level)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(log_level)
        app.logger.info('🚀 ERP System production logging initialized')
    
    # Development logging
    if app.debug:
        app.logger.setLevel(logging.DEBUG)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        app.logger.addHandler(console_handler)
        app.logger.debug('🚀 ERP System running in DEBUG mode')

def setup_security_middleware(app):
    """Setup comprehensive security middleware"""
    
    @app.before_request
    def security_checks():
        """Perform security checks before each request"""
        from flask import g
        
        # Skip security checks for static files and health endpoint
        if request.endpoint in ['static', 'health_check', 'favicon', 'favicon_svg']:
            return
        
        if security_manager:
            # Get client IP
            client_ip = security_manager.get_client_ip()
            g.client_ip = client_ip
            
            # Check IP blacklist
            if security_manager.is_ip_blacklisted(client_ip):
                security_manager.record_security_event('BLOCKED_REQUEST', {
                    'ip': client_ip,
                    'endpoint': request.endpoint,
                    'method': request.method,
                    'reason': 'IP blacklisted'
                }, severity='WARNING')
                return jsonify({'error': 'Access denied'}), 403
            
            # Basic rate limiting check (additional to Flask-Limiter)
            if request.method in ['POST', 'PUT', 'DELETE']:
                cache_key = f"rate_limit:{client_ip}:{request.endpoint}"
                requests = cache.get(cache_key) or 0
                
                # Allow up to 100 requests per minute per IP for modification endpoints
                if requests > 100:
                    security_manager.record_security_event('RATE_LIMIT_EXCEEDED', {
                        'ip': client_ip,
                        'endpoint': request.endpoint,
                        'requests': requests
                    }, severity='WARNING')
                    return jsonify({'error': 'Too many requests'}), 429
                
                cache.set(cache_key, requests + 1, timeout=60)
            
            # Check for suspicious patterns in request
            user_agent = request.headers.get('User-Agent', '')
            suspicious_patterns = ['bot', 'crawler', 'spider', 'scraper', 'scanner']
            
            if any(pattern in user_agent.lower() for pattern in suspicious_patterns):
                security_manager.record_security_event('SUSPICIOUS_USER_AGENT', {
                    'ip': client_ip,
                    'user_agent': user_agent,
                    'endpoint': request.endpoint
                }, severity='INFO')
    
    @app.after_request
    def log_request(response):
        """Log request details for security monitoring"""
        if security_manager and not request.endpoint in ['static', 'favicon', 'favicon_svg']:
            # Log all API requests
            if request.path.startswith('/api/'):
                security_manager.record_security_event('API_REQUEST', {
                    'method': request.method,
                    'endpoint': request.endpoint,
                    'status_code': response.status_code,
                    'content_length': response.content_length
                }, severity='INFO')
        
        return response

# Create app instance for import
app = create_app()

if __name__ == '__main__':
    app.logger.info('🌟 Starting ERP System directly...')
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 8005)),
        debug=os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    ) 