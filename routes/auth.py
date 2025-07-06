from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, timedelta
from extensions import db, limiter, jwt, bcrypt, cache
from models.user import User
from models.employee import Employee
import hashlib
import os
import secrets
import logging

# Import security functions
try:
    from security import (
        security_manager, sanitize_input, validate_password_strength,
        validate_jwt_claims, audit_trail, generate_secure_token
    )
except ImportError:
    # Fallback if security module is not available
    security_manager = None
    sanitize_input = lambda x: x
    validate_password_strength = lambda x: {'is_valid': True, 'errors': []}
    validate_jwt_claims = lambda f: f
    audit_trail = lambda action: lambda f: f
    generate_secure_token = lambda: secrets.token_urlsafe(32)

auth_bp = Blueprint('auth', __name__)

# Store blacklisted tokens (In production, use Redis)
blacklisted_tokens = set()

# Track failed login attempts (In production, use Redis)
failed_attempts = {}
locked_accounts = {}

# Configuration
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)
STRONG_PASSWORD_MIN_LENGTH = 8

@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    return jwt_payload['jti'] in blacklisted_tokens

def is_strong_password(password):
    """Check if password meets security requirements"""
    if len(password) < STRONG_PASSWORD_MIN_LENGTH:
        return False
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*(),.?\":{}|<>" for c in password)
    
    return has_upper and has_lower and has_digit and has_special

def get_client_ip():
    """Get client IP address"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr

def is_account_locked(email):
    """Check if account is locked due to failed attempts"""
    key = f"locked:{email}"
    locked_until = locked_accounts.get(key)
    
    if locked_until and datetime.utcnow() < locked_until:
        return True
    
    # Clean up expired lockouts
    if locked_until and datetime.utcnow() >= locked_until:
        locked_accounts.pop(key, None)
        failed_attempts.pop(email, None)
    
    return False

def record_failed_attempt(email):
    """Record a failed login attempt"""
    if email not in failed_attempts:
        failed_attempts[email] = {'count': 0, 'last_attempt': datetime.utcnow()}
    
    failed_attempts[email]['count'] += 1
    failed_attempts[email]['last_attempt'] = datetime.utcnow()
    
    # Lock account if max attempts exceeded
    if failed_attempts[email]['count'] >= MAX_LOGIN_ATTEMPTS:
        locked_accounts[f"locked:{email}"] = datetime.utcnow() + LOCKOUT_DURATION
        return True
    
    return False

def clear_failed_attempts(email):
    """Clear failed attempts after successful login"""
    failed_attempts.pop(email, None)
    locked_accounts.pop(f"locked:{email}", None)

def generate_secure_token():
    """Generate a secure random token"""
    return secrets.token_urlsafe(32)

# Enhanced login with security features
@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")  # Rate limiting
@audit_trail('USER_LOGIN')
def login():
    """Enhanced user login API with security features"""
    try:
        data = request.get_json()
        
        if not data:
            if security_manager:
                security_manager.record_security_event('LOGIN_NO_DATA', {
                    'endpoint': request.endpoint
                }, severity='WARNING')
            return jsonify({
                'success': False,
                'message': 'لا توجد بيانات'
            }), 400
        
        # Sanitize input data
        email = sanitize_input(data.get('email', '')).strip().lower()
        password = data.get('password', '')  # Don't sanitize password
        remember_me = bool(data.get('remember_me', False))
        
        # Input validation
        if not email or not password:
            if security_manager:
                security_manager.record_security_event('LOGIN_MISSING_CREDENTIALS', {
                    'has_email': bool(email),
                    'has_password': bool(password)
                }, severity='WARNING')
            return jsonify({
                'success': False,
                'message': 'البريد الإلكتروني وكلمة المرور مطلوبان'
            }), 400
        
        # Check IP blacklist if security manager is available
        if security_manager:
            client_ip = security_manager.get_client_ip()
            if security_manager.is_ip_blacklisted(client_ip):
                security_manager.record_security_event('LOGIN_BLACKLISTED_IP', {
                    'ip': client_ip
                }, severity='CRITICAL')
                return jsonify({
                    'success': False,
                    'message': 'الوصول مرفوض من هذا العنوان'
                }), 403
        
        # Check if account is locked
        if is_account_locked(email):
            remaining_time = locked_accounts.get(f"locked:{email}") - datetime.utcnow()
            minutes_left = int(remaining_time.total_seconds() / 60)
            if security_manager:
                security_manager.record_security_event('LOGIN_ACCOUNT_LOCKED', {
                    'email': email,
                    'minutes_remaining': minutes_left
                }, severity='WARNING')
            return jsonify({
                'success': False,
                'message': f'الحساب مقفل بسبب محاولات دخول فاشلة. المحاولة مرة أخرى خلال {minutes_left} دقيقة',
                'locked_until': locked_accounts.get(f"locked:{email}").isoformat()
            }), 423  # HTTP 423 Locked
        
        # Find user
        user = User.query.filter_by(email=email).first()
        
        if not user:
            record_failed_attempt(email)
            if security_manager:
                security_manager.record_security_event('LOGIN_USER_NOT_FOUND', {
                    'email': email
                }, severity='WARNING')
            return jsonify({
                'success': False,
                'message': 'بيانات تسجيل الدخول غير صحيحة'
            }), 401
        
        # Check password
        if not user.check_password(password):
            is_locked = record_failed_attempt(email)
            if security_manager:
                security_manager.record_security_event('LOGIN_INVALID_PASSWORD', {
                    'email': email,
                    'user_id': user.id,
                    'account_locked': is_locked
                }, user_id=user.id, severity='WARNING')
            
            if is_locked:
                return jsonify({
                    'success': False,
                    'message': f'تم قفل الحساب بسبب {MAX_LOGIN_ATTEMPTS} محاولات دخول فاشلة. المحاولة مرة أخرى خلال {LOCKOUT_DURATION.seconds // 60} دقيقة'
                }), 423
            
            attempts_left = MAX_LOGIN_ATTEMPTS - failed_attempts.get(email, {}).get('count', 0)
            return jsonify({
                'success': False,
                'message': f'بيانات تسجيل الدخول غير صحيحة. محاولات متبقية: {attempts_left}'
            }), 401
        
        # Check if user is active
        if not user.is_active:
            if security_manager:
                security_manager.record_security_event('LOGIN_INACTIVE_USER', {
                    'email': email,
                    'user_id': user.id
                }, user_id=user.id, severity='WARNING')
            return jsonify({
                'success': False,
                'message': 'الحساب معطل. تواصل مع الإدارة.'
            }), 401
        
        # Clear failed attempts on successful login
        clear_failed_attempts(email)
        
        # Create tokens with enhanced security
        expires_delta = timedelta(days=30) if remember_me else timedelta(hours=1)
        
        # Add additional claims for security
        additional_claims = {
            'ip': get_client_ip(),
            'user_agent': request.headers.get('User-Agent', '')[:100],  # Truncate for security
            'login_time': datetime.utcnow().isoformat(),
            'remember_me': remember_me
        }
        
        access_token = create_access_token(
            identity=user.id,
            expires_delta=expires_delta,
            additional_claims=additional_claims
        )
        refresh_token = create_refresh_token(identity=user.id)
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Log successful login
        if security_manager:
            security_manager.record_security_event('LOGIN_SUCCESS', {
                'email': email,
                'user_id': user.id,
                'role': user.role,
                'remember_me': remember_me,
                'expires_in': int(expires_delta.total_seconds())
            }, user_id=user.id, severity='INFO')
        
        # Prepare user data
        user_data = {
            'id': user.id,
            'name': user.full_name,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'is_admin': user.role == 'admin',
            'avatar_url': user.avatar,
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'permissions': get_user_permissions(user.role)
        }
        
        # Log successful login to console
        print(f"✅ User {user.email} logged in successfully from IP {get_client_ip()}")
        
        return jsonify({
            'success': True,
            'message': f'مرحباً {user.full_name}! تم تسجيل الدخول بنجاح',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user_data,
            'expires_in': int(expires_delta.total_seconds()),
            'security_info': {
                'login_ip': get_client_ip(),
                'login_time': datetime.utcnow().isoformat(),
                'session_timeout': expires_delta.total_seconds()
            }
        }), 200
        
    except Exception as e:
        if security_manager:
            security_manager.record_security_event('LOGIN_ERROR', {
                'error': str(e),
                'endpoint': request.endpoint
            }, severity='ERROR')
        print(f"❌ Login error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في تسجيل الدخول'
        }), 500

def get_user_permissions(role):
    """Get user permissions based on role"""
    permissions = {
        'admin': [
            'read_all', 'write_all', 'delete_all',
            'manage_users', 'manage_projects', 'manage_clients',
            'manage_employees', 'manage_tasks', 'manage_invoices',
            'manage_expenses', 'view_reports', 'manage_settings'
        ],
        'manager': [
            'read_projects', 'write_projects',
            'read_employees', 'write_employees',
            'read_clients', 'write_clients',
            'read_tasks', 'write_tasks',
            'read_invoices', 'write_invoices',
            'read_expenses', 'write_expenses',
            'view_reports'
        ],
        'employee': [
            'read_own_tasks', 'write_own_tasks',
            'read_own_timetrack', 'write_own_timetrack',
            'read_own_profile', 'write_own_profile',
            'read_projects', 'read_clients'
        ]
    }
    return permissions.get(role, [])

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Enhanced user logout API"""
    try:
        # Get JWT token ID to blacklist it
        jti = get_jwt()['jti']
        blacklisted_tokens.add(jti)
        
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        # Log logout activity
        print(f"✅ User {user.email if user else user_id} logged out from IP {get_client_ip()}")
        
        return jsonify({
            'success': True,
            'message': 'تم تسجيل الخروج بنجاح'
        }), 200
        
    except Exception as e:
        print(f"❌ Logout error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في تسجيل الخروج'
        }), 500

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Enhanced refresh access token with security checks"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_active:
            return jsonify({
                'success': False,
                'message': 'المستخدم غير موجود أو معطل'
            }), 401
        
        # Create new access token with current claims
        additional_claims = {
            'ip': get_client_ip(),
            'user_agent': request.headers.get('User-Agent', '')[:100],
            'refresh_time': datetime.utcnow().isoformat()
        }
        
        new_token = create_access_token(
            identity=current_user_id,
            additional_claims=additional_claims
        )
        
        return jsonify({
            'success': True,
            'access_token': new_token,
            'expires_in': 3600  # 1 hour for production
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'فشل في تحديث الرمز المميز'
        }), 500

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user info with security validation"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'المستخدم غير موجود'
            }), 404
        
        # Security check - validate IP if available in token
        token_claims = get_jwt()
        token_ip = token_claims.get('ip')
        current_ip = get_client_ip()
        
        # Log IP mismatch (potential session hijacking)
        if token_ip and token_ip != current_ip:
            print(f"⚠️ IP mismatch for user {user.email}: token IP {token_ip} vs current IP {current_ip}")
        
        user_data = {
            'id': user.id,
            'name': user.full_name,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'is_admin': user.role == 'admin',
            'avatar_url': user.avatar,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'permissions': get_user_permissions(user.role),
            'security_info': {
                'login_ip': token_ip,
                'current_ip': current_ip,
                'login_time': token_claims.get('login_time')
            }
        }
        
        return jsonify({
            'success': True,
            'user': user_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب بيانات المستخدم'
        }), 500

# Rest of the original auth.py functions with minor security enhancements...
@auth_bp.route('/register', methods=['POST'])
@limiter.limit("3 per hour")  # Limit registrations
def register():
    """Enhanced user registration API"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['first_name', 'last_name', 'username', 'email', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'الحقل {field} مطلوب'
                }), 400
        
        # Enhanced password validation
        password = data['password']
        if not is_strong_password(password):
            return jsonify({
                'success': False,
                'message': f'كلمة المرور يجب أن تحتوي على الأقل {STRONG_PASSWORD_MIN_LENGTH} أحرف وتشمل أحرف كبيرة وصغيرة وأرقام ورموز خاصة'
            }), 400
        
        username = data['username'].strip().lower()
        email = data['email'].strip().lower()
        
        # Check for existing users
        if User.query.filter_by(email=email).first():
            return jsonify({
                'success': False,
                'message': 'هذا البريد الإلكتروني مسجل بالفعل'
            }), 400
            
        if User.query.filter_by(username=username).first():
            return jsonify({
                'success': False,
                'message': 'اسم المستخدم مستخدم بالفعل'
            }), 400
        
        # Create new user
        user = User(
            first_name=data['first_name'],
            last_name=data['last_name'],
            username=username,
            email=email,
            role=data.get('role', 'employee'),
            phone=data.get('phone'),
            is_active=True,
            is_verified=False  # Require email verification in production
        )
        # Set password using the setter
        user.password = password
        
        db.session.add(user)
        db.session.commit()
        
        # Log registration
        print(f"✅ New user registered: {user.email} from IP {get_client_ip()}")
        
        return jsonify({
            'success': True,
            'message': 'تم إنشاء الحساب بنجاح',
            'user': {
                'id': user.id,
                'name': user.full_name,
                'email': user.email,
                'role': user.role
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Registration error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في إنشاء الحساب'
        }), 500

# Utility functions
def create_default_admin():
    """Create default admin user if not exists"""
    try:
        # Check if admin user already exists by email or username
        admin_by_email = User.query.filter_by(email='admin@erp.com').first()
        admin_by_username = User.query.filter_by(username='admin').first()
        
        if admin_by_email or admin_by_username:
            if admin_by_email:
                print("✅ Default admin user already exists: admin@erp.com")
                return admin_by_email
            else:
                print("✅ Username 'admin' already exists, skipping admin creation")
                return admin_by_username
        
        # Create admin user if none exists
        admin = User(
            first_name='المدير',
            last_name='العام',
            username='admin',
            email='admin@erp.com',
            role='admin',
            is_active=True,
            is_verified=True
        )
        # Set password using the setter
        admin.password = 'admin123'
        
        db.session.add(admin)
        db.session.commit()
        
        print("✅ Default admin user created: admin@erp.com / admin123")
        print("⚠️  SECURITY WARNING: Change default admin password in production!")
        return admin
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error creating default admin: {str(e)}")
        return None

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get user profile"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        
        return jsonify({
            'success': True,
            'user': user.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'خطأ في جلب الملف الشخصي'
        }), 500

@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update user profile"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        data = request.get_json()
        
        # Update allowed fields
        allowed_fields = ['first_name', 'last_name', 'phone', 'avatar']
        for field in allowed_fields:
            if field in data:
                setattr(user, field, data[field])
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        print(f"✅ Profile updated for user {user.email}")
        
        return jsonify({
            'success': True,
            'message': 'تم تحديث الملف الشخصي بنجاح',
            'user': user.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'خطأ في تحديث الملف الشخصي'
        }), 500

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
@limiter.limit("3 per minute")
def change_password():
    """Enhanced change user password with security checks"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        data = request.get_json()
        
        if not data.get('current_password') or not data.get('new_password'):
            return jsonify({
                'success': False,
                'message': 'كلمة المرور الحالية والجديدة مطلوبة'
            }), 400
        
        # Check current password
        if not user.check_password(data['current_password']):
            return jsonify({
                'success': False,
                'message': 'كلمة المرور الحالية غير صحيحة'
            }), 400
        
        # Validate new password strength
        new_password = data['new_password']
        if not is_strong_password(new_password):
            return jsonify({
                'success': False,
                'message': f'كلمة المرور الجديدة يجب أن تحتوي على الأقل {STRONG_PASSWORD_MIN_LENGTH} أحرف وتشمل أحرف كبيرة وصغيرة وأرقام ورموز خاصة'
            }), 400
        
        # Check if new password is different from current
        if user.check_password(new_password):
            return jsonify({
                'success': False,
                'message': 'كلمة المرور الجديدة يجب أن تكون مختلفة عن الحالية'
            }), 400
        
        # Update password
        user.password = new_password
        db.session.commit()
        
        # Log password change
        print(f"✅ Password changed for user {user.email} from IP {get_client_ip()}")
        
        return jsonify({
            'success': True,
            'message': 'تم تغيير كلمة المرور بنجاح'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'خطأ في تغيير كلمة المرور'
        }), 500

@auth_bp.route('/verify', methods=['GET'])
@jwt_required()
def verify_token():
    """Enhanced verify JWT token with security checks"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'الرمز المميز غير صالح'
            }), 401
        
        # Additional security checks
        token_claims = get_jwt()
        
        # Check if user is still active
        if not user.is_active:
            return jsonify({
                'success': False,
                'message': 'الحساب معطل'
            }), 401
        
        return jsonify({
            'success': True,
            'message': 'الرمز المميز صالح',
            'user': user.to_dict(),
            'token_info': {
                'ip': token_claims.get('ip'),
                'login_time': token_claims.get('login_time'),
                'current_ip': get_client_ip()
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في التحقق من الرمز المميز'
        }), 500 