#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app import create_app
from extensions import db
from models.user import User
from models.employee import Employee
from models.client import Client
from models.project import Project
from models.task import Task
from models.timetrack import TimeTrack
from models.expense import Expense
from models.invoice import Invoice
from datetime import datetime, date, timedelta
import random

def create_sample_data():
    """Create sample data for the ERP system"""
    
    app = create_app()
    
    with app.app_context():
        # Clear existing data
        db.drop_all()
        db.create_all()
        
        print("إنشاء البيانات التجريبية...")
        
        # Create admin user
        admin_user = User(
            email='admin@erpsystem.com',
            username='admin',
            first_name='أحمد',
            last_name='المدير',
            role='admin',
            is_active=True,
            is_verified=True
        )
        admin_user.password = 'admin123'
        db.session.add(admin_user)
        
        # Create sample client
        client = Client(
            name='شركة التقنية المتقدمة',
            email='info@techadvanced.com',
            phone='+966 11 1234567',
            industry='تقنية المعلومات',
            contact_person='خالد العتيبي',
            status='active'
        )
        db.session.add(client)
        
        # Create sample employee
        employee = Employee(
            employee_id='EMP1001',
            first_name='محمد',
            last_name='علي',
            email='mohamed@erpsystem.com',
            position='مطور ويب أول',
            department='التطوير',
            hire_date=date.today() - timedelta(days=365),
            status='active'
        )
        db.session.add(employee)
        
        db.session.commit()
        
        # Create sample project
        project = Project(
            name='تطوير موقع تجارة إلكترونية',
            project_code='ECOM-2024-001',
            description='تطوير موقع تجارة إلكترونية متكامل',
            status='active',
            priority='high',
            category='web_app',
            budget=150000,
            start_date=date.today() - timedelta(days=30),
            end_date=date.today() + timedelta(days=60),
            progress=45,
            client_id=client.id,
            created_by=admin_user.id
        )
        db.session.add(project)
        
        db.session.commit()
        
        # Create sample task
        task = Task(
            title='تطوير واجهة المستخدم الرئيسية',
            description='تطوير الصفحة الرئيسية وواجهات التسوق',
            status='in_progress',
            priority='high',
            category='development',
            estimated_hours=40,
            project_id=project.id,
            assigned_to=admin_user.id,
            created_by=admin_user.id,
            due_date=date.today() + timedelta(days=14)
        )
        db.session.add(task)
        
        db.session.commit()
        
        print("✅ تم إنشاء البيانات التجريبية بنجاح!")
        print("\n📋 بيانات الدخول:")
        print("البريد الإلكتروني: admin@erpsystem.com")
        print("كلمة المرور: admin123")
        print("\n🚀 يمكنك الآن تشغيل الخادم باستخدام: python app.py")

if __name__ == '__main__':
    create_sample_data() 