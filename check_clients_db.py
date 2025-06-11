#!/usr/bin/env python3
from extensions import db
from models.client import Client
from app import create_app

app = create_app()
with app.app_context():
    clients = Client.query.all()
    print(f'إجمالي العملاء: {len(clients)}')
    print('\nقائمة العملاء:')
    for c in clients:
        print(f'ID: {c.id}, النوع: {c.client_type}, الاسم: {c.display_name}, الإيميل: {c.email}, الحالة: {c.status}')
    
    # Check for duplicate emails
    emails = [c.email for c in clients]
    duplicates = set([x for x in emails if emails.count(x) > 1])
    if duplicates:
        print(f'\nإيميلات مكررة: {duplicates}')
    else:
        print('\nلا توجد إيميلات مكررة')
    
    # Check active clients specifically
    active_clients = Client.query.filter_by(status='active').all()
    print(f'\nالعملاء النشطين: {len(active_clients)}')
    
    active_emails = [c.email for c in active_clients]
    active_duplicates = set([x for x in active_emails if active_emails.count(x) > 1])
    if active_duplicates:
        print(f'إيميلات مكررة في العملاء النشطين: {active_duplicates}')
    else:
        print('لا توجد إيميلات مكررة في العملاء النشطين') 