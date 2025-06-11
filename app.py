#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, send_from_directory, redirect, url_for, session
from flask_cors import CORS
from config.config import Config
from extensions import db, jwt, bcrypt, migrate, mail, limiter
from routes import register_blueprints
import os

def create_app(config_class=Config):
    """Factory function to create Flask application"""
    
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(config_class)
    
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
        return render_template('login.html')

    @app.route('/login')
    def login_page():
        """صفحة تسجيل الدخول"""
        return render_template('login.html')
    
    @app.route('/logout')
    def logout_page():
        """تسجيل الخروج وإعادة توجيه لصفحة تسجيل الدخول"""
        session.clear()
        return redirect(url_for('login_page'))

    @app.route('/dashboard')
    def dashboard_page():
        """صفحة لوحة التحكم"""
        return render_template('dashboard.html')

    @app.route('/test')
    def api_test_page():
        """صفحة اختبار API"""
        return render_template('api_test.html')

    @app.route('/projects')
    def projects_page():
        """صفحة إدارة المشاريع"""
        return render_template('projects.html')

    @app.route('/employees')
    def employees_page():
        """صفحة إدارة الموظفين"""
        return render_template('employees.html')

    @app.route('/clients')
    def clients_page():
        """صفحة إدارة العملاء"""
        return render_template('clients.html')

    @app.route('/clients-enhanced')
    def clients_enhanced_page():
        """صفحة إدارة العملاء المحسنة مع دعم الشركات والأفراد"""
        return render_template('clients_enhanced.html')

    @app.route('/subscriptions')
    def subscriptions_page():
        """صفحة إدارة اشتراكات العملاء"""
        return render_template('subscriptions.html')

    @app.route('/tasks')
    def tasks_page():
        """صفحة إدارة المهام"""
        return render_template('tasks.html')

    @app.route('/reports')
    def reports_page():
        """صفحة التقارير والإحصائيات"""
        return render_template('reports.html')

    @app.route('/settings')
    def settings_page():
        """صفحة الإعدادات"""
        return render_template('index.html')  # placeholder until we create settings.html

    @app.route('/mobile_nav_test.html')
    def mobile_nav_test():
        """صفحة اختبار النافيجيشن للموبايل"""
        return send_from_directory('.', 'mobile_nav_test.html')

    @app.route('/health')
    def health_check():
        """Health check endpoint"""
        return {
            'status': 'OK',
            'message': 'Fikra Management System يعمل بنجاح',
            'version': '1.0.0'
        }
    
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'الصفحة غير موجودة'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return {'error': 'خطأ داخلي في الخادم'}, 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000) 