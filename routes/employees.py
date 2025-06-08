from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from extensions import db
from models.employee import Employee
from models.user import User

employees_bp = Blueprint('employees', __name__)

@employees_bp.route('/', methods=['GET'])
@jwt_required()
def get_employees():
    """Get all employees"""
    try:
        employees = Employee.query.filter_by(status='active').all()
        
        return jsonify({
            'success': True,
            'employees': [employee.to_dict() for employee in employees]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب الموظفين'
        }), 500

@employees_bp.route('/<int:employee_id>', methods=['GET'])
@jwt_required()
def get_employee(employee_id):
    """Get single employee by ID"""
    try:
        employee = Employee.query.get_or_404(employee_id)
        
        return jsonify({
            'success': True,
            'employee': employee.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'الموظف غير موجود'
        }), 404

@employees_bp.route('/', methods=['POST'])
@jwt_required()
def create_employee():
    """Create new employee"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['employee_id', 'first_name', 'last_name', 'email', 'position', 'department', 'hire_date']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'الحقل {field} مطلوب'
                }), 400
        
        # Check if employee_id or email already exists
        if Employee.query.filter_by(employee_id=data['employee_id']).first():
            return jsonify({
                'success': False,
                'message': 'رقم الموظف مستخدم بالفعل'
            }), 400
        
        if Employee.query.filter_by(email=data['email']).first():
            return jsonify({
                'success': False,
                'message': 'البريد الإلكتروني مستخدم بالفعل'
            }), 400
        
        # Create employee
        employee = Employee(
            employee_id=data['employee_id'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'],
            phone=data.get('phone'),
            address=data.get('address'),
            position=data['position'],
            department=data['department'],
            employment_type=data.get('employment_type', 'full_time'),
            status=data.get('status', 'active'),
            salary=data.get('salary'),
            hourly_rate=data.get('hourly_rate'),
            skills=data.get('skills', []),
            education=data.get('education'),
            certifications=data.get('certifications', []),
            languages=data.get('languages', []),
            manager_id=data.get('manager_id')
        )
        
        # Parse dates
        if data.get('hire_date'):
            employee.hire_date = datetime.strptime(data['hire_date'], '%Y-%m-%d').date()
        if data.get('date_of_birth'):
            employee.date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
        
        db.session.add(employee)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم إنشاء الموظف بنجاح',
            'employee': employee.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في إنشاء الموظف'
        }), 500

@employees_bp.route('/<int:employee_id>', methods=['PUT'])
@jwt_required()
def update_employee(employee_id):
    """Update employee"""
    try:
        employee = Employee.query.get_or_404(employee_id)
        data = request.get_json()
        
        # Check permissions (admin or manager)
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user.role in ['admin', 'manager']:
            return jsonify({
                'success': False,
                'message': 'ليس لديك صلاحية لتعديل بيانات الموظف'
            }), 403
        
        # Update allowed fields
        allowed_fields = [
            'first_name', 'last_name', 'email', 'phone', 'address',
            'position', 'department', 'employment_type', 'status',
            'salary', 'hourly_rate', 'skills', 'education', 'certifications',
            'languages', 'manager_id', 'performance_rating'
        ]
        
        for field in allowed_fields:
            if field in data:
                setattr(employee, field, data[field])
        
        # Parse dates
        if 'hire_date' in data:
            employee.hire_date = datetime.strptime(data['hire_date'], '%Y-%m-%d').date() if data['hire_date'] else None
        if 'date_of_birth' in data:
            employee.date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date() if data['date_of_birth'] else None
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم تحديث بيانات الموظف بنجاح',
            'employee': employee.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في تحديث بيانات الموظف'
        }), 500

@employees_bp.route('/<int:employee_id>', methods=['DELETE'])
@jwt_required()
def delete_employee(employee_id):
    """Delete employee (soft delete by changing status)"""
    try:
        employee = Employee.query.get_or_404(employee_id)
        
        # Check permissions (admin only)
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if user.role != 'admin':
            return jsonify({
                'success': False,
                'message': 'ليس لديك صلاحية لحذف الموظف'
            }), 403
        
        # Soft delete by changing status
        employee.status = 'terminated'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم حذف الموظف بنجاح'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في حذف الموظف'
        }), 500

@employees_bp.route('/departments', methods=['GET'])
@jwt_required()
def get_departments():
    """Get list of departments"""
    try:
        departments = db.session.query(Employee.department).distinct().all()
        departments_list = [dept[0] for dept in departments if dept[0]]
        
        return jsonify({
            'success': True,
            'departments': departments_list
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب الأقسام'
        }), 500

@employees_bp.route('/statistics', methods=['GET'])
@jwt_required()
def get_employee_statistics():
    """Get employee statistics"""
    try:
        total_employees = Employee.query.count()
        active_employees = Employee.query.filter_by(status='active').count()
        inactive_employees = Employee.query.filter_by(status='inactive').count()
        
        # Department distribution
        dept_stats = db.session.query(
            Employee.department,
            db.func.count(Employee.id)
        ).filter_by(status='active').group_by(Employee.department).all()
        
        department_distribution = [
            {'department': dept, 'count': count}
            for dept, count in dept_stats if dept
        ]
        
        return jsonify({
            'success': True,
            'statistics': {
                'total_employees': total_employees,
                'active_employees': active_employees,
                'inactive_employees': inactive_employees,
                'department_distribution': department_distribution
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب إحصائيات الموظفين'
        }), 500 