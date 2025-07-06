#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Security Module for ERP System
Provides comprehensive security features including IP validation, audit logging, 
input sanitization, and enhanced authentication security.
"""

import os
import re
import hashlib
import secrets
import logging
import time
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, List, Optional, Any
from flask import request, jsonify, current_app, g, session
from flask_jwt_extended import get_jwt_identity, get_jwt, verify_jwt_in_request
import ipaddress
from werkzeug.useragents import UserAgent
import bleach
from extensions import db, cache, limiter

# Configure security logger
security_logger = logging.getLogger('security')

class SecurityManager:
    """Central security management class"""
    
    def __init__(self):
        self.failed_attempts = {}
        self.blacklisted_ips = set()
        self.security_events = []
    
    def record_security_event(self, event_type: str, details: Dict[str, Any], 
                            user_id: Optional[int] = None, severity: str = 'INFO'):
        """Record security events for audit purposes"""
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'details': details,
            'user_id': user_id,
            'ip_address': self.get_client_ip(),
            'user_agent': request.headers.get('User-Agent', 'Unknown')[:200],
            'severity': severity
        }
        
        # Log to file
        security_logger.info(f"Security Event: {event_type} - {details}")
        
        # Store in cache for recent events (optional: store in database)
        cache_key = f"security_events:{datetime.utcnow().strftime('%Y-%m-%d')}"
        try:
            events = cache.get(cache_key) or []
            events.append(event)
            cache.set(cache_key, events, timeout=86400)  # 24 hours
        except Exception as e:
            security_logger.error(f"Failed to cache security event: {e}")
    
    @staticmethod
    def get_client_ip() -> str:
        """Get real client IP address considering proxies"""
        # Check various headers for real IP
        ip_headers = [
            'X-Forwarded-For',
            'X-Real-IP',
            'X-Original-Forwarded-For',
            'CF-Connecting-IP',  # Cloudflare
            'True-Client-IP'
        ]
        
        for header in ip_headers:
            ip = request.headers.get(header)
            if ip:
                # Take the first IP if comma-separated
                ip = ip.split(',')[0].strip()
                try:
                    # Validate IP address
                    ipaddress.ip_address(ip)
                    return ip
                except ValueError:
                    continue
        
        return request.remote_addr or 'unknown'
    
    def is_ip_blacklisted(self, ip: str) -> bool:
        """Check if IP is blacklisted"""
        return ip in self.blacklisted_ips
    
    def blacklist_ip(self, ip: str, reason: str, duration_hours: int = 24):
        """Blacklist an IP address"""
        self.blacklisted_ips.add(ip)
        cache.set(f"blacklisted_ip:{ip}", {
            'reason': reason,
            'blacklisted_at': datetime.utcnow().isoformat(),
            'duration_hours': duration_hours
        }, timeout=duration_hours * 3600)
        
        self.record_security_event('IP_BLACKLISTED', {
            'ip': ip,
            'reason': reason,
            'duration_hours': duration_hours
        }, severity='WARNING')
    
    def validate_ip_location(self, ip: str) -> bool:
        """Basic IP location validation (can be enhanced with GeoIP)"""
        try:
            ip_obj = ipaddress.ip_address(ip)
            
            # Block known malicious ranges (example)
            if ip_obj.is_private or ip_obj.is_loopback:
                return True  # Allow private/local IPs
            
            # Add your IP validation logic here
            # For example, you could integrate with GeoIP databases
            # to block specific countries or regions
            
            return True
        except ValueError:
            return False

# Initialize security manager
security_manager = SecurityManager()

def sanitize_input(data: Any, allowed_tags: List[str] = None) -> Any:
    """Sanitize user input to prevent XSS and injection attacks"""
    if allowed_tags is None:
        allowed_tags = []
    
    if isinstance(data, str):
        # Remove potentially dangerous characters
        cleaned = bleach.clean(data, tags=allowed_tags, strip=True)
        return cleaned.strip()
    elif isinstance(data, dict):
        return {key: sanitize_input(value, allowed_tags) for key, value in data.items()}
    elif isinstance(data, list):
        return [sanitize_input(item, allowed_tags) for item in data]
    else:
        return data

def validate_password_strength(password: str) -> Dict[str, Any]:
    """Validate password strength according to security policy"""
    result = {
        'is_valid': True,
        'errors': [],
        'score': 0
    }
    
    if len(password) < 8:
        result['errors'].append('كلمة المرور يجب أن تكون 8 أحرف على الأقل')
        result['is_valid'] = False
    else:
        result['score'] += 1
    
    if not re.search(r'[A-Z]', password):
        result['errors'].append('كلمة المرور يجب أن تحتوي على حرف كبير واحد على الأقل')
        result['is_valid'] = False
    else:
        result['score'] += 1
    
    if not re.search(r'[a-z]', password):
        result['errors'].append('كلمة المرور يجب أن تحتوي على حرف صغير واحد على الأقل')
        result['is_valid'] = False
    else:
        result['score'] += 1
    
    if not re.search(r'\d', password):
        result['errors'].append('كلمة المرور يجب أن تحتوي على رقم واحد على الأقل')
        result['is_valid'] = False
    else:
        result['score'] += 1
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        result['errors'].append('كلمة المرور يجب أن تحتوي على رمز خاص واحد على الأقل')
        result['is_valid'] = False
    else:
        result['score'] += 1
    
    # Check for common passwords
    common_passwords = ['password', '123456', 'admin', 'qwerty', 'letmein']
    if password.lower() in common_passwords:
        result['errors'].append('كلمة المرور شائعة جداً، يرجى اختيار كلمة مرور أكثر تعقيداً')
        result['is_valid'] = False
    
    return result

def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token"""
    return secrets.token_urlsafe(length)

def hash_data(data: str, salt: str = None) -> str:
    """Hash data with optional salt"""
    if salt is None:
        salt = secrets.token_hex(16)
    
    return hashlib.pbkdf2_hmac('sha256', data.encode(), salt.encode(), 100000).hex()

def validate_file_upload(file) -> Dict[str, Any]:
    """Validate uploaded file for security"""
    result = {
        'is_valid': True,
        'errors': []
    }
    
    if not file:
        result['errors'].append('لم يتم اختيار ملف')
        result['is_valid'] = False
        return result
    
    # Check file extension
    allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', {'txt', 'pdf', 'png', 'jpg'})
    file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    
    if file_ext not in allowed_extensions:
        result['errors'].append(f'نوع الملف غير مسموح. الأنواع المسموحة: {", ".join(allowed_extensions)}')
        result['is_valid'] = False
    
    # Check file size
    max_size = current_app.config.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)
    if hasattr(file, 'content_length') and file.content_length > max_size:
        result['errors'].append(f'حجم الملف كبير جداً. الحد الأقصى: {max_size // (1024*1024)} ميجابايت')
        result['is_valid'] = False
    
    return result

def require_api_key(f):
    """Decorator to require API key for certain endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        expected_key = current_app.config.get('API_KEY')
        
        if not api_key or not expected_key or api_key != expected_key:
            security_manager.record_security_event('INVALID_API_KEY', {
                'endpoint': request.endpoint,
                'provided_key': api_key[:10] + '...' if api_key else None
            }, severity='WARNING')
            
            return jsonify({'error': 'Invalid or missing API key'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

def validate_jwt_claims(f):
    """Decorator to validate additional JWT claims"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request()
            claims = get_jwt()
            current_ip = security_manager.get_client_ip()
            
            # Validate IP address if stored in token
            token_ip = claims.get('ip')
            if token_ip and token_ip != current_ip:
                security_manager.record_security_event('IP_MISMATCH', {
                    'token_ip': token_ip,
                    'current_ip': current_ip,
                    'user_id': get_jwt_identity()
                }, severity='WARNING')
                
                return jsonify({'error': 'Invalid session - IP mismatch'}), 401
            
            # Check token age
            issued_at = claims.get('iat')
            if issued_at:
                token_age = datetime.utcnow().timestamp() - issued_at
                max_age = current_app.config.get('JWT_MAX_AGE_SECONDS', 86400)  # 24 hours
                
                if token_age > max_age:
                    return jsonify({'error': 'Token expired due to age'}), 401
            
        except Exception as e:
            security_manager.record_security_event('JWT_VALIDATION_ERROR', {
                'error': str(e)
            }, severity='ERROR')
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

def rate_limit_by_user(limit: str):
    """Rate limiting decorator based on user ID"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                verify_jwt_in_request()
                user_id = get_jwt_identity()
                key = f"user:{user_id}"
            except:
                key = security_manager.get_client_ip()
            
            # Apply rate limiting
            limiter.limit(limit, key_func=lambda: key)(f)(*args, **kwargs)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def audit_trail(action: str):
    """Decorator to create audit trail for sensitive actions"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = datetime.utcnow()
            user_id = None
            
            try:
                verify_jwt_in_request()
                user_id = get_jwt_identity()
            except:
                pass
            
            # Execute function
            try:
                result = f(*args, **kwargs)
                status = 'SUCCESS'
                error_msg = None
            except Exception as e:
                result = None
                status = 'FAILED'
                error_msg = str(e)
                raise
            finally:
                # Record audit event
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                security_manager.record_security_event('AUDIT_TRAIL', {
                    'action': action,
                    'status': status,
                    'execution_time': execution_time,
                    'error': error_msg,
                    'endpoint': request.endpoint,
                    'method': request.method
                }, user_id=user_id)
            
            return result
        return decorated_function
    return decorator

def setup_csrf_protection():
    """Setup CSRF protection utilities"""
    def generate_csrf_token():
        if 'csrf_token' not in session:
            session['csrf_token'] = generate_secure_token()
        return session['csrf_token']
    
    def validate_csrf_token(token):
        return token and session.get('csrf_token') == token
    
    return generate_csrf_token, validate_csrf_token

# Initialize CSRF protection
generate_csrf_token, validate_csrf_token = setup_csrf_protection()

def validate_email(email):
    """Validate email format with security considerations"""
    if not email or len(email) > 254:
        return False, "عنوان بريد إلكتروني غير صالح"
    
    # Basic email regex (RFC 5322 compliant)
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, email):
        return False, "تنسيق البريد الإلكتروني غير صالح"
    
    # Check for dangerous patterns
    dangerous_patterns = [
        r'[<>]',  # XSS attempts
        r'javascript:',  # Script injection
        r'data:',  # Data URLs
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, email.lower()):
            return False, "البريد الإلكتروني يحتوي على محتوى غير آمن"
    
    return True, "البريد الإلكتروني صالح"

def validate_phone(phone):
    """Validate phone number format"""
    if not phone:
        return True, "رقم الهاتف اختياري"
    
    # Remove spaces and special characters for validation
    clean_phone = re.sub(r'[^\d+]', '', phone)
    
    # Basic phone validation (international format)
    if not re.match(r'^\+?[1-9]\d{6,14}$', clean_phone):
        return False, "تنسيق رقم الهاتف غير صالح"
    
    return True, "رقم الهاتف صالح"

def check_ip_reputation(ip_address):
    """Check IP address reputation (basic implementation)"""
    try:
        ip = ipaddress.ip_address(ip_address)
        
        # Check if it's a private IP (should be allowed in most cases)
        if ip.is_private:
            return True, "عنوان IP محلي"
        
        # Check if it's a loopback address
        if ip.is_loopback:
            return True, "عنوان IP محلي"
        
        # In production, you would integrate with IP reputation services
        # For now, we'll implement basic checks
        
        # Block known malicious IP ranges (example)
        malicious_ranges = [
            '10.0.0.0/8',  # This is just an example - don't actually block private IPs
        ]
        
        for range_str in malicious_ranges:
            if ip in ipaddress.ip_network(range_str):
                return False, "عنوان IP مشبوه"
        
        return True, "عنوان IP آمن"
        
    except ValueError:
        return False, "عنوان IP غير صالح"

def rate_limit_decorator(max_requests=60, window_seconds=3600):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.remote_addr
            
            # Check if IP is blocked
            if security_manager.is_ip_blacklisted(client_ip):
                security_manager.record_security_event('BLOCKED_IP_ATTEMPT', {
                    'ip': client_ip,
                    'endpoint': request.endpoint
                }, severity='WARNING')
                return jsonify({
                    'error': 'Access denied',
                    'message': 'عنوان IP محجوب'
                }), 403
            
            # Implement simple rate limiting
            current_time = time.time()
            key = f"rate_limit:{client_ip}:{request.endpoint}"
            
            # In production, use Redis for this
            # For now, use a simple in-memory approach
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def secure_headers_decorator(f):
    """Add security headers to response"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = f(*args, **kwargs)
        
        # Add security headers
        if hasattr(response, 'headers'):
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'SAMEORIGIN'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            response.headers['Content-Security-Policy'] = "default-src 'self'"
        
        return response
    
    return decorated_function

def hash_sensitive_data(data):
    """Hash sensitive data for logging/storage"""
    if not data:
        return None
    
    # Use SHA-256 for non-reversible hashing
    return hashlib.sha256(str(data).encode()).hexdigest()[:16]

def generate_csrf_token():
    """Generate CSRF token"""
    return secrets.token_urlsafe(32)

def validate_csrf_token(token, session_token):
    """Validate CSRF token"""
    return secrets.compare_digest(token, session_token)

def audit_log(action, user_id, details=None):
    """Create audit log entry"""
    log_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'action': action,
        'user_id': user_id,
        'ip_address': request.remote_addr if request else 'system',
        'user_agent': request.headers.get('User-Agent')[:200] if request else 'system',
        'details': details or {}
    }
    
    # In production, store in database or external logging service
    security_manager.record_security_event('AUDIT_LOG', log_entry)

class SecurityMiddleware:
    """Security middleware for Flask application"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize security middleware"""
        
        @app.before_request
        def security_checks():
            """Perform security checks before each request"""
            
            # Check IP reputation
            client_ip = request.remote_addr
            is_safe, message = check_ip_reputation(client_ip)
            
            if not is_safe:
                security_manager.record_security_event('MALICIOUS_IP_BLOCKED', {
                    'ip': client_ip,
                    'reason': message
                }, severity='WARNING')
                return jsonify({
                    'error': 'Access denied',
                    'message': 'الوصول مرفوض'
                }), 403
            
            # Check if IP is blocked
            if security_manager.is_ip_blacklisted(client_ip):
                return jsonify({
                    'error': 'IP blocked',
                    'message': 'تم حجب عنوان IP'
                }), 403
            
            # Validate request size
            if request.content_length and request.content_length > 16 * 1024 * 1024:  # 16MB
                return jsonify({
                    'error': 'Request too large',
                    'message': 'حجم الطلب كبير جداً'
                }), 413
        
        @app.after_request
        def add_security_headers(response):
            """Add security headers to all responses"""
            
            # Security headers
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'SAMEORIGIN'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            
            # Remove server information
            response.headers.pop('Server', None)
            
            # HSTS header for HTTPS
            if request.is_secure:
                response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            
            return response

# Utility functions for common security operations
def mask_sensitive_data(data, mask_char='*', visible_chars=3):
    """Mask sensitive data for display"""
    if not data or len(data) <= visible_chars:
        return mask_char * len(data) if data else ''
    
    return data[:visible_chars] + mask_char * (len(data) - visible_chars)

def secure_filename(filename):
    """Make filename secure for storage"""
    # Remove dangerous characters
    filename = re.sub(r'[^\w\-_\.]', '', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:250] + ('.' + ext if ext else '')
    
    return filename or 'unnamed_file'

def validate_file_upload(file, allowed_extensions=None, max_size=16*1024*1024):
    """Validate file upload for security"""
    if not file or not file.filename:
        return False, "لم يتم اختيار ملف"
    
    # Check file size
    if hasattr(file, 'content_length') and file.content_length > max_size:
        return False, f"حجم الملف كبير جداً (الحد الأقصى: {max_size // (1024*1024)}MB)"
    
    # Check file extension
    if allowed_extensions:
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if ext not in allowed_extensions:
            return False, f"نوع الملف غير مسموح. الأنواع المسموحة: {', '.join(allowed_extensions)}"
    
    # Check for potentially dangerous filenames
    dangerous_names = ['..', '.htaccess', 'web.config', 'index.php']
    if any(danger in file.filename.lower() for danger in dangerous_names):
        return False, "اسم الملف غير آمن"
    
    return True, "الملف صالح" 