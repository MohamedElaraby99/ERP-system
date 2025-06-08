from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date
from extensions import db
from models.project import Project
from models.user import User
from models.client import Client
from models.employee import Employee

projects_bp = Blueprint('projects', __name__)

@projects_bp.route('/', methods=['GET'])
@jwt_required()
def get_projects():
    """Get all projects with pagination and filtering"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        status = request.args.get('status')
        priority = request.args.get('priority')
        client_id = request.args.get('client_id', type=int)
        search = request.args.get('search')
        
        query = Project.query
        
        # Apply filters
        if status:
            query = query.filter(Project.status == status)
        if priority:
            query = query.filter(Project.priority == priority)
        if client_id:
            query = query.filter(Project.client_id == client_id)
        if search:
            query = query.filter(
                Project.name.contains(search) |
                Project.description.contains(search) |
                Project.project_code.contains(search)
            )
        
        # Order by creation date (newest first)
        query = query.order_by(Project.created_at.desc())
        
        # Paginate
        projects = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'success': True,
            'projects': [project.to_dict() for project in projects.items],
            'pagination': {
                'page': page,
                'pages': projects.pages,
                'per_page': per_page,
                'total': projects.total,
                'has_next': projects.has_next,
                'has_prev': projects.has_prev
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب المشاريع'
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
    """Create new project"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'client_id', 'project_code']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'الحقل {field} مطلوب'
                }), 400
        
        # Check if project code already exists
        if Project.query.filter_by(project_code=data['project_code']).first():
            return jsonify({
                'success': False,
                'message': 'رمز المشروع مستخدم بالفعل'
            }), 400
        
        # Validate client exists
        client = Client.query.get(data['client_id'])
        if not client:
            return jsonify({
                'success': False,
                'message': 'العميل غير موجود'
            }), 400
        
        # Create project
        project = Project(
            name=data['name'],
            description=data.get('description'),
            project_code=data['project_code'],
            status=data.get('status', 'planning'),
            priority=data.get('priority', 'medium'),
            category=data.get('category'),
            budget=data.get('budget'),
            hourly_rate=data.get('hourly_rate'),
            estimated_hours=data.get('estimated_hours'),
            technologies=data.get('technologies', []),
            repository_url=data.get('repository_url'),
            staging_url=data.get('staging_url'),
            production_url=data.get('production_url'),
            client_id=data['client_id'],
            created_by=user_id,
            project_manager_id=data.get('project_manager_id')
        )
        
        # Parse dates
        if data.get('start_date'):
            project.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        if data.get('end_date'):
            project.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        
        db.session.add(project)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم إنشاء المشروع بنجاح',
            'project': project.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في إنشاء المشروع'
        }), 500

@projects_bp.route('/<int:project_id>', methods=['PUT'])
@jwt_required()
def update_project(project_id):
    """Update project"""
    try:
        project = Project.query.get_or_404(project_id)
        data = request.get_json()
        
        # Check permissions (project manager or admin)
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not (user.role in ['admin', 'manager'] or 
                project.created_by == user_id or 
                (project.project_manager and project.project_manager.user_id == user_id)):
            return jsonify({
                'success': False,
                'message': 'ليس لديك صلاحية لتعديل هذا المشروع'
            }), 403
        
        # Update allowed fields
        allowed_fields = [
            'name', 'description', 'status', 'priority', 'category',
            'budget', 'hourly_rate', 'estimated_hours', 'progress',
            'technologies', 'repository_url', 'staging_url', 'production_url',
            'project_manager_id'
        ]
        
        for field in allowed_fields:
            if field in data:
                setattr(project, field, data[field])
        
        # Parse dates
        if 'start_date' in data:
            project.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date() if data['start_date'] else None
        if 'end_date' in data:
            project.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date() if data['end_date'] else None
        
        # Update actual start/end dates based on status
        if data.get('status') == 'active' and not project.actual_start_date:
            project.actual_start_date = date.today()
        elif data.get('status') == 'completed' and not project.actual_end_date:
            project.actual_end_date = date.today()
        
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
    """Delete project"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # Check permissions (admin only)
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if user.role != 'admin':
            return jsonify({
                'success': False,
                'message': 'ليس لديك صلاحية لحذف المشروع'
            }), 403
        
        db.session.delete(project)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم حذف المشروع بنجاح'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في حذف المشروع'
        }), 500

@projects_bp.route('/<int:project_id>/team', methods=['POST'])
@jwt_required()
def add_team_member(project_id):
    """Add team member to project"""
    try:
        project = Project.query.get_or_404(project_id)
        data = request.get_json()
        
        employee_id = data.get('employee_id')
        if not employee_id:
            return jsonify({
                'success': False,
                'message': 'معرف الموظف مطلوب'
            }), 400
        
        employee = Employee.query.get(employee_id)
        if not employee:
            return jsonify({
                'success': False,
                'message': 'الموظف غير موجود'
            }), 404
        
        project.add_team_member(employee)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم إضافة الموظف للفريق بنجاح'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في إضافة الموظف'
        }), 500

@projects_bp.route('/<int:project_id>/team/<int:employee_id>', methods=['DELETE'])
@jwt_required()
def remove_team_member(project_id, employee_id):
    """Remove team member from project"""
    try:
        project = Project.query.get_or_404(project_id)
        employee = Employee.query.get_or_404(employee_id)
        
        project.remove_team_member(employee)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم إزالة الموظف من الفريق بنجاح'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في إزالة الموظف'
        }), 500

@projects_bp.route('/statistics', methods=['GET'])
@jwt_required()
def get_project_statistics():
    """Get project statistics"""
    try:
        total_projects = Project.query.count()
        active_projects = Project.query.filter(Project.status.in_(['planning', 'active'])).count()
        completed_projects = Project.query.filter_by(status='completed').count()
        overdue_projects = Project.query.filter(
            Project.end_date < date.today(),
            Project.status.in_(['planning', 'active'])
        ).count()
        
        # Recent projects
        recent_projects = Project.query.order_by(Project.created_at.desc()).limit(5).all()
        
        return jsonify({
            'success': True,
            'statistics': {
                'total_projects': total_projects,
                'active_projects': active_projects,
                'completed_projects': completed_projects,
                'overdue_projects': overdue_projects,
                'recent_projects': [project.to_dict() for project in recent_projects]
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب الإحصائيات'
        }), 500 