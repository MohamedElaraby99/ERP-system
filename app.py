#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, send_from_directory, redirect, url_for, session, request, jsonify
from flask_cors import CORS
from config.config import Config
from extensions import (
    db, jwt, bcrypt, migrate, mail, limiter, cache,
    init_sentry, setup_security_headers, setup_request_id, csrf
)
from flask_wtf.csrf import CSRFProtect
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

def setup_logging(app):
    """Setup enhanced logging"""
    logging.basicConfig(level=logging.DEBUG)
    
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    # Create file handler
    file_handler = RotatingFileHandler(
        'logs/erp.log',
        maxBytes=10240,
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.DEBUG)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    console_handler.setLevel(logging.DEBUG)
    
    # Add handlers to app logger
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.DEBUG)
    
    # Log all requests
    @app.before_request
    def log_request_info():
        app.logger.debug('Headers: %s', dict(request.headers))
        app.logger.debug('Body: %s', request.get_data())

def create_app(config_class=Config):
    """Create and configure the Flask application"""
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(config_class)
    
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
    
    # Initialize CSRF protection (shared instance)
    csrf.init_app(app)
    
    # Configure CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:8005", "http://127.0.0.1:8005"],
            "supports_credentials": True,
            "allow_headers": ["Content-Type", "Authorization", "X-CSRFToken"],
            "expose_headers": ["Content-Type", "X-CSRFToken"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        }
    })
    
    # Register blueprints
    register_blueprints(app)
    
    # Setup security headers
    setup_security_headers(app)

    # Setup request ID
    setup_request_id(app)

    # Initialize Sentry if configured
    init_sentry(app)

    # Log startup
    app.logger.info('ERP System startup')
    
    # CSRF exempt routes
    csrf.exempt(app.blueprints['auth_api'])
    
    return app

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