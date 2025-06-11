from datetime import datetime
from extensions import db
from enum import Enum

class TaskStatus(Enum):
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    ON_HOLD = 'on_hold'

class TaskPriority(Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    URGENT = 'urgent'

class Task(db.Model):
    """Task model for project task management"""
    
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    task_code = db.Column(db.String(20), unique=True)
    
    # Task Details
    status = db.Column(db.Enum(TaskStatus), default=TaskStatus.PENDING)
    priority = db.Column(db.Enum(TaskPriority), default=TaskPriority.MEDIUM)
    category = db.Column(db.String(50))  # development, design, testing, documentation, meeting
    
    # Time Management
    estimated_hours = db.Column(db.Float)
    actual_hours = db.Column(db.Float, default=0)
    start_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    completed_date = db.Column(db.DateTime)
    
    # Progress
    progress = db.Column(db.Integer, default=0)  # 0-100
    
    # Task Hierarchy
    parent_task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'))
    
    # Dependencies
    dependencies = db.Column(db.JSON)  # [task_id1, task_id2, ...]
    
    # Technical Details
    tags = db.Column(db.JSON)  # ['frontend', 'api', 'database']
    files = db.Column(db.JSON)  # File attachments
    links = db.Column(db.JSON)  # External links
    
    # Foreign Keys
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    assignee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    parent_task = db.relationship('Task', remote_side=[id], backref='subtasks')
    project = db.relationship('Project', backref='tasks')
    assignee = db.relationship('Employee', backref='assigned_tasks')
    created_by = db.relationship('User', backref='created_tasks')
    comments = db.relationship('TaskComment', backref='task', lazy='dynamic', cascade='all, delete-orphan')
    time_logs = db.relationship('TaskTimeLog', backref='task', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def is_overdue(self):
        """Check if task is overdue"""
        if self.status == TaskStatus.COMPLETED:
            return False
        return self.due_date < datetime.now().date()
    
    @property
    def total_hours_tracked(self):
        """Calculate total hours tracked for this task"""
        from sqlalchemy import func
        return db.session.query(func.sum(TaskTimeLog.hours)).filter_by(task_id=self.id).scalar() or 0
    
    @property
    def completion_percentage(self):
        """Calculate completion percentage"""
        if self.status == TaskStatus.COMPLETED:
            return 100
        elif self.status == TaskStatus.CANCELLED:
            return 0
        return self.progress
    
    @property
    def time_variance(self):
        """Calculate time variance (actual vs estimated)"""
        if not self.estimated_hours:
            return None
        actual = self.total_hours_tracked
        return ((actual - self.estimated_hours) / self.estimated_hours) * 100
    
    @property
    def days_remaining(self):
        """Calculate days remaining until due date"""
        if self.status == TaskStatus.COMPLETED:
            return 0
        delta = self.due_date - datetime.now().date()
        return delta.days
    
    def get_dependency_tasks(self):
        """Get task dependencies"""
        if not self.dependencies:
            return []
        return Task.query.filter(Task.id.in_(self.dependencies)).all()
    
    def can_start(self):
        """Check if task can be started (all dependencies completed)"""
        dependency_tasks = self.get_dependency_tasks()
        return all(task.status == TaskStatus.COMPLETED for task in dependency_tasks)
    
    def get_blocking_tasks(self):
        """Get tasks that are blocked by this task"""
        return Task.query.filter(Task.dependencies.contains([self.id])).all()
    
    def complete_task(self):
        """Mark task as completed"""
        self.status = TaskStatus.COMPLETED
        self.progress = 100
        self.completed_date = datetime.utcnow()
        
        # Update project progress
        if self.project:
            self.project.update_progress()
    
    def to_dict(self):
        """Convert task to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'task_code': self.task_code,
            'status': self.status.value if self.status else None,
            'priority': self.priority.value if self.priority else None,
            'category': self.category,
            'estimated_hours': self.estimated_hours,
            'actual_hours': self.actual_hours,
            'total_hours_tracked': self.total_hours_tracked,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'completed_date': self.completed_date.isoformat() if self.completed_date else None,
            'progress': self.progress,
            'completion_percentage': self.completion_percentage,
            'parent_task_id': self.parent_task_id,
            'dependencies': self.dependencies or [],
            'tags': self.tags or [],
            'files': self.files or [],
            'links': self.links or [],
            'project_id': self.project_id,
            'project_name': self.project.name if self.project else None,
            'assignee_id': self.assignee_id,
            'assignee_name': f"{self.assignee.first_name} {self.assignee.last_name}" if self.assignee else None,
            'assignee_email': self.assignee.email if self.assignee else None,
            'created_by_id': self.created_by_id,
            'created_by_name': self.created_by.username if self.created_by else None,
            'is_overdue': self.is_overdue,
            'time_variance': self.time_variance,
            'can_start': self.can_start(),
            'subtasks_count': len(self.subtasks),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'days_remaining': self.days_remaining,
            'comments_count': self.comments.count(),
            'time_logs_count': self.time_logs.count()
        }
    
    def __repr__(self):
        return f'<Task {self.title}>' 

class TaskComment(db.Model):
    __tablename__ = 'task_comments'

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='task_comments')

    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'user_id': self.user_id,
            'user_name': self.user.username if self.user else None,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class TaskTimeLog(db.Model):
    __tablename__ = 'task_time_logs'

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    logged_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    hours = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    logged_at = db.Column(db.DateTime, default=datetime.utcnow)

    logged_by = db.relationship('User', backref='time_logs')

    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'logged_by_id': self.logged_by_id,
            'logged_by_name': self.logged_by.username if self.logged_by else None,
            'hours': self.hours,
            'description': self.description,
            'logged_at': self.logged_at.isoformat() if self.logged_at else None
        }

class TaskAssignment(db.Model):
    __tablename__ = 'task_assignments'

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    assigned_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    role = db.Column(db.String(50), default='assignee')  # assignee, reviewer, collaborator
    is_active = db.Column(db.Boolean, default=True)

    task = db.relationship('Task', backref='assignments')
    employee = db.relationship('Employee', backref='task_assignments')
    assigned_by = db.relationship('User', backref='task_assignments')

    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'employee_id': self.employee_id,
            'employee_name': f"{self.employee.first_name} {self.employee.last_name}" if self.employee else None,
            'assigned_by_id': self.assigned_by_id,
            'assigned_by_name': self.assigned_by.username if self.assigned_by else None,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'role': self.role,
            'is_active': self.is_active
        } 