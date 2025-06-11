from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date
from extensions import db
from models.project import Project
from models.user import User
from models.client import Client
from models.employee import Employee
from sqlalchemy import func

projects_bp = Blueprint('projects', __name__)

@projects_bp.route('/', methods=['GET'])
@jwt_required()
def get_projects():
    """Get all projects with pagination and filtering - Enhanced for subscription/one-time projects"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        status = request.args.get('status')
        priority = request.args.get('priority')
        client_id = request.args.get('client_id', type=int)
        project_type = request.args.get('project_type')  # NEW: filter by subscription/onetime
        technology = request.args.get('technology')  # NEW: filter by technology
        search = request.args.get('search')
        
        query = Project.query
        
        # Apply filters
        if status:
            query = query.filter(Project.status == status)
        if priority:
            query = query.filter(Project.priority == priority)
        if client_id:
            query = query.filter(Project.client_id == client_id)
        if project_type:
            query = query.filter(Project.project_type == project_type)
        if technology:
            query = query.filter(Project.technologies.contains(technology))
        if search:
            query = query.filter(
                Project.name.contains(search) |
                Project.description.contains(search) |
                Project.project_code.contains(search)
            )
        
        # Order by creation date (newest first)
        query = query.order_by(Project.created_at.desc())
        
        # Get all projects (simplified for testing)
        projects = query.all()
        
        return jsonify([project.to_dict() for project in projects])
        
    except Exception as e:
        print(f"Error fetching projects: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب المشاريع',
            'error': str(e)
        }), 500

@projects_bp.route('/<int:project_id>', methods=['GET'])
@jwt_required()
def get_project(project_id):
    """Get single project by ID"""
    try:
        project = Project.query.get_or_404(project_id)
        
        return jsonify({
            'success': True,
            'project': project.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'المشروع غير موجود'
        }), 404

@projects_bp.route('/', methods=['POST'])
@jwt_required()
def create_project():
    """Create new project - Enhanced for subscription/one-time projects"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        print(f"Creating project with data: {data}")
        
        # Validate required fields
        required_fields = ['name', 'project_type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'الحقل {field} مطلوب'
                }), 400
        
        # Validate project type
        if data['project_type'] not in ['subscription', 'onetime']:
            return jsonify({
                'success': False,
                'message': 'نوع المشروع يجب أن يكون subscription أو onetime'
            }), 400
        
        # Create project
        project = Project(
            name=data['name'],
            description=data.get('description'),
            project_type=data['project_type'],
            status=data.get('status', 'active'),
            priority=data.get('priority', 'medium'),
            category=data.get('category'),
            technologies=data.get('technologies'),
            repository_url=data.get('repository_url'),
            staging_url=data.get('staging_url'),
            production_url=data.get('production_url'),
            created_by=user_id,
            project_manager_id=data.get('project_manager_id')
        )
        
        # Generate project code
        project.generate_project_code()
        
        # Handle subscription projects
        if data['project_type'] == 'subscription':
            project.monthly_price = data.get('monthly_price', 0)
            project.subscriber_count = data.get('subscriber_count', 0)
            
            # Add subscription clients if provided
            if data.get('client_ids'):
                for client_id in data['client_ids']:
                    client = Client.query.get(client_id)
                    if client:
                        project.add_subscription_client(client)
        
        # Handle one-time projects
        elif data['project_type'] == 'onetime':
            project.total_amount = data.get('total_amount', 0)
            project.paid_amount = data.get('paid_amount', 0)
            project.budget = data.get('budget')
            
            # Set single client for one-time projects
            if data.get('client_id'):
                client = Client.query.get(data['client_id'])
                if client:
                    project.client_id = data['client_id']
        
        # Parse dates
        if data.get('start_date'):
            project.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        if data.get('end_date'):
            project.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        
        db.session.add(project)
        db.session.commit()
        
        print(f"Project created successfully: {project.name}")
        
        return jsonify({
            'success': True,
            'message': 'تم إنشاء المشروع بنجاح',
            'project': project.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating project: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في إنشاء المشروع',
            'error': str(e)
        }), 500

@projects_bp.route('/<int:project_id>', methods=['PUT'])
@jwt_required()
def update_project(project_id):
    """Update project - Enhanced for subscription/one-time projects"""
    try:
        project = Project.query.get_or_404(project_id)
        data = request.get_json()
        
        # Update basic fields
        allowed_fields = [
            'name', 'description', 'status', 'priority', 'category',
            'technologies', 'repository_url', 'staging_url', 'production_url',
            'project_manager_id'
        ]
        
        for field in allowed_fields:
            if field in data:
                setattr(project, field, data[field])
        
        # Update subscription fields
        if project.project_type == 'subscription':
            if 'monthly_price' in data:
                project.monthly_price = data['monthly_price']
            if 'subscriber_count' in data:
                project.subscriber_count = data['subscriber_count']
        
        # Update one-time fields
        elif project.project_type == 'onetime':
            if 'total_amount' in data:
                project.total_amount = data['total_amount']
            if 'paid_amount' in data:
                project.paid_amount = data['paid_amount']
            if 'budget' in data:
                project.budget = data['budget']
        
        # Parse dates
        if 'start_date' in data:
            project.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date() if data['start_date'] else None
        if 'end_date' in data:
            project.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date() if data['end_date'] else None
        
        project.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم تحديث المشروع بنجاح',
            'project': project.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في تحديث المشروع'
        }), 500

@projects_bp.route('/<int:project_id>', methods=['DELETE'])
@jwt_required()
def delete_project(project_id):
    """Delete project with proper handling of related records"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # Check permission - only creator or admin can delete
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if project.created_by != user_id and user.role != 'admin':
            return jsonify({
                'success': False,
                'message': 'ليس لديك صلاحية لحذف هذا المشروع'
            }), 403
        
        # Check if project has active subscriptions
        from models.subscription import ClientSubscription
        active_subscriptions = ClientSubscription.query.filter_by(
            project_id=project_id, 
            status='active'
        ).count()
        
        if active_subscriptions > 0:
            return jsonify({
                'success': False,
                'message': f'لا يمكن حذف المشروع. يوجد {active_subscriptions} اشتراك نشط مرتبط بهذا المشروع. يرجى إلغاء الاشتراكات أولاً.'
            }), 400
        
        # Handle related records
        try:
            # Delete subscription payments first
            from models.subscription import SubscriptionPayment
            subscription_ids = [s.id for s in ClientSubscription.query.filter_by(project_id=project_id).all()]
            if subscription_ids:
                SubscriptionPayment.query.filter(SubscriptionPayment.subscription_id.in_(subscription_ids)).delete(synchronize_session=False)
            
            # Delete or update related subscription records
            subscriptions = ClientSubscription.query.filter_by(project_id=project_id).all()
            for subscription in subscriptions:
                if subscription.status in ['cancelled', 'expired', 'paused']:
                    db.session.delete(subscription)
                else:
                    # Don't delete active subscriptions - this should not happen due to check above
                    subscription.status = 'cancelled'
                    subscription.notes = f"مشروع محذوف: {project.name}"
            
            # Handle tasks if they exist
            try:
                from models.task import Task
                Task.query.filter_by(project_id=project_id).delete()
            except ImportError:
                pass  # Task model doesn't exist
            
            # Handle time tracks if they exist
            try:
                from models.timetrack import TimeTrack
                TimeTrack.query.filter_by(project_id=project_id).delete()
            except ImportError:
                pass  # TimeTrack model doesn't exist
            
            # Handle expenses if they exist
            try:
                from models.expense import Expense
                Expense.query.filter_by(project_id=project_id).delete()
            except ImportError:
                pass  # Expense model doesn't exist
            
            # Clear team members associations
            project.team_members.clear()
            
            # Clear subscription clients associations
            project.subscription_clients.clear()
            
            # Now delete the project
            db.session.delete(project)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'تم حذف المشروع وجميع البيانات المرتبطة به بنجاح'
            })
            
        except Exception as e:
            db.session.rollback()
            print(f"Error during project deletion: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return jsonify({
                'success': False,
                'message': f'حدث خطأ أثناء حذف البيانات المرتبطة: {str(e)}'
            }), 500
        
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting project: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'message': f'حدث خطأ في حذف المشروع: {str(e)}'
        }), 500

@projects_bp.route('/<int:project_id>/subscribers', methods=['POST'])
@jwt_required()
def add_subscriber(project_id):
    """Add subscriber to subscription project"""
    try:
        project = Project.query.get_or_404(project_id)
        
        if project.project_type != 'subscription':
            return jsonify({
                'success': False,
                'message': 'هذا المشروع ليس مشروع اشتراك'
            }), 400
        
        data = request.get_json()
        client_id = data.get('client_id')
        
        if not client_id:
            return jsonify({
                'success': False,
                'message': 'معرف العميل مطلوب'
            }), 400
        
        client = Client.query.get_or_404(client_id)
        project.add_subscription_client(client)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم إضافة المشترك بنجاح',
            'project': project.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في إضافة المشترك'
        }), 500

@projects_bp.route('/<int:project_id>/subscribers/<int:client_id>', methods=['DELETE'])
@jwt_required()
def remove_subscriber(project_id, client_id):
    """Remove subscriber from subscription project"""
    try:
        project = Project.query.get_or_404(project_id)
        
        if project.project_type != 'subscription':
            return jsonify({
                'success': False,
                'message': 'هذا المشروع ليس مشروع اشتراك'
            }), 400
        
        client = Client.query.get_or_404(client_id)
        project.remove_subscription_client(client)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم إزالة المشترك بنجاح',
            'project': project.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في إزالة المشترك'
        }), 500

@projects_bp.route('/<int:project_id>/subscribers', methods=['GET'])
@jwt_required()
def get_subscribers(project_id):
    """Get subscribers for subscription project"""
    try:
        project = Project.query.get_or_404(project_id)
        
        if project.project_type != 'subscription':
            return jsonify({
                'success': False,
                'message': 'هذا المشروع ليس مشروع اشتراك'
            }), 400
        
        # Get all subscription clients for this project
        subscribers = []
        for client in project.subscription_clients:
            subscribers.append(client.to_dict())
        
        return jsonify({
            'success': True,
            'project_id': project_id,
            'project_name': project.name,
            'subscriber_count': len(subscribers),
            'subscribers': subscribers
        })
        
    except Exception as e:
        print(f"Error getting subscribers: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب المشتركين',
            'error': str(e)
        }), 500

@projects_bp.route('/statistics', methods=['GET'])
@jwt_required()
def get_project_statistics():
    """Get project statistics - Enhanced for subscription/one-time projects"""
    try:
        # Basic counts
        total_projects = Project.query.count()
        subscription_projects = Project.query.filter_by(project_type='subscription').count()
        onetime_projects = Project.query.filter_by(project_type='onetime').count()
        active_projects = Project.query.filter_by(status='active').count()
        completed_projects = Project.query.filter_by(status='completed').count()
        
        # Revenue calculations
        monthly_revenue = db.session.query(
            func.sum(Project.monthly_price * Project.subscriber_count)
        ).filter_by(project_type='subscription').scalar() or 0
        
        total_onetime_revenue = db.session.query(
            func.sum(Project.total_amount)
        ).filter_by(project_type='onetime').scalar() or 0
        
        paid_onetime_revenue = db.session.query(
            func.sum(Project.paid_amount)
        ).filter_by(project_type='onetime').scalar() or 0
        
        pending_payments = total_onetime_revenue - paid_onetime_revenue
        
        return jsonify({
            'success': True,
            'statistics': {
                'total_projects': total_projects,
                'subscription_projects': subscription_projects,
                'onetime_projects': onetime_projects,
                'active_projects': active_projects,
                'completed_projects': completed_projects,
                'monthly_revenue': float(monthly_revenue),
                'total_onetime_revenue': float(total_onetime_revenue),
                'paid_onetime_revenue': float(paid_onetime_revenue),
                'pending_payments': float(pending_payments)
            }
        })
        
    except Exception as e:
        print(f"Error getting statistics: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب الإحصائيات',
            'error': str(e)
        }), 500