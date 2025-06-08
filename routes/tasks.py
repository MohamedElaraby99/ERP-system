from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from extensions import db
from models.task import Task

tasks_bp = Blueprint('tasks', __name__)

@tasks_bp.route('/', methods=['GET'])
@jwt_required()
def get_tasks():
    """Get all tasks"""
    try:
        project_id = request.args.get('project_id', type=int)
        
        query = Task.query
        if project_id:
            query = query.filter_by(project_id=project_id)
        
        tasks = query.order_by(Task.created_at.desc()).all()
        
        return jsonify({
            'success': True,
            'tasks': [task.to_dict() for task in tasks]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب المهام'
        }), 500

@tasks_bp.route('/<int:task_id>', methods=['GET'])
@jwt_required()
def get_task(task_id):
    """Get single task by ID"""
    try:
        task = Task.query.get_or_404(task_id)
        
        return jsonify({
            'success': True,
            'task': task.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'المهمة غير موجودة'
        }), 404 