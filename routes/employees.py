from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from extensions import db
from models.employee import Employee
from models.user import User
from models.task import Task
from sqlalchemy import func, extract, and_, or_
import hashlib

employees_bp = Blueprint('employees', __name__)

@employees_bp.route('/', methods=['GET'])
@jwt_required()
def get_employees():
    """Get all employees with advanced filtering and pagination"""
    try:
        # Get query parameters
        department = request.args.get('department')
        status = request.args.get('status')
        employment_type = request.args.get('employment_type')
        search = request.args.get('search')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        sort_by = request.args.get('sort_by', 'first_name')
        sort_order = request.args.get('sort_order', 'asc')
        
        # Performance filters
        min_rating = request.args.get('min_rating', type=float)
        max_rating = request.args.get('max_rating', type=float)
        
        # Date filters
        hired_after = request.args.get('hired_after')
        hired_before = request.args.get('hired_before')

        # Build query
        query = Employee.query

        # Apply filters
        if department:
            query = query.filter(Employee.department == department)

        if status:
            query = query.filter(Employee.status == status)
            
        if employment_type:
            query = query.filter(Employee.employment_type == employment_type)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Employee.first_name.ilike(search_term),
                    Employee.last_name.ilike(search_term),
                    Employee.email.ilike(search_term),
                    Employee.employee_id.ilike(search_term),
                    Employee.position.ilike(search_term)
                )
            )
            
        # Performance rating filters
        if min_rating is not None:
            query = query.filter(Employee.performance_rating >= min_rating)
        if max_rating is not None:
            query = query.filter(Employee.performance_rating <= max_rating)
            
        # Date filters
        if hired_after:
            try:
                date_after = datetime.strptime(hired_after, '%Y-%m-%d').date()
                query = query.filter(Employee.hire_date >= date_after)
            except ValueError:
                pass
                
        if hired_before:
            try:
                date_before = datetime.strptime(hired_before, '%Y-%m-%d').date()
                query = query.filter(Employee.hire_date <= date_before)
            except ValueError:
                pass

        # Apply sorting
        sort_column = getattr(Employee, sort_by, Employee.first_name)
        if sort_order.lower() == 'desc':
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Execute pagination
        employees_paginated = query.paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify({
            'success': True,
            'employees': [employee.to_dict() for employee in employees_paginated.items],
            'total': employees_paginated.total,
            'pages': employees_paginated.pages,
            'current_page': page,
            'per_page': per_page,
            'has_next': employees_paginated.has_next,
            'has_prev': employees_paginated.has_prev
        }), 200

    except Exception as e:
        print(f"❌ Error getting employees: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب الموظفين'
        }), 500

@employees_bp.route('/<int:employee_id>', methods=['GET'])
@jwt_required()
def get_employee(employee_id):
    """Get employee details with additional stats"""
    try:
        employee = Employee.query.get_or_404(employee_id)
        
        # Get additional statistics
        employee_data = employee.to_dict()
        
        # Get task statistics
        total_tasks = Task.query.filter_by(assignee_id=employee_id).count()
        completed_tasks = Task.query.filter(
            and_(Task.assignee_id == employee_id, Task.status == 'COMPLETED')
        ).count()
        
        employee_data.update({
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'task_completion_rate': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        })
        
        return jsonify({
            'success': True,
            'employee': employee_data
        }), 200

    except Exception as e:
        print(f"❌ Error getting employee: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'الموظف غير موجود'
        }), 404

@employees_bp.route('/', methods=['POST'])
@jwt_required()
def create_employee():
    """Create new employee with user account"""
    try:
        data = request.get_json()
        print(f"📊 Received employee data: {data}")

        # Validate required fields
        required_fields = ['first_name', 'last_name', 'email', 'position', 'department', 'hire_date', 'password']
        for field in required_fields:
            if field not in data or not data[field]:
                print(f"❌ Missing required field: {field}")
                return jsonify({
                    'success': False,
                    'message': f'الحقل {field} مطلوب'
                }), 400

        # Check if email already exists in Employee table
        if Employee.query.filter_by(email=data['email']).first():
            return jsonify({
                'success': False,
                'message': 'البريد الإلكتروني موجود بالفعل'
            }), 400
            
        # Check if email already exists in User table
        if User.query.filter_by(email=data['email']).first():
            return jsonify({
                'success': False,
                'message': 'البريد الإلكتروني موجود بالفعل في النظام'
            }), 400

        # Generate employee ID
        employee_count = Employee.query.count()
        employee_id = f"EMP{employee_count + 1:04d}"

        # Check if employee_id is provided and unique
        if 'employee_id' in data and data['employee_id']:
            if Employee.query.filter_by(employee_id=data['employee_id']).first():
                return jsonify({
                    'success': False,
                    'message': 'رقم الموظف موجود بالفعل'
                }), 400
            employee_id = data['employee_id']

        # Parse hire date
        try:
            hire_date = datetime.strptime(data['hire_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'تنسيق تاريخ التوظيف غير صحيح (يجب أن يكون YYYY-MM-DD)'
            }), 400

        # Parse birth date if provided
        date_of_birth = None
        if data.get('date_of_birth'):
            try:
                date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': 'تنسيق تاريخ الميلاد غير صحيح (يجب أن يكون YYYY-MM-DD)'
                }), 400

        # Create user account first
        user = User(
            username=data['email'],
            email=data['email'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            role=data.get('role', 'employee'),
            is_active=True,
            is_verified=True
        )
        # Set password using the setter (which uses bcrypt)
        user.password = data['password']
        
        db.session.add(user)
        db.session.flush()  # Get user ID

        # Parse skills if provided as string
        skills = data.get('skills', [])
        if isinstance(skills, str):
            skills = [skill.strip() for skill in skills.split(',') if skill.strip()]

        # Create employee
        employee = Employee(
            employee_id=employee_id,
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'],
            phone=data.get('phone'),
            address=data.get('address'),
            date_of_birth=date_of_birth,
            national_id=data.get('national_id'),
            position=data['position'],
            department=data['department'],
            hire_date=hire_date,
            employment_type=data.get('employment_type', 'full_time'),
            status=data.get('status', 'active'),
            salary=data.get('salary'),
            hourly_rate=data.get('hourly_rate'),
            currency=data.get('currency', 'SAR'),
            skills=skills,
            education=data.get('education'),
            certifications=data.get('certifications', []),
            languages=data.get('languages', []),
            emergency_contact_name=data.get('emergency_contact_name'),
            emergency_contact_phone=data.get('emergency_contact_phone'),
            emergency_contact_relation=data.get('emergency_contact_relation'),
            bank_name=data.get('bank_name'),
            bank_account=data.get('bank_account'),
            iban=data.get('iban'),
            manager_id=data.get('manager_id'),
            user_id=user.id
        )

        db.session.add(employee)
        db.session.commit()

        print(f"✅ Employee created successfully: {employee.full_name}")

        return jsonify({
            'success': True,
            'message': 'تم إنشاء الموظف بنجاح',
            'employee': employee.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error creating employee: {str(e)}")
        print(f"❌ Error type: {type(e).__name__}")
        print(f"❌ Error details: {repr(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'حدث خطأ في إنشاء الموظف: {str(e)}'
        }), 500

@employees_bp.route('/<int:employee_id>', methods=['PUT'])
@jwt_required()
def update_employee(employee_id):
    """Update employee details"""
    try:
        employee = Employee.query.get_or_404(employee_id)
        data = request.get_json()

        # Update basic information
        if 'first_name' in data:
            employee.first_name = data['first_name']
        if 'last_name' in data:
            employee.last_name = data['last_name']
        
        # Check email uniqueness if changing
        if 'email' in data and data['email'] != employee.email:
            if Employee.query.filter_by(email=data['email']).first():
                return jsonify({
                    'success': False,
                    'message': 'البريد الإلكتروني موجود بالفعل'
                }), 400
            employee.email = data['email']
            
            # Update user email if exists
            if employee.user_id:
                user = User.query.get(employee.user_id)
                if user:
                    user.email = data['email']
                    user.username = data['email']

        # Parse skills if provided as string
        if 'skills' in data:
            skills = data['skills']
            if isinstance(skills, str):
                skills = [skill.strip() for skill in skills.split(',') if skill.strip()]
            employee.skills = skills

        # Update other fields
        updatable_fields = [
            'phone', 'address', 'national_id', 'position', 'department',
            'employment_type', 'status', 'salary', 'hourly_rate', 'currency',
            'education', 'certifications', 'languages',
            'emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relation',
            'bank_name', 'bank_account', 'iban', 'manager_id', 'performance_rating'
        ]

        for field in updatable_fields:
            if field in data:
                setattr(employee, field, data[field])
                
        # Update user data if provided
        if employee.user_id and ('role' in data or 'password' in data or 'is_active' in data):
            user = User.query.get(employee.user_id)
            if user:
                if 'role' in data:
                    user.role = data['role']
                    print(f"🔄 Updated user role to: {data['role']}")
                    
                if 'password' in data and data['password']:
                    user.password = data['password']
                    print(f"🔄 Updated user password")
                    
                if 'is_active' in data:
                    user.is_active = data['is_active']
                    print(f"🔄 Updated user active status to: {data['is_active']}")

        # Update dates
        if 'hire_date' in data and data['hire_date']:
            try:
                employee.hire_date = datetime.strptime(data['hire_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': 'تنسيق تاريخ التوظيف غير صحيح'
                }), 400

        if 'date_of_birth' in data and data['date_of_birth']:
            try:
                employee.date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': 'تنسيق تاريخ الميلاد غير صحيح'
                }), 400

        if 'last_performance_review' in data and data['last_performance_review']:
            try:
                employee.last_performance_review = datetime.strptime(data['last_performance_review'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': 'تنسيق تاريخ آخر تقييم أداء غير صحيح'
                }), 400

        employee.updated_at = datetime.utcnow()
        db.session.commit()

        print(f"✅ Employee updated successfully: {employee.full_name}")

        return jsonify({
            'success': True,
            'message': 'تم تحديث الموظف بنجاح',
            'employee': employee.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error updating employee: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في تحديث الموظف'
        }), 500

@employees_bp.route('/<int:employee_id>', methods=['DELETE'])
@jwt_required()
def delete_employee(employee_id):
    """Delete employee with validation"""
    try:
        employee = Employee.query.get_or_404(employee_id)
        
        # Check if employee has active tasks
        active_tasks = Task.query.filter(
            and_(Task.assignee_id == employee_id, Task.status.in_(['PENDING', 'IN_PROGRESS']))
        ).count()
        
        if active_tasks > 0:
            return jsonify({
                'success': False,
                'message': f'لا يمكن حذف الموظف لوجود {active_tasks} مهام نشطة مرتبطة به'
            }), 400

        # Store employee name for logging
        employee_name = employee.full_name
        
        # Delete associated user if exists
        if employee.user_id:
            user = User.query.get(employee.user_id)
            if user:
                db.session.delete(user)

        db.session.delete(employee)
        db.session.commit()

        print(f"✅ Employee deleted successfully: {employee_name}")

        return jsonify({
            'success': True,
            'message': 'تم حذف الموظف بنجاح'
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error deleting employee: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في حذف الموظف'
        }), 500

@employees_bp.route('/departments', methods=['GET'])
@jwt_required()
def get_departments():
    """Get all departments with employee counts"""
    try:
        departments = db.session.query(
            Employee.department,
            func.count(Employee.id).label('employee_count')
        ).filter(
            Employee.status == 'active'
        ).group_by(Employee.department).all()

        departments_list = [
            {
                'name': dept.department,
                'employee_count': dept.employee_count
            }
            for dept in departments if dept.department
        ]

        return jsonify({
            'success': True,
            'departments': departments_list
        }), 200

    except Exception as e:
        print(f"❌ Error getting departments: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب الأقسام'
        }), 500

@employees_bp.route('/statistics', methods=['GET'])
@jwt_required()
def get_employee_statistics():
    """Get comprehensive employee statistics"""
    try:
        # Basic counts
        total_employees = Employee.query.filter_by(status='active').count()
        total_departments = db.session.query(Employee.department).distinct().count()
        
        # Employment type breakdown
        employment_types = db.session.query(
            Employee.employment_type,
            func.count(Employee.id).label('count')
        ).filter(Employee.status == 'active').group_by(Employee.employment_type).all()
        
        # Department breakdown
        departments = db.session.query(
            Employee.department,
            func.count(Employee.id).label('count')
        ).filter(Employee.status == 'active').group_by(Employee.department).all()
        
        # Performance statistics
        avg_performance = db.session.query(
            func.avg(Employee.performance_rating)
        ).filter(
            and_(Employee.status == 'active', Employee.performance_rating.isnot(None))
        ).scalar() or 0
        
        # Recent hires (last 30 days)
        thirty_days_ago = datetime.now().date() - timedelta(days=30)
        recent_hires = Employee.query.filter(
            and_(Employee.hire_date >= thirty_days_ago, Employee.status == 'active')
        ).count()
        
        # Salary statistics
        salary_stats = db.session.query(
            func.avg(Employee.salary).label('avg_salary'),
            func.min(Employee.salary).label('min_salary'),
            func.max(Employee.salary).label('max_salary')
        ).filter(
            and_(Employee.status == 'active', Employee.salary.isnot(None))
        ).first()

        return jsonify({
            'success': True,
            'statistics': {
                'total_employees': total_employees,
                'total_departments': total_departments,
                'recent_hires': recent_hires,
                'average_performance': float(avg_performance),
                'employment_types': [
                    {'type': et.employment_type, 'count': et.count}
                    for et in employment_types
                ],
                'departments': [
                    {'department': dept.department, 'count': dept.count}
                    for dept in departments
                ],
                'salary_statistics': {
                    'average': float(salary_stats.avg_salary) if salary_stats.avg_salary else 0,
                    'minimum': float(salary_stats.min_salary) if salary_stats.min_salary else 0,
                    'maximum': float(salary_stats.max_salary) if salary_stats.max_salary else 0
                }
            }
        }), 200

    except Exception as e:
        print(f"❌ Error getting employee statistics: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب الإحصائيات'
        }), 500

@employees_bp.route('/bulk-update', methods=['PUT'])
@jwt_required()
def bulk_update_employees():
    """Bulk update multiple employees"""
    try:
        data = request.get_json()
        employee_ids = data.get('employee_ids', [])
        updates = data.get('updates', {})
        
        if not employee_ids:
            return jsonify({
                'success': False,
                'message': 'لم يتم تحديد موظفين للتحديث'
            }), 400
            
        # Validate employee IDs
        employees = Employee.query.filter(Employee.id.in_(employee_ids)).all()
        if len(employees) != len(employee_ids):
            return jsonify({
                'success': False,
                'message': 'بعض الموظفين المحددين غير موجودين'
            }), 400
        
        # Apply updates
        for employee in employees:
            for field, value in updates.items():
                if hasattr(employee, field):
                    setattr(employee, field, value)
            employee.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'تم تحديث {len(employees)} موظف بنجاح',
            'updated_count': len(employees)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error in bulk update: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في التحديث الجماعي'
        }), 500

@employees_bp.route('/<int:employee_id>/tasks', methods=['GET'])
@jwt_required()
def get_employee_tasks(employee_id):
    """Get tasks assigned to specific employee"""
    try:
        employee = Employee.query.get_or_404(employee_id)
        
        # Get query parameters
        status = request.args.get('status')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Build query
        query = Task.query.filter_by(assignee_id=employee_id)
        
        if status:
            query = query.filter(Task.status == status)
            
        # Order by created date
        query = query.order_by(Task.created_at.desc())
        
        # Execute pagination
        tasks_paginated = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'employee': employee.to_dict(),
            'tasks': [task.to_dict() for task in tasks_paginated.items],
            'total': tasks_paginated.total,
            'pages': tasks_paginated.pages,
            'current_page': page,
            'per_page': per_page
        }), 200
        
    except Exception as e:
        print(f"❌ Error getting employee tasks: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب مهام الموظف'
        }), 500

@employees_bp.route('/<int:employee_id>/performance', methods=['PUT'])
@jwt_required()
def update_employee_performance(employee_id):
    """Update employee performance rating"""
    try:
        employee = Employee.query.get_or_404(employee_id)
        data = request.get_json()
        
        # Validate performance rating
        rating = data.get('performance_rating')
        if rating is None or not (1 <= rating <= 5):
            return jsonify({
                'success': False,
                'message': 'يجب أن يكون تقييم الأداء بين 1 و 5'
            }), 400
            
        employee.performance_rating = rating
        employee.last_performance_review = datetime.now().date()
        employee.updated_at = datetime.utcnow()
        
        # Add review notes if provided
        if 'review_notes' in data:
            # You could store this in a separate PerformanceReview model
            pass
            
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم تحديث تقييم الأداء بنجاح',
            'employee': employee.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error updating performance: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في تحديث تقييم الأداء'
        }), 500 