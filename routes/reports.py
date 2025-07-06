from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from extensions import db
from models.subscription import ClientSubscription, SubscriptionPayment
from models.project import Project
from models.client import Client
from models.invoice import Invoice
from models.expense import Expense
import io
import xlsxwriter

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/financial-summary', methods=['GET'])
@jwt_required()
def get_financial_summary():
    """Get comprehensive financial summary"""
    try:
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Default to current month if no dates provided
        if not start_date or not end_date:
            today = datetime.now()
            start_date = today.replace(day=1).date()
            end_date = today.date()
        else:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Get all financial data
        summary = calculate_financial_summary(start_date, end_date)
        
        return jsonify({
            'success': True,
            'summary': summary,
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }
        }), 200
        
    except Exception as e:
        print(f"❌ Error getting financial summary: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب الملخص المالي'
        }), 500

@reports_bp.route('/transactions', methods=['GET'])
@jwt_required()
def get_all_transactions():
    """Get all financial transactions"""
    try:
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        transaction_type = request.args.get('type')  # income, expense, expected
        
        transactions = get_financial_transactions(start_date, end_date, transaction_type)
        
        return jsonify({
            'success': True,
            'transactions': transactions,
            'total': len(transactions)
        }), 200
        
    except Exception as e:
        print(f"❌ Error getting transactions: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب المعاملات'
        }), 500

@reports_bp.route('/export/excel', methods=['POST'])
@jwt_required()
def export_excel():
    """Export report to Excel"""
    try:
        data = request.get_json()
        export_type = data.get('export_type', 'financial')
        
        if export_type == 'clients':
            # Export clients data
            filters = data.get('filters', {})
            clients = get_clients_for_export(filters)
            excel_buffer = create_clients_excel_report(clients)
            filename = f"clients_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
        else:
            # Export financial data
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            transaction_type = data.get('type')
            
            # Get transactions
            transactions = get_financial_transactions(start_date, end_date, transaction_type)
            
            # Create Excel file
            excel_buffer = create_excel_report(transactions, start_date, end_date)
            filename = f"financial_report_{start_date}_{end_date}.xlsx"
        
        return send_file(
            excel_buffer,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"❌ Error exporting Excel: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في تصدير التقرير'
        }), 500

@reports_bp.route('/monthly-comparison', methods=['GET'])
@jwt_required()
def get_monthly_comparison():
    """Get monthly financial comparison for charts"""
    try:
        months_count = request.args.get('months', 6, type=int)
        
        comparison_data = []
        today = datetime.now()
        
        for i in range(months_count - 1, -1, -1):
            # Calculate month start and end
            month_date = today.replace(day=1) - timedelta(days=i * 30)
            month_start = month_date.replace(day=1)
            
            # Calculate next month start
            if month_start.month == 12:
                next_month = month_start.replace(year=month_start.year + 1, month=1)
            else:
                next_month = month_start.replace(month=month_start.month + 1)
            
            month_end = next_month - timedelta(days=1)
            
            # Get month summary
            month_summary = calculate_financial_summary(month_start.date(), month_end.date())
            
            comparison_data.append({
                'month': month_start.strftime('%Y-%m'),
                'month_name': month_start.strftime('%B %Y'),
                'month_name_ar': get_arabic_month_name(month_start),
                'revenue': month_summary['total_revenue'],
                'expenses': month_summary['total_expenses'],
                'profit': month_summary['net_profit'],
                'expected_revenue': month_summary['expected_revenue']
            })
        
        return jsonify({
            'success': True,
            'comparison': comparison_data
        }), 200
        
    except Exception as e:
        print(f"❌ Error getting monthly comparison: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب المقارنة الشهرية'
        }), 500

def calculate_financial_summary(start_date, end_date):
    """Calculate comprehensive financial summary for given period"""
    
    # Initialize summary
    summary = {
        'total_revenue': 0,
        'total_expenses': 0,
        'expected_revenue': 0,
        'net_profit': 0,
        'subscription_revenue': 0,
        'project_revenue': 0,
        'active_subscriptions': 0,
        'completed_projects': 0,
        'pending_payments': 0
    }
    
    # Get subscription revenue
    subscription_payments = SubscriptionPayment.query.filter(
        SubscriptionPayment.payment_date >= start_date,
        SubscriptionPayment.payment_date <= end_date,
        SubscriptionPayment.status == 'completed'
    ).all()
    
    subscription_revenue = sum(payment.amount for payment in subscription_payments)
    summary['subscription_revenue'] = subscription_revenue
    summary['total_revenue'] += subscription_revenue
    
    # Get project revenue (completed projects)
    completed_projects = Project.query.filter(
        Project.created_at >= datetime.combine(start_date, datetime.min.time()),
        Project.created_at <= datetime.combine(end_date, datetime.max.time()),
        Project.status == 'completed'
    ).all()
    
    project_revenue = sum(project.budget or 0 for project in completed_projects)
    summary['project_revenue'] = project_revenue
    summary['total_revenue'] += project_revenue
    summary['completed_projects'] = len(completed_projects)
    
    # Get expected revenue (active projects not yet completed)
    active_projects = Project.query.filter(
        Project.status.in_(['active', 'on_hold']),
        Project.budget.isnot(None)
    ).all()
    
    expected_revenue = sum(project.budget for project in active_projects)
    summary['expected_revenue'] = expected_revenue
    
    # Get expenses
    expenses = Expense.query.filter(
        Expense.expense_date >= start_date,
        Expense.expense_date <= end_date,
        Expense.status == 'approved'
    ).all()
    
    total_expenses = sum(expense.amount for expense in expenses)
    summary['total_expenses'] = total_expenses
    
    # Calculate net profit
    summary['net_profit'] = summary['total_revenue'] - summary['total_expenses']
    
    # Get active subscriptions count
    summary['active_subscriptions'] = ClientSubscription.query.filter_by(status='active').count()
    
    # Get pending payments
    pending_payments = SubscriptionPayment.query.filter_by(status='pending').all()
    summary['pending_payments'] = sum(payment.amount for payment in pending_payments)
    
    return summary

def get_financial_transactions(start_date=None, end_date=None, transaction_type=None):
    """Get all financial transactions for the specified period"""
    
    transactions = []
    
    # Parse dates if provided
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Get subscription payments (income)
    if not transaction_type or transaction_type == 'income':
        subscription_query = SubscriptionPayment.query.join(ClientSubscription).join(Client).join(Project)
        
        if start_date and end_date:
            subscription_query = subscription_query.filter(
                SubscriptionPayment.payment_date >= start_date,
                SubscriptionPayment.payment_date <= end_date
            )
        
        subscription_payments = subscription_query.all()
        
        for payment in subscription_payments:
            transactions.append({
                'id': f'sub_pay_{payment.id}',
                'date': payment.payment_date.isoformat(),
                'type': 'income',
                'description': f'دفعة اشتراك - {payment.subscription.subscription_plan}',
                'client': payment.subscription.client.display_name,
                'project': payment.subscription.project.name,
                'amount': float(payment.amount),
                'status': 'paid' if payment.status == 'completed' else 'pending',
                'source': 'subscription'
            })
    
    # Get project revenue (income)
    if not transaction_type or transaction_type == 'income':
        project_query = Project.query.join(Client, Project.client_id == Client.id, isouter=True)
        
        if start_date and end_date:
            project_query = project_query.filter(
                Project.created_at >= datetime.combine(start_date, datetime.min.time()),
                Project.created_at <= datetime.combine(end_date, datetime.max.time())
            )
        
        projects = project_query.all()
        
        for project in projects:
            if project.budget and project.budget > 0:
                transactions.append({
                    'id': f'project_{project.id}',
                    'date': project.created_at.date().isoformat(),
                    'type': 'income',
                    'description': f'مشروع: {project.name}',
                    'client': project.client.display_name if project.client else 'غير محدد',
                    'project': project.name,
                    'amount': float(project.budget),
                    'status': 'paid' if project.status == 'completed' else 'expected',
                    'source': 'project'
                })
    
    # Get expenses
    if not transaction_type or transaction_type == 'expense':
        expense_query = Expense.query
        
        if start_date and end_date:
            expense_query = expense_query.filter(
                Expense.expense_date >= start_date,
                Expense.expense_date <= end_date
            )
        
        expenses = expense_query.all()
        
        for expense in expenses:
            transactions.append({
                'id': f'expense_{expense.id}',
                'date': expense.expense_date.isoformat(),
                'type': 'expense',
                'description': expense.description,
                'client': 'مصروف',
                'project': expense.category or 'عام',
                'amount': float(expense.amount),
                'status': 'paid' if expense.status == 'approved' else 'pending',
                'source': 'expense'
            })
    
    # Sort by date (newest first)
    transactions.sort(key=lambda x: x['date'], reverse=True)
    
    return transactions

def create_excel_report(transactions, start_date, end_date):
    """Create Excel report with financial data"""
    
    # Create BytesIO buffer
    excel_buffer = io.BytesIO()
    
    # Create workbook in memory
    wb = xlsxwriter.Workbook(excel_buffer, {'in_memory': True})
    ws = wb.add_worksheet("التقرير المالي")
    
    # Set up formats
    header_format = wb.add_format({
        'bold': True,
        'font_color': 'white',
        'bg_color': '#366092',
        'align': 'center',
        'valign': 'vcenter'
    })
    
    # Add header
    headers = ['التاريخ', 'النوع', 'الوصف', 'العميل', 'المشروع', 'المبلغ (ج.م)', 'الحالة']
    
    for col, header in enumerate(headers):
        ws.write(0, col, header, header_format)
    
    # Add data
    for row, transaction in enumerate(transactions, 1):
        ws.write(row, 0, transaction['date'])
        ws.write(row, 1, 'إيراد' if transaction['type'] == 'income' else 'مصروف')
        ws.write(row, 2, transaction['description'])
        ws.write(row, 3, transaction['client'])
        ws.write(row, 4, transaction['project'])
        ws.write(row, 5, transaction['amount'])
        ws.write(row, 6, transaction['status'])
    
    # Auto-adjust column widths
    for col in range(len(headers)):
        max_length = len(headers[col])
        for row, transaction in enumerate(transactions):
            if col == 0:
                cell_length = len(str(transaction['date']))
            elif col == 1:
                cell_length = len('إيراد' if transaction['type'] == 'income' else 'مصروف')
            elif col == 2:
                cell_length = len(str(transaction['description']))
            elif col == 3:
                cell_length = len(str(transaction['client']))
            elif col == 4:
                cell_length = len(str(transaction['project']))
            elif col == 5:
                cell_length = len(str(transaction['amount']))
            elif col == 6:
                cell_length = len(str(transaction['status']))
            
            if cell_length > max_length:
                max_length = cell_length
        
        ws.set_column(col, col, max_length + 2)
    
    # Close workbook to save data
    wb.close()
    
    # Seek to beginning of buffer
    excel_buffer.seek(0)
    
    return excel_buffer

def get_arabic_month_name(date):
    """Get Arabic month name"""
    arabic_months = {
        1: 'يناير', 2: 'فبراير', 3: 'مارس', 4: 'أبريل',
        5: 'مايو', 6: 'يونيو', 7: 'يوليو', 8: 'أغسطس',
        9: 'سبتمبر', 10: 'أكتوبر', 11: 'نوفمبر', 12: 'ديسمبر'
    }
    return f"{arabic_months[date.month]} {date.year}" 

def get_clients_for_export(filters):
    """Get clients data for export"""
    from models.client import Client
    
    query = Client.query
    
    # Apply filters
    if filters.get('status'):
        query = query.filter_by(status=filters['status'])
    
    if filters.get('type'):
        query = query.filter_by(client_type=filters['type'])
    
    return query.order_by(Client.created_at.desc()).all()

def create_clients_excel_report(clients):
    """Create Excel report with clients data"""
    
    # Create BytesIO buffer
    excel_buffer = io.BytesIO()
    
    # Create workbook in memory
    wb = xlsxwriter.Workbook(excel_buffer, {'in_memory': True})
    ws = wb.add_worksheet("العملاء")
    
    # Set up formats
    header_format = wb.add_format({
        'bold': True,
        'font_color': 'white',
        'bg_color': '#366092',
        'align': 'center',
        'valign': 'vcenter'
    })
    
    # Add header
    headers = [
        'الرقم', 'اسم العميل', 'النوع', 'البريد الإلكتروني', 'الهاتف',
        'المدينة', 'البلد', 'الحالة', 'القطاع', 'الأولوية', 'المصدر',
        'تاريخ الإضافة', 'آخر تحديث'
    ]
    
    for col, header in enumerate(headers):
        ws.write(0, col, header, header_format)
    
    # Add data
    for row, client in enumerate(clients, 1):
        ws.write(row, 0, client.id)
        ws.write(row, 1, client.display_name or 'غير محدد')
        ws.write(row, 2, 'فرد' if client.client_type == 'individual' else 'شركة')
        ws.write(row, 3, client.email or 'غير محدد')
        ws.write(row, 4, client.phone or 'غير محدد')
        ws.write(row, 5, client.city or 'غير محدد')
        ws.write(row, 6, client.country or 'غير محدد')
        ws.write(row, 7, get_status_text_arabic(client.status))
        ws.write(row, 8, client.industry or 'غير محدد')
        ws.write(row, 9, get_priority_text_arabic(client.priority))
        ws.write(row, 10, client.source or 'غير محدد')
        ws.write(row, 11, client.created_at.strftime('%Y-%m-%d') if client.created_at else 'غير محدد')
        ws.write(row, 12, client.updated_at.strftime('%Y-%m-%d') if client.updated_at else 'غير محدد')
    
    # Auto-adjust column widths
    for col in range(len(headers)):
        max_length = len(headers[col])
        for row, client in enumerate(clients):
            if col == 0:
                cell_length = len(str(client.id))
            elif col == 1:
                cell_length = len(client.display_name or 'غير محدد')
            elif col == 2:
                cell_length = len('فرد' if client.client_type == 'individual' else 'شركة')
            elif col == 3:
                cell_length = len(client.email or 'غير محدد')
            elif col == 4:
                cell_length = len(client.phone or 'غير محدد')
            elif col == 5:
                cell_length = len(client.city or 'غير محدد')
            elif col == 6:
                cell_length = len(client.country or 'غير محدد')
            elif col == 7:
                cell_length = len(get_status_text_arabic(client.status))
            elif col == 8:
                cell_length = len(client.industry or 'غير محدد')
            elif col == 9:
                cell_length = len(get_priority_text_arabic(client.priority))
            elif col == 10:
                cell_length = len(client.source or 'غير محدد')
            elif col == 11:
                cell_length = len(client.created_at.strftime('%Y-%m-%d') if client.created_at else 'غير محدد')
            elif col == 12:
                cell_length = len(client.updated_at.strftime('%Y-%m-%d') if client.updated_at else 'غير محدد')
            
            if cell_length > max_length:
                max_length = cell_length
        
        ws.set_column(col, col, max_length + 2)
    
    # Close workbook to save data
    wb.close()
    
    # Seek to beginning of buffer
    excel_buffer.seek(0)
    
    return excel_buffer

def get_status_text_arabic(status):
    """Get Arabic status text"""
    statuses = {
        'active': 'نشط',
        'inactive': 'غير نشط',
        'potential': 'محتمل',
        'targeted': 'سيتم استهدافه'
    }
    return statuses.get(status, 'غير محدد')

def get_priority_text_arabic(priority):
    """Get Arabic priority text"""
    priorities = {
        'low': 'منخفضة',
        'medium': 'متوسطة',
        'high': 'عالية'
    }
    return priorities.get(priority, 'غير محدد')