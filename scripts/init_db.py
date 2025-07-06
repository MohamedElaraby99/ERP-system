#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ERP System Database Initialization Script
This script initializes the database with required tables and default data.
"""

import os
import sys
import logging
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import create_app
from extensions import db
from models.user import User
from models.employee import Employee
from models.client import Client
from models.project import Project

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def init_database():
    """Initialize database with tables and default data"""
    
    logger.info("🚀 Starting database initialization...")
    
    # Create Flask app
    app = create_app()
    
    with app.app_context():
        try:
            # Drop all tables if they exist (for fresh start)
            if os.environ.get('RESET_DB', 'false').lower() == 'true':
                logger.warning("⚠️ Dropping all existing tables...")
                db.drop_all()
            
            # Create all tables
            logger.info("📊 Creating database tables...")
            db.create_all()
            logger.info("✅ Database tables created successfully")
            
            # Create default admin user
            create_default_admin()
            
            # Create sample data if requested
            if os.environ.get('CREATE_SAMPLE_DATA', 'false').lower() == 'true':
                create_sample_data()
            
            # Commit all changes
            db.session.commit()
            logger.info("💾 All changes committed to database")
            
            logger.info("🎉 Database initialization completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            db.session.rollback()
            raise
        
def create_default_admin():
    """Create default admin user if it doesn't exist"""
    
    admin_email = os.environ.get('ADMIN_EMAIL', 'admin@company.com')
    admin_password = os.environ.get('ADMIN_PASSWORD', 'Admin123!@#')
    
    # Check if admin already exists
    existing_admin = User.query.filter_by(email=admin_email).first()
    
    if existing_admin:
        logger.info(f"👤 Admin user already exists: {admin_email}")
        return existing_admin
    
    logger.info("👤 Creating default admin user...")
    
    # Create admin user
    admin_user = User(
        email=admin_email,
        username='admin',
        first_name='مدير',
        last_name='النظام',
        role='admin',
        is_active=True,
        is_verified=True,
        phone='+966501234567'
    )
    admin_user.password = admin_password
    
    db.session.add(admin_user)
    db.session.flush()  # Get the ID
    
    # Create corresponding employee record
    admin_employee = Employee(
        user_id=admin_user.id,
        employee_id='EMP001',
        department='الإدارة',
        position='مدير عام',
        hire_date=datetime.utcnow().date(),
        salary=10000.00,
        is_active=True
    )
    
    db.session.add(admin_employee)
    
    logger.info(f"✅ Default admin user created: {admin_email}")
    logger.info(f"🔑 Default password: {admin_password}")
    logger.warning("⚠️ Please change the default password after first login!")
    
    return admin_user

def create_sample_data():
    """Create sample data for testing and demonstration"""
    
    logger.info("📝 Creating sample data...")
    
    # Create sample employees
    sample_employees = [
        {
            'email': 'manager@company.com',
            'username': 'manager',
            'first_name': 'محمد',
            'last_name': 'المدير',
            'role': 'manager',
            'department': 'إدارة المشاريع',
            'position': 'مدير مشاريع',
            'employee_id': 'EMP002'
        },
        {
            'email': 'employee@company.com', 
            'username': 'employee',
            'first_name': 'فاطمة',
            'last_name': 'الموظفة',
            'role': 'employee',
            'department': 'التطوير',
            'position': 'مطور برمجيات',
            'employee_id': 'EMP003'
        }
    ]
    
    for emp_data in sample_employees:
        # Check if user already exists
        if User.query.filter_by(email=emp_data['email']).first():
            continue
            
        # Create user
        user = User(
            email=emp_data['email'],
            username=emp_data['username'],
            first_name=emp_data['first_name'],
            last_name=emp_data['last_name'],
            role=emp_data['role'],
            is_active=True,
            is_verified=True
        )
        user.password = 'Password123!'
        
        db.session.add(user)
        db.session.flush()
        
        # Create employee record
        employee = Employee(
            user_id=user.id,
            employee_id=emp_data['employee_id'],
            department=emp_data['department'],
            position=emp_data['position'],
            hire_date=datetime.utcnow().date(),
            salary=5000.00,
            is_active=True
        )
        
        db.session.add(employee)
    
    # Create sample clients
    sample_clients = [
        {
            'name': 'شركة التقنية المتقدمة',
            'email': 'info@advanced-tech.com',
            'phone': '+966501111111',
            'client_type': 'company',
            'contact_person': 'محمد محمد'
        },
        {
            'name': 'سارة محمد',
            'email': 'sara@gmail.com',
            'phone': '+966502222222', 
            'client_type': 'individual',
            'contact_person': 'سارة محمد'
        }
    ]
    
    for client_data in sample_clients:
        # Check if client already exists
        if Client.query.filter_by(email=client_data['email']).first():
            continue
            
        client = Client(
            name=client_data['name'],
            email=client_data['email'],
            phone=client_data['phone'],
            client_type=client_data['client_type'],
            contact_person=client_data['contact_person'],
            status='active'
        )
        
        db.session.add(client)
    
    # Create sample project
    admin_user = User.query.filter_by(role='admin').first()
    sample_client = Client.query.first()
    
    if admin_user and sample_client and not Project.query.first():
        project = Project(
            name='مشروع تطوير موقع إلكتروني',
            description='تطوير موقع إلكتروني متكامل للشركة مع لوحة إدارة',
            client_id=sample_client.id,
            created_by=admin_user.id,
            start_date=datetime.utcnow().date(),
            budget=50000.00,
            status='active'
        )
        
        db.session.add(project)
    
    logger.info("✅ Sample data created successfully")

def check_database_connection():
    """Check database connection"""
    
    app = create_app()
    
    with app.app_context():
        try:
            # Try to execute a simple query
            db.session.execute('SELECT 1')
            logger.info("✅ Database connection successful")
            return True
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False

def main():
    """Main function"""
    
    logger.info("🔍 Checking database connection...")
    
    if not check_database_connection():
        logger.error("❌ Cannot connect to database. Please check your configuration.")
        sys.exit(1)
    
    try:
        init_database()
        logger.info("🎉 Database initialization completed successfully!")
        
        # Print summary
        app = create_app()
        with app.app_context():
            user_count = User.query.count()
            employee_count = Employee.query.count()
            client_count = Client.query.count()
            project_count = Project.query.count()
            
            logger.info("📊 Database Summary:")
            logger.info(f"   👥 Users: {user_count}")
            logger.info(f"   👔 Employees: {employee_count}")
            logger.info(f"   🏢 Clients: {client_count}")
            logger.info(f"   📋 Projects: {project_count}")
        
    except Exception as e:
        logger.error(f"❌ Initialization failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 