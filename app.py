#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, send_from_directory, redirect, url_for, session, request, jsonify
from flask_cors import CORS
from config.config import Config
from extensions import db, jwt, bcrypt, migrate, mail, limiter
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
    
    # تفعيل التسجيل المفصل
    if not app.debug:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/erp_system.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('ERP System startup')
    
    # تفعيل التسجيل للوحة التحكم أثناء التطوير
    if app.debug:
        app.logger.setLevel(logging.DEBUG)
        # إضافة معالج للكونسول
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        app.logger.addHandler(console_handler)
        app.logger.debug('🚀 ERP System running in DEBUG mode')
    
    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    limiter.init_app(app)
    
    # Configure CORS
    CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000"])
    
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
    def health_check():
        """Health check endpoint"""
        app.logger.info('🏥 فحص صحة النظام')
        return {
            'status': 'OK',
            'message': 'Fikra Management System يعمل بنجاح',
            'version': '1.0.0'
        }
    
    @app.errorhandler(404)
    def not_found(error):
        app.logger.warning(f'❌ 404: الصفحة غير موجودة - {error}')
        return {'error': 'الصفحة غير موجودة'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'💥 500: خطأ داخلي في الخادم - {error}')
        return {'error': 'خطأ داخلي في الخادم'}, 500
    
    return app

# Create app instance for import
app = create_app()

if __name__ == '__main__':
    print("🚀 Starting Flask application with debugging enabled...")
    app.run(debug=True, host='0.0.0.0', port=5000) 