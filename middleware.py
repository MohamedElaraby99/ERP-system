#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from functools import wraps
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from models.user import User

def role_required(*allowed_roles):
    """
    Decorator لفرض متطلبات الأدوار على المسارات
    """
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            try:
                # الحصول على هوية المستخدم من JWT
                current_user_id = get_jwt_identity()
                
                # البحث عن المستخدم في قاعدة البيانات
                user = User.query.get(current_user_id)
                
                if not user:
                    return jsonify({'message': 'المستخدم غير موجود'}), 404
                
                # التحقق من الدور
                if user.role not in allowed_roles:
                    return jsonify({
                        'message': 'ليس لديك صلاحية للوصول لهذا المورد',
                        'required_roles': list(allowed_roles),
                        'current_role': user.role
                    }), 403
                
                # إضافة معلومات المستخدم للطلب
                request.current_user = user
                
                return f(*args, **kwargs)
                
            except Exception as e:
                return jsonify({'message': 'خطأ في التحقق من الصلاحيات'}), 500
                
        return decorated_function
    return decorator

def admin_required(f):
    """
    Decorator للمسارات التي تتطلب صلاحيات مدير النظام فقط
    """
    return role_required('admin')(f)

def manager_or_admin_required(f):
    """
    Decorator للمسارات التي تتطلب صلاحيات مدير أو مدير النظام
    """
    return role_required('admin', 'manager')(f)

def authenticated_required(f):
    """
    Decorator للمسارات التي تتطلب مستخدم مسجل فقط
    """
    return role_required('admin', 'manager', 'employee')(f)

def get_user_permissions(role):
    """
    إرجاع قائمة بالصلاحيات المتاحة للدور
    """
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

def has_permission(user_role, required_permission):
    """
    التحقق من وجود صلاحية معينة للمستخدم
    """
    user_permissions = get_user_permissions(user_role)
    return required_permission in user_permissions

def permission_required(permission):
    """
    Decorator للتحقق من صلاحية معينة
    """
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            try:
                current_user_id = get_jwt_identity()
                user = User.query.get(current_user_id)
                
                if not user:
                    return jsonify({'message': 'المستخدم غير موجود'}), 404
                
                if not has_permission(user.role, permission):
                    return jsonify({
                        'message': f'ليس لديك صلاحية {permission}',
                        'current_role': user.role
                    }), 403
                
                request.current_user = user
                return f(*args, **kwargs)
                
            except Exception as e:
                return jsonify({'message': 'خطأ في التحقق من الصلاحيات'}), 500
                
        return decorated_function
    return decorator

class RoleChecker:
    """
    كلاس مساعد للتحقق من الأدوار والصلاحيات
    """
    
    @staticmethod
    def can_manage_users(user_role):
        return user_role == 'admin'
    
    @staticmethod
    def can_manage_projects(user_role):
        return user_role in ['admin', 'manager']
    
    @staticmethod
    def can_manage_employees(user_role):
        return user_role in ['admin', 'manager']
    
    @staticmethod
    def can_view_reports(user_role):
        return user_role in ['admin', 'manager']
    
    @staticmethod
    def can_manage_finances(user_role):
        return user_role in ['admin', 'manager']
    
    @staticmethod
    def can_access_dashboard(user_role):
        return user_role in ['admin', 'manager', 'employee']
    
    @staticmethod
    def get_accessible_routes(user_role):
        """
        إرجاع قائمة بالمسارات المتاحة للمستخدم حسب دوره
        """
        routes = {
            'admin': [
                '/dashboard', '/projects', '/employees', '/clients',
                '/tasks', '/reports', '/settings', '/users',
                '/invoices', '/expenses', '/timetrack'
            ],
            'manager': [
                '/dashboard', '/projects', '/employees', '/clients',
                '/tasks', '/reports', '/invoices', '/expenses', '/timetrack'
            ],
            'employee': [
                '/dashboard', '/tasks', '/timetrack', '/profile'
            ]
        }
        
        return routes.get(user_role, [])

def get_role_display_name(role):
    """
    إرجاع الاسم المعروض للدور باللغة العربية
    """
    role_names = {
        'admin': 'مدير النظام',
        'manager': 'مدير',
        'employee': 'موظف'
    }
    return role_names.get(role, role)

def get_available_roles():
    """
    إرجاع قائمة بجميع الأدوار المتاحة
    """
    return [
        {'value': 'admin', 'label': 'مدير النظام'},
        {'value': 'manager', 'label': 'مدير'},
        {'value': 'employee', 'label': 'موظف'}
    ]

def filter_data_by_role(data, user_role, user_id=None):
    """
    فلترة البيانات حسب دور المستخدم
    """
    if user_role == 'admin':
        return data  # المدير يرى كل شيء
    
    elif user_role == 'manager':
        # المدير يرى البيانات المتعلقة بقسمه أو المشاريع المخصصة له
        return data
    
    elif user_role == 'employee':
        # الموظف يرى البيانات المتعلقة به فقط
        if hasattr(data, 'assignee_id'):
            return [item for item in data if item.assignee_id == user_id]
        elif hasattr(data, 'user_id'):
            return [item for item in data if item.user_id == user_id]
    
    return data

def validate_role_hierarchy(current_user_role, target_user_role):
    """
    التحقق من التسلسل الهرمي للأدوار
    """
    hierarchy = {
        'admin': 3,
        'manager': 2,
        'employee': 1
    }
    
    current_level = hierarchy.get(current_user_role, 0)
    target_level = hierarchy.get(target_user_role, 0)
    
    return current_level >= target_level

# ديكوريتر لحماية الصفحات على مستوى الواجهة الأمامية
def login_required_page(f):
    """
    ديكوريتر للصفحات التي تتطلب تسجيل دخول
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # هذا سيتم التعامل معه في JavaScript على الواجهة الأمامية
        return f(*args, **kwargs)
    return decorated_function 