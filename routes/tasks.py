from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date
from extensions import db
from models.task import Task, TaskComment, TaskTimeLog, TaskAssignment, TaskStatus, TaskPriority
from models.project import Project
from models.employee import Employee
from models.user import User

tasks_bp = Blueprint('tasks', __name__)

@tasks_bp.route('/', methods=['GET'])
@jwt_required()
def get_tasks():
    """Get all tasks with optional filtering"""
    try:
        # Get query parameters
        status = request.args.get('status')
        priority = request.args.get('priority')
        project_id = request.args.get('project_id', type=int)
        assignee_id = request.args.get('assignee_id', type=int)
        created_by_id = request.args.get('created_by_id', type=int)
        overdue_only = request.args.get('overdue_only', 'false').lower() == 'true'
        my_tasks_only = request.args.get('my_tasks_only', 'false').lower() == 'true'
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)

        # Build query
        query = Task.query

        # Apply filters
        if status:
            try:
                status_enum = TaskStatus(status)
                query = query.filter(Task.status == status_enum)
            except ValueError:
                pass

        if priority:
            try:
                priority_enum = TaskPriority(priority)
                query = query.filter(Task.priority == priority_enum)
            except ValueError:
                pass

        if project_id:
            query = query.filter(Task.project_id == project_id)

        if assignee_id:
            query = query.filter(Task.assignee_id == assignee_id)

        if created_by_id:
            query = query.filter(Task.created_by_id == created_by_id)

        # My tasks filter - get current user's employee record
        if my_tasks_only:
            current_user_id = get_jwt_identity()
            user = User.query.get(current_user_id)
            if user and user.employee:
                query = query.filter(Task.assignee_id == user.employee.id)

        # Order by priority and due date
        query = query.order_by(
            Task.priority.desc(),
            Task.due_date.asc(),
            Task.created_at.desc()
        )

        # Execute pagination
        tasks_paginated = query.paginate(
            page=page, per_page=per_page, error_out=False
        )

        tasks = tasks_paginated.items

        # Filter overdue if requested
        if overdue_only:
            tasks = [task for task in tasks if task.is_overdue]

        return jsonify({
            'success': True,
            'tasks': [task.to_dict() for task in tasks],
            'total': tasks_paginated.total,
            'pages': tasks_paginated.pages,
            'current_page': page,
            'per_page': per_page,
            'has_next': tasks_paginated.has_next,
            'has_prev': tasks_paginated.has_prev
        }), 200

    except Exception as e:
        print(f"❌ Error getting tasks: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب المهام'
        }), 500

@tasks_bp.route('/', methods=['POST'])
@jwt_required()
def create_task():
    """Create a new task"""
    try:
        data = request.get_json()
        current_user_id = get_jwt_identity()

        # Validate required fields
        required_fields = ['title', 'project_id', 'assignee_id', 'start_date', 'due_date']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'message': f'الحقل {field} مطلوب'
                }), 400

        # Validate dates
        try:
            start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date()
            
            if due_date < start_date:
                return jsonify({
                    'success': False,
                    'message': 'تاريخ الانتهاء يجب أن يكون بعد تاريخ البداية'
                }), 400
                
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'تنسيق التاريخ غير صحيح (يجب أن يكون YYYY-MM-DD)'
            }), 400

        # Validate project exists
        project = Project.query.get(data['project_id'])
        if not project:
            return jsonify({
                'success': False,
                'message': 'المشروع غير موجود'
            }), 404

        # Validate assignee exists
        assignee = Employee.query.get(data['assignee_id'])
        if not assignee:
            return jsonify({
                'success': False,
                'message': 'الموظف المُكلف غير موجود'
            }), 404

        # Validate priority and status
        try:
            priority = TaskPriority(data.get('priority', 'medium'))
            status = TaskStatus(data.get('status', 'pending'))
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'قيمة الأولوية أو الحالة غير صحيحة'
            }), 400

        # Create task
        task = Task(
            title=data['title'],
            description=data.get('description', ''),
            project_id=data['project_id'],
            assignee_id=data['assignee_id'],
            created_by_id=current_user_id,
            priority=priority,
            status=status,
            start_date=start_date,
            due_date=due_date,
            estimated_hours=data.get('estimated_hours'),
            progress_percentage=data.get('progress_percentage', 0),
            tags=data.get('tags', []),
            dependencies=data.get('dependencies', [])
        )

        db.session.add(task)
        db.session.commit()

        print(f"✅ Task created successfully: {task.title}")
        
        return jsonify({
            'success': True,
            'message': 'تم إنشاء المهمة بنجاح',
            'task': task.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error creating task: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في إنشاء المهمة'
        }), 500

@tasks_bp.route('/<int:task_id>', methods=['GET'])
@jwt_required()
def get_task(task_id):
    """Get task details"""
    try:
        task = Task.query.get_or_404(task_id)
        
        # Get additional details
        task_dict = task.to_dict()
        
        # Add comments
        comments = TaskComment.query.filter_by(task_id=task_id).order_by(TaskComment.created_at.desc()).all()
        task_dict['comments'] = [comment.to_dict() for comment in comments]
        
        # Add time logs
        time_logs = TaskTimeLog.query.filter_by(task_id=task_id).order_by(TaskTimeLog.logged_at.desc()).all()
        task_dict['time_logs'] = [log.to_dict() for log in time_logs]
        
        return jsonify({
            'success': True,
            'task': task_dict
        }), 200

    except Exception as e:
        print(f"❌ Error getting task: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'المهمة غير موجودة'
        }), 404

@tasks_bp.route('/<int:task_id>', methods=['PUT'])
@jwt_required()
def update_task(task_id):
    """Update task details"""
    try:
        task = Task.query.get_or_404(task_id)
        data = request.get_json()

        # Update basic fields
        if 'title' in data:
            task.title = data['title']
        if 'description' in data:
            task.description = data['description']

        # Update dates
        if 'start_date' in data and data['start_date']:
            try:
                task.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': 'تنسيق تاريخ البداية غير صحيح'
                }), 400

        if 'due_date' in data and data['due_date']:
            try:
                task.due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': 'تنسيق تاريخ الانتهاء غير صحيح'
                }), 400

        # Validate date logic
        if task.due_date < task.start_date:
            return jsonify({
                'success': False,
                'message': 'تاريخ الانتهاء يجب أن يكون بعد تاريخ البداية'
            }), 400

        # Update assignee
        if 'assignee_id' in data and data['assignee_id']:
            assignee = Employee.query.get(data['assignee_id'])
            if not assignee:
                return jsonify({
                    'success': False,
                    'message': 'الموظف المُكلف غير موجود'
                }), 404
            task.assignee_id = data['assignee_id']

        # Update priority and status
        if 'priority' in data:
            try:
                task.priority = TaskPriority(data['priority'])
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': 'قيمة الأولوية غير صحيحة'
                }), 400

        if 'status' in data:
            try:
                new_status = TaskStatus(data['status'])
                old_status = task.status
                task.status = new_status
                
                # Handle status changes
                if new_status == TaskStatus.COMPLETED and old_status != TaskStatus.COMPLETED:
                    task.completed_date = datetime.utcnow()
                    task.progress_percentage = 100
                elif new_status != TaskStatus.COMPLETED:
                    task.completed_date = None
                    
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': 'قيمة الحالة غير صحيحة'
                }), 400

        # Update other fields
        if 'estimated_hours' in data:
            task.estimated_hours = data['estimated_hours']
        if 'progress_percentage' in data:
            task.update_progress(data['progress_percentage'])
        if 'tags' in data:
            task.tags = data['tags']
        if 'dependencies' in data:
            task.dependencies = data['dependencies']

        task.updated_at = datetime.utcnow()
        db.session.commit()

        print(f"✅ Task updated successfully: {task.title}")

        return jsonify({
            'success': True,
            'message': 'تم تحديث المهمة بنجاح',
            'task': task.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error updating task: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في تحديث المهمة'
        }), 500

@tasks_bp.route('/<int:task_id>', methods=['DELETE'])
@jwt_required()
def delete_task(task_id):
    """Delete a task"""
    try:
        task = Task.query.get_or_404(task_id)
        
        # Store task title for response
        task_title = task.title
        
        # Delete task (cascade will handle comments and time logs)
        db.session.delete(task)
        db.session.commit()

        print(f"✅ Task deleted successfully: {task_title}")

        return jsonify({
            'success': True,
            'message': 'تم حذف المهمة بنجاح'
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error deleting task: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في حذف المهمة'
        }), 500

@tasks_bp.route('/<int:task_id>/comments', methods=['POST'])
@jwt_required()
def add_comment(task_id):
    """Add comment to task"""
    try:
        task = Task.query.get_or_404(task_id)
        data = request.get_json()
        current_user_id = get_jwt_identity()

        if not data.get('content'):
            return jsonify({
                'success': False,
                'message': 'محتوى التعليق مطلوب'
            }), 400

        comment = task.add_comment(data['content'], current_user_id)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'تم إضافة التعليق بنجاح',
            'comment': comment.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error adding comment: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في إضافة التعليق'
        }), 500

@tasks_bp.route('/<int:task_id>/time-log', methods=['POST'])
@jwt_required()
def add_time_log(task_id):
    """Add time log to task"""
    try:
        task = Task.query.get_or_404(task_id)
        data = request.get_json()
        current_user_id = get_jwt_identity()

        if not data.get('hours') or data['hours'] <= 0:
            return jsonify({
                'success': False,
                'message': 'عدد الساعات مطلوب ويجب أن يكون أكبر من صفر'
            }), 400

        task.add_time_log(
            hours=data['hours'],
            description=data.get('description'),
            user_id=current_user_id
        )
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'تم تسجيل الوقت بنجاح',
            'task': task.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error adding time log: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في تسجيل الوقت'
        }), 500

@tasks_bp.route('/<int:task_id>/progress', methods=['PUT'])
@jwt_required()
def update_progress(task_id):
    """Update task progress"""
    try:
        task = Task.query.get_or_404(task_id)
        data = request.get_json()

        if 'progress_percentage' not in data:
            return jsonify({
                'success': False,
                'message': 'نسبة التقدم مطلوبة'
            }), 400

        progress = data['progress_percentage']
        if not (0 <= progress <= 100):
            return jsonify({
                'success': False,
                'message': 'نسبة التقدم يجب أن تكون بين 0 و 100'
            }), 400

        task.update_progress(progress)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'تم تحديث نسبة التقدم بنجاح',
            'task': task.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error updating progress: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في تحديث نسبة التقدم'
        }), 500

@tasks_bp.route('/employee/<int:employee_id>', methods=['GET'])
@jwt_required()
def get_employee_tasks(employee_id):
    """Get tasks assigned to specific employee"""
    try:
        employee = Employee.query.get_or_404(employee_id)
        
        # Get query parameters
        status = request.args.get('status')
        priority = request.args.get('priority')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        # Build query
        query = Task.query.filter(Task.assignee_id == employee_id)

        # Apply filters
        if status:
            try:
                status_enum = TaskStatus(status)
                query = query.filter(Task.status == status_enum)
            except ValueError:
                pass

        if priority:
            try:
                priority_enum = TaskPriority(priority)
                query = query.filter(Task.priority == priority_enum)
            except ValueError:
                pass

        # Order by priority and due date
        query = query.order_by(
            Task.priority.desc(),
            Task.due_date.asc()
        )

        # Execute pagination
        tasks_paginated = query.paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify({
            'success': True,
            'employee': {
                'id': employee.id,
                'name': f"{employee.first_name} {employee.last_name}",
                'email': employee.email
            },
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

@tasks_bp.route('/statistics', methods=['GET'])
@jwt_required()
def get_task_statistics():
    """Get task statistics"""
    try:
        # Overall statistics
        total_tasks = Task.query.count()
        pending_tasks = Task.query.filter(Task.status == TaskStatus.PENDING).count()
        in_progress_tasks = Task.query.filter(Task.status == TaskStatus.IN_PROGRESS).count()
        completed_tasks = Task.query.filter(Task.status == TaskStatus.COMPLETED).count()
        overdue_tasks = len([task for task in Task.query.all() if task.is_overdue])
        
        # Priority distribution
        high_priority = Task.query.filter(Task.priority == TaskPriority.HIGH).count()
        medium_priority = Task.query.filter(Task.priority == TaskPriority.MEDIUM).count()
        low_priority = Task.query.filter(Task.priority == TaskPriority.LOW).count()
        urgent_priority = Task.query.filter(Task.priority == TaskPriority.URGENT).count()

        # Employee workload
        from sqlalchemy import func
        employee_workload = db.session.query(
            Employee.id,
            Employee.first_name,
            Employee.last_name,
            func.count(Task.id).label('task_count')
        ).join(Task, Employee.id == Task.assignee_id)\
         .group_by(Employee.id, Employee.first_name, Employee.last_name)\
         .all()

        workload_data = []
        for emp_id, first_name, last_name, task_count in employee_workload:
            workload_data.append({
                'employee_id': emp_id,
                'employee_name': f"{first_name} {last_name}",
                'task_count': task_count
            })

        statistics = {
            'total_tasks': total_tasks,
            'pending_tasks': pending_tasks,
            'in_progress_tasks': in_progress_tasks,
            'completed_tasks': completed_tasks,
            'overdue_tasks': overdue_tasks,
            'completion_rate': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            'priority_distribution': {
                'urgent': urgent_priority,
                'high': high_priority,
                'medium': medium_priority,
                'low': low_priority
            },
            'employee_workload': workload_data
        }

        return jsonify({
            'success': True,
            'statistics': statistics
        }), 200

    except Exception as e:
        print(f"❌ Error getting task statistics: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب الإحصائيات'
        }), 500

@tasks_bp.route('/assign', methods=['POST'])
@jwt_required()
def assign_task():
    """Assign or reassign task to employee"""
    try:
        data = request.get_json()
        current_user_id = get_jwt_identity()

        required_fields = ['task_id', 'employee_id']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'الحقل {field} مطلوب'
                }), 400

        # Validate task exists
        task = Task.query.get(data['task_id'])
        if not task:
            return jsonify({
                'success': False,
                'message': 'المهمة غير موجودة'
            }), 404

        # Validate employee exists
        employee = Employee.query.get(data['employee_id'])
        if not employee:
            return jsonify({
                'success': False,
                'message': 'الموظف غير موجود'
            }), 404

        # Update task assignment
        old_assignee = task.assignee
        task.assignee_id = data['employee_id']
        task.updated_at = datetime.utcnow()

        # Create assignment record
        assignment = TaskAssignment(
            task_id=data['task_id'],
            employee_id=data['employee_id'],
            assigned_by_id=current_user_id,
            role=data.get('role', 'assignee')
        )
        db.session.add(assignment)
        db.session.commit()

        message = f"تم تعيين المهمة '{task.title}' إلى {employee.first_name} {employee.last_name}"
        if old_assignee:
            message += f" (كانت مُعيّنة لـ {old_assignee.first_name} {old_assignee.last_name})"

        print(f"✅ Task assigned successfully: {message}")

        return jsonify({
            'success': True,
            'message': message,
            'task': task.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error assigning task: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في تعيين المهمة'
        }), 500 