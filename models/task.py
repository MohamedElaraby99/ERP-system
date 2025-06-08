from datetime import datetime
from extensions import db

class Task(db.Model):
    """Task model for project task management"""
    
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    task_code = db.Column(db.String(20), unique=True)
    
    # Task Details
    status = db.Column(db.String(20), default='todo')  # todo, in_progress, review, completed, cancelled
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, urgent
    category = db.Column(db.String(50))  # development, design, testing, documentation, meeting
    
    # Time Management
    estimated_hours = db.Column(db.Float)
    actual_hours = db.Column(db.Float, default=0)
    start_date = db.Column(db.Date)
    due_date = db.Column(db.Date)
    completed_date = db.Column(db.Date)
    
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
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    parent_task = db.relationship('Task', remote_side=[id], backref='subtasks')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_tasks')
    time_tracks = db.relationship('TimeTrack', backref='task', cascade='all, delete-orphan')
    
    @property
    def is_overdue(self):
        """Check if task is overdue"""
        if not self.due_date or self.status in ['completed', 'cancelled']:
            return False
        return datetime.now().date() > self.due_date
    
    @property
    def total_hours_tracked(self):
        """Calculate total hours tracked for this task"""
        from sqlalchemy import func
        return db.session.query(func.sum(TimeTrack.hours)).filter_by(task_id=self.id).scalar() or 0
    
    @property
    def completion_percentage(self):
        """Calculate completion percentage"""
        if self.status == 'completed':
            return 100
        elif self.status == 'cancelled':
            return 0
        return self.progress
    
    @property
    def time_variance(self):
        """Calculate time variance (actual vs estimated)"""
        if not self.estimated_hours:
            return None
        actual = self.total_hours_tracked
        return ((actual - self.estimated_hours) / self.estimated_hours) * 100
    
    def get_dependency_tasks(self):
        """Get task dependencies"""
        if not self.dependencies:
            return []
        return Task.query.filter(Task.id.in_(self.dependencies)).all()
    
    def can_start(self):
        """Check if task can be started (all dependencies completed)"""
        dependency_tasks = self.get_dependency_tasks()
        return all(task.status == 'completed' for task in dependency_tasks)
    
    def get_blocking_tasks(self):
        """Get tasks that are blocked by this task"""
        return Task.query.filter(Task.dependencies.contains([self.id])).all()
    
    def complete_task(self):
        """Mark task as completed"""
        self.status = 'completed'
        self.progress = 100
        self.completed_date = datetime.now().date()
        
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
            'status': self.status,
            'priority': self.priority,
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
            'assigned_to': self.assigned_to,
            'assigned_to_name': self.assignee.full_name if self.assignee else None,
            'created_by': self.created_by,
            'created_by_name': self.creator.full_name if self.creator else None,
            'is_overdue': self.is_overdue,
            'time_variance': self.time_variance,
            'can_start': self.can_start(),
            'subtasks_count': len(self.subtasks),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<Task {self.title}>' 