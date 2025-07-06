#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

# Add parent directory to path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from models.user import User

def create_default_admin():
    """Create default admin user if it doesn't exist"""
    app = create_app()
    
    with app.app_context():
        # Check if admin exists
        admin = User.query.filter_by(email='admin@erpsystem.com').first()
        
        if not admin:
            print('Creating default admin user...')
            admin = User(
                email='admin@erpsystem.com',
                username='admin',
                password='admin123',
                first_name='System',
                last_name='Admin',
                role='admin',
                is_active=True,
                is_verified=True
            )
            
            db.session.add(admin)
            db.session.commit()
            print('Default admin user created successfully!')
        else:
            print('Admin user already exists.')

if __name__ == '__main__':
    create_default_admin() 