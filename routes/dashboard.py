from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date, timedelta
from sqlalchemy import func, extract
from extensions import db
from models.project import Project
from models.user import User
from models.employee import Employee
from models.client import Client
from models.task import Task
from models.timetrack import TimeTrack
from models.expense import Expense
from models.invoice import Invoice

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        # Projects stats
        total_projects = Project.query.count()
        active_projects = Project.query.filter(Project.status.in_(['planning', 'active'])).count()
        completed_projects = Project.query.filter_by(status='completed').count()
        
        # Tasks stats  
        total_tasks = Task.query.count()
        pending_tasks = Task.query.filter(Task.status.in_(['todo', 'in_progress'])).count()
        completed_tasks = Task.query.filter_by(status='completed').count()
        
        # Employees and Clients
        total_employees = Employee.query.filter_by(status='active').count()
        total_clients = Client.query.filter_by(status='active').count()
        
        return jsonify({
            'success': True,
            'stats': {
                'projects': {
                    'total': total_projects,
                    'active': active_projects,
                    'completed': completed_projects
                },
                'tasks': {
                    'total': total_tasks,
                    'pending': pending_tasks,
                    'completed': completed_tasks
                },
                'resources': {
                    'employees': total_employees,
                    'clients': total_clients
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب الإحصائيات'
        }), 500

@dashboard_bp.route('/recent-activities', methods=['GET'])
@jwt_required()
def get_recent_activities():
    """Get recent activities"""
    try:
        limit = request.args.get('limit', 5, type=int)
        
        # Recent projects
        recent_projects = Project.query.order_by(Project.created_at.desc()).limit(limit).all()
        
        # Recent tasks
        recent_tasks = Task.query.order_by(Task.created_at.desc()).limit(limit).all()
        
        return jsonify({
            'success': True,
            'activities': {
                'recent_projects': [project.to_dict() for project in recent_projects],
                'recent_tasks': [task.to_dict() for task in recent_tasks]
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب الأنشطة الحديثة'
        }), 500

@dashboard_bp.route('/charts/revenue', methods=['GET'])
@jwt_required()
def get_revenue_chart():
    """Get revenue chart data"""
    try:
        period = request.args.get('period', 'monthly')  # daily, weekly, monthly, yearly
        
        if period == 'monthly':
            # Get revenue for last 12 months
            chart_data = []
            for i in range(12):
                month_start = (date.today().replace(day=1) - timedelta(days=30 * i))
                month_end = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
                
                revenue = db.session.query(func.sum(Invoice.total_amount)).filter(
                    Invoice.status == 'paid',
                    Invoice.paid_date >= month_start,
                    Invoice.paid_date <= month_end
                ).scalar() or 0
                
                expenses = db.session.query(func.sum(Expense.total_amount)).filter(
                    Expense.status == 'approved',
                    Expense.expense_date >= month_start,
                    Expense.expense_date <= month_end
                ).scalar() or 0
                
                chart_data.append({
                    'period': month_start.strftime('%Y-%m'),
                    'revenue': float(revenue),
                    'expenses': float(expenses),
                    'profit': float(revenue - expenses)
                })
            
            chart_data.reverse()
        
        return jsonify({
            'success': True,
            'chart_data': chart_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب بيانات الإيرادات'
        }), 500

@dashboard_bp.route('/charts/projects-status', methods=['GET'])
@jwt_required()
def get_projects_status_chart():
    """Get projects status distribution chart"""
    try:
        status_counts = db.session.query(
            Project.status,
            func.count(Project.id)
        ).group_by(Project.status).all()
        
        chart_data = [
            {
                'status': status,
                'count': count,
                'label': {
                    'planning': 'التخطيط',
                    'active': 'نشط',
                    'on_hold': 'معلق',
                    'completed': 'مكتمل',
                    'cancelled': 'ملغي'
                }.get(status, status)
            }
            for status, count in status_counts
        ]
        
        return jsonify({
            'success': True,
            'chart_data': chart_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب بيانات حالة المشاريع'
        }), 500

@dashboard_bp.route('/charts/team-performance', methods=['GET'])
@jwt_required()
def get_team_performance_chart():
    """Get team performance chart"""
    try:
        # Get employees with their project and task counts
        performance_data = db.session.query(
            Employee.id,
            Employee.first_name,
            Employee.last_name,
            func.count(Project.id).label('project_count'),
            func.count(Task.id).label('task_count')
        ).outerjoin(Project, Employee.id == Project.project_manager_id)\
         .outerjoin(Task, Employee.user_id == Task.assigned_to)\
         .filter(Employee.status == 'active')\
         .group_by(Employee.id, Employee.first_name, Employee.last_name)\
         .limit(10).all()
        
        chart_data = [
            {
                'employee': f"{data.first_name} {data.last_name}",
                'projects': data.project_count,
                'tasks': data.task_count,
                'total_hours': TimeTrack.query.filter_by(employee_id=data.id).with_entities(
                    func.sum(TimeTrack.hours)
                ).scalar() or 0
            }
            for data in performance_data
        ]
        
        return jsonify({
            'success': True,
            'chart_data': chart_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب بيانات أداء الفريق'
        }), 500

@dashboard_bp.route('/notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    """Get user notifications"""
    try:
        user_id = get_jwt_identity()
        
        notifications = []
        
        # Overdue tasks assigned to user
        overdue_tasks = Task.query.filter(
            Task.assigned_to == user_id,
            Task.due_date < date.today(),
            Task.status.in_(['todo', 'in_progress'])
        ).all()
        
        for task in overdue_tasks:
            notifications.append({
                'type': 'overdue_task',
                'title': 'مهمة متأخرة',
                'message': f'المهمة "{task.title}" متأخرة عن موعدها',
                'link': f'/tasks/{task.id}',
                'priority': 'high',
                'date': task.due_date.isoformat()
            })
        
        # Project deadlines approaching (within 7 days)
        upcoming_deadlines = Project.query.filter(
            Project.end_date <= date.today() + timedelta(days=7),
            Project.end_date >= date.today(),
            Project.status.in_(['planning', 'active'])
        ).all()
        
        for project in upcoming_deadlines:
            notifications.append({
                'type': 'project_deadline',
                'title': 'موعد تسليم قريب',
                'message': f'موعد تسليم مشروع "{project.name}" خلال أسبوع',
                'link': f'/projects/{project.id}',
                'priority': 'medium',
                'date': project.end_date.isoformat()
            })
        
        # Pending expenses for approval
        user = User.query.get(user_id)
        if user.role in ['admin', 'manager']:
            pending_expenses = Expense.query.filter_by(status='pending').count()
            if pending_expenses > 0:
                notifications.append({
                    'type': 'pending_approval',
                    'title': 'مصروفات تحتاج موافقة',
                    'message': f'{pending_expenses} مصروف ينتظر الموافقة',
                    'link': '/expenses?status=pending',
                    'priority': 'medium',
                    'date': date.today().isoformat()
                })
        
        # Sort by priority and date
        priority_order = {'high': 3, 'medium': 2, 'low': 1}
        notifications.sort(key=lambda x: (priority_order.get(x['priority'], 0), x['date']), reverse=True)
        
        return jsonify({
            'success': True,
            'notifications': notifications[:20]  # Limit to 20 notifications
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب الإشعارات'
        }), 500 