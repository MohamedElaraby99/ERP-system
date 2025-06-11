from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, timedelta
from extensions import db, limiter, jwt, bcrypt
from models.user import User
from models.employee import Employee

auth_bp = Blueprint('auth', __name__)

# Store blacklisted tokens
blacklisted_tokens = set()

@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    return jwt_payload['jti'] in blacklisted_tokens

# API endpoints only - pages are handled in app.py
@auth_bp.route('/login', methods=['POST'])
def login():
    """User login API"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'لا توجد بيانات'
            }), 400
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        remember_me = data.get('remember_me', False)
        
        # Validation
        if not email or not password:
            return jsonify({
                'success': False,
                'message': 'البريد الإلكتروني وكلمة المرور مطلوبان'
            }), 400
        
        # Find user
        user = User.query.filter_by(email=email).first()
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'بيانات تسجيل الدخول غير صحيحة'
            }), 401
        
        # Check password using user's check_password method (which uses bcrypt)
        if not user.check_password(password):
            return jsonify({
                'success': False,
                'message': 'بيانات تسجيل الدخول غير صحيحة'
            }), 401
        
        # Check if user is active
        if not user.is_active:
            return jsonify({
                'success': False,
                'message': 'الحساب معطل. تواصل مع الإدارة.'
            }), 401
        
        # Create tokens
        expires_delta = timedelta(days=30) if remember_me else timedelta(hours=24)
        access_token = create_access_token(
            identity=user.id,
            expires_delta=expires_delta
        )
        refresh_token = create_refresh_token(identity=user.id)
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
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
            'last_login': user.last_login.isoformat() if user.last_login else None
        }
        
        print(f"✅ User {user.email} logged in successfully")
        
        return jsonify({
            'success': True,
            'message': f'مرحباً {user.full_name}! تم تسجيل الدخول بنجاح',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user_data,
            'expires_in': int(expires_delta.total_seconds())
        }), 200
        
    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في تسجيل الدخول'
        }), 500

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """User logout API"""
    try:
        # Get JWT token ID to blacklist it
        jti = get_jwt()['jti']
        blacklisted_tokens.add(jti)
        
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        print(f"✅ User {user.email if user else user_id} logged out")
        
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
    """Refresh access token"""
    try:
        current_user = get_jwt_identity()
        new_token = create_access_token(identity=current_user)
        
        return jsonify({
            'success': True,
            'access_token': new_token
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'فشل في تحديث الرمز المميز'
        }), 500

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user info"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'المستخدم غير موجود'
            }), 404
        
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
            'last_login': user.last_login.isoformat() if user.last_login else None
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

@auth_bp.route('/register', methods=['POST'])
def register():
    """User registration API (for admin use)"""
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
        
        email = data['email'].strip().lower()
        username = data['username'].strip().lower()
        
        # Check if user already exists
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
            is_verified=True
        )
        # Set password using the setter
        user.password = data['password']
        
        db.session.add(user)
        db.session.commit()
        
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
    """Change user password"""
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
        
        # Update password
        user.password = data['new_password']
        db.session.commit()
        
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
    """Verify JWT token"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'الرمز المميز غير صالح'
            }), 401
        
        return jsonify({
            'success': True,
            'message': 'الرمز المميز صالح',
            'user': user.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في التحقق من الرمز المميز'
        }), 500 