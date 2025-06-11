from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date, timedelta
from sqlalchemy import func, extract, and_
from extensions import db
from models import Project, Client, ClientSubscription, SubscriptionPayment
import traceback

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard/stats', methods=['GET'])
def get_dashboard_statistics():
    """جلب إحصائيات لوحة التحكم الشاملة"""
    try:
        # إحصائيات المشاريع
        total_projects = Project.query.count()
        subscription_projects = Project.query.filter_by(project_type='subscription').count()
        onetime_projects = Project.query.filter_by(project_type='onetime').count()
        active_projects = Project.query.filter_by(status='active').count()
        completed_projects = Project.query.filter_by(status='completed').count()
        
        # إحصائيات العملاء
        total_clients = Client.query.count()
        active_subscriptions = ClientSubscription.query.filter_by(status='active').count()
        
        # حساب العملاء النشطين (لديهم اشتراكات فعالة)
        active_clients = db.session.query(Client).join(
            ClientSubscription, Client.id == ClientSubscription.client_id
        ).filter(ClientSubscription.status == 'active').distinct().count()
        
        # الإيرادات الشهرية من الاشتراكات
        monthly_revenue = db.session.query(
            func.sum(ClientSubscription.monthly_amount)
        ).filter(ClientSubscription.status == 'active').scalar() or 0
        
        # إجمالي إيرادات الاشتراكات
        subscription_revenue = db.session.query(
            func.sum(SubscriptionPayment.amount)
        ).filter(SubscriptionPayment.status == 'paid').scalar() or 0
        
        statistics = {
            'total_projects': total_projects,
            'subscription_projects': subscription_projects,
            'onetime_projects': onetime_projects,
            'active_projects': active_projects,
            'completed_projects': completed_projects,
            'total_clients': total_clients,
            'active_clients': active_clients,
            'active_subscriptions': active_subscriptions,
            'monthly_revenue': float(monthly_revenue),
            'subscription_revenue': float(subscription_revenue),
            'project_revenue': 0,
            'pending_amount': 0,
            'total_revenue': float(subscription_revenue)
        }

        return jsonify({
            'success': True,
            'statistics': statistics
        })

    except Exception as e:
        current_app.logger.error(f"خطأ في جلب إحصائيات لوحة التحكم: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'خطأ في جلب الإحصائيات'
        }), 500

@dashboard_bp.route('/dashboard/recent-activities', methods=['GET'])
def get_recent_activities():
    """جلب النشاطات الحديثة"""
    try:
        activities = []
        
        # المشاريع الحديثة (آخر 10)
        recent_projects = Project.query.order_by(Project.created_at.desc()).limit(10).all()
        for project in recent_projects:
            activities.append({
                'type': 'project_created',
                'title': f'تم إنشاء مشروع جديد: {project.name}',
                'description': f'مشروع {project.project_type} في فئة {project.category}',
                'timestamp': project.created_at.isoformat(),
                'icon': 'fas fa-project-diagram',
                'color': 'primary'
            })
        
        # الاشتراكات الحديثة (آخر 10)
        recent_subscriptions = ClientSubscription.query.order_by(
            ClientSubscription.created_at.desc()
        ).limit(10).all()
        for subscription in recent_subscriptions:
            activities.append({
                'type': 'subscription_created',
                'title': f'اشتراك جديد: {subscription.client.name}',
                'description': f'اشتراك في {subscription.project.name} بقيمة {float(subscription.monthly_amount)} ر.س شهرياً',
                'timestamp': subscription.created_at.isoformat(),
                'icon': 'fas fa-sync-alt',
                'color': 'success'
            })
        
        # الدفعات الحديثة (آخر 10)
        recent_payments = SubscriptionPayment.query.filter_by(status='paid').order_by(
            SubscriptionPayment.payment_date.desc()
        ).limit(10).all()
        for payment in recent_payments:
            activities.append({
                'type': 'payment_received',
                'title': f'تم استلام دفعة من {payment.subscription.client.name}',
                'description': f'مبلغ {float(payment.amount)} ر.س لاشتراك {payment.subscription.project.name}',
                'timestamp': payment.payment_date.isoformat() if payment.payment_date else payment.created_at.isoformat(),
                'icon': 'fas fa-money-bill',
                'color': 'info'
            })
        
        # ترتيب النشاطات حسب التاريخ
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return jsonify({
            'success': True,
            'activities': activities[:20]  # أحدث 20 نشاط
        })

    except Exception as e:
        current_app.logger.error(f"خطأ في جلب النشاطات الحديثة: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': 'خطأ في جلب النشاطات'
        }), 500

@dashboard_bp.route('/dashboard/notifications', methods=['GET'])
def get_notifications():
    """جلب التنبيهات والإشعارات"""
    try:
        notifications = []
        
        # الاشتراكات المتأخرة
        overdue_subscriptions = ClientSubscription.query.filter(
            and_(
                ClientSubscription.status == 'active',
                ClientSubscription.next_billing_date < datetime.now().date()
            )
        ).all()
        
        if overdue_subscriptions:
            notifications.append({
                'type': 'warning',
                'title': 'اشتراكات متأخرة',
                'message': f'يوجد {len(overdue_subscriptions)} اشتراك متأخر عن الدفع',
                'action_url': '/subscriptions?filter=overdue',
                'priority': 'high',
                'timestamp': datetime.now().isoformat()
            })
        
        # المشاريع القريبة من الانتهاء
        upcoming_deadlines = Project.query.filter(
            and_(
                Project.status == 'active',
                Project.end_date != None,
                Project.end_date <= datetime.now().date() + timedelta(days=7)
            )
        ).all()
        
        if upcoming_deadlines:
            notifications.append({
                'type': 'info',
                'title': 'مشاريع قريبة من الانتهاء',
                'message': f'{len(upcoming_deadlines)} مشروع ينتهي خلال الأسبوع القادم',
                'action_url': '/projects?filter=upcoming',
                'priority': 'medium',
                'timestamp': datetime.now().isoformat()
            })
        
        # العملاء الجدد (آخر 7 أيام)
        new_clients = Client.query.filter(
            Client.created_at >= datetime.now() - timedelta(days=7)
        ).count()
        
        if new_clients > 0:
            notifications.append({
                'type': 'success',
                'title': 'عملاء جدد',
                'message': f'تم إضافة {new_clients} عميل جديد هذا الأسبوع',
                'action_url': '/clients',
                'priority': 'low',
                'timestamp': datetime.now().isoformat()
            })
        
        # إشعار عام للنظام
        notifications.append({
            'type': 'info',
            'title': 'نظام إدارة المشاريع',
            'message': 'مرحباً بك في النظام الشامل لإدارة المشاريع والاشتراكات',
            'action_url': None,
            'priority': 'low',
            'timestamp': datetime.now().isoformat()
        })

        return jsonify({
            'success': True,
            'notifications': notifications
        })

    except Exception as e:
        current_app.logger.error(f"خطأ في جلب التنبيهات: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': 'خطأ في جلب التنبيهات'
        }), 500

@dashboard_bp.route('/dashboard/chart-data', methods=['GET'])
def get_chart_data():
    """جلب بيانات الرسوم البيانية"""
    try:
        # بيانات الإيرادات الشهرية
        monthly_revenue_data = []
        for i in range(12):
            month = (datetime.now().month - i) % 12 or 12
            year = datetime.now().year - (1 if datetime.now().month - i <= 0 else 0)
            
            month_revenue = db.session.query(
                func.sum(SubscriptionPayment.amount)
            ).filter(
                and_(
                    SubscriptionPayment.status == 'paid',
                    extract('month', SubscriptionPayment.payment_date) == month,
                    extract('year', SubscriptionPayment.payment_date) == year
                )
            ).scalar() or 0
            
            monthly_revenue_data.insert(0, {
                'month': f'{year}-{month:02d}',
                'amount': float(month_revenue)
            })
        
        # بيانات الاشتراكات حسب الحالة
        subscription_status_data = [
            {
                'status': 'نشط',
                'count': ClientSubscription.query.filter_by(status='active').count()
            },
            {
                'status': 'متوقف',
                'count': ClientSubscription.query.filter_by(status='paused').count()
            },
            {
                'status': 'ملغي',
                'count': ClientSubscription.query.filter_by(status='cancelled').count()
            }
        ]
        
        # بيانات المشاريع حسب النوع
        project_type_data = [
            {
                'type': 'اشتراكات',
                'count': Project.query.filter_by(project_type='subscription').count()
            },
            {
                'type': 'مرة واحدة',
                'count': Project.query.filter_by(project_type='onetime').count()
            }
        ]

        return jsonify({
            'success': True,
            'chart_data': {
                'monthly_revenue': monthly_revenue_data[-6:],  # آخر 6 أشهر
                'subscription_status': subscription_status_data,
                'project_types': project_type_data
            }
        })

    except Exception as e:
        current_app.logger.error(f"خطأ في جلب بيانات الرسوم البيانية: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'خطأ في جلب البيانات'
        }), 500 