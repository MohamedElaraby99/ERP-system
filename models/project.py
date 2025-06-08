from datetime import datetime
from extensions import db
from sqlalchemy import func

# Association table for project team members
project_team = db.Table('project_team',
    db.Column('project_id', db.Integer, db.ForeignKey('projects.id'), primary_key=True),
    db.Column('employee_id', db.Integer, db.ForeignKey('employees.id'), primary_key=True)
)

class Project(db.Model):
    """Project model for managing software projects"""
    
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    project_code = db.Column(db.String(20), unique=True, nullable=False)
    
    # Project details
    status = db.Column(db.String(20), nullable=False, default='planning')  # planning, active, on_hold, completed, cancelled
    priority = db.Column(db.String(20), nullable=False, default='medium')  # low, medium, high, urgent
    category = db.Column(db.String(50))  # web_app, mobile_app, desktop_app, api, etc.
    
    # Dates
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    actual_start_date = db.Column(db.Date)
    actual_end_date = db.Column(db.Date)
    
    # Financial
    budget = db.Column(db.Numeric(12, 2))
    actual_cost = db.Column(db.Numeric(12, 2), default=0)
    hourly_rate = db.Column(db.Numeric(8, 2))
    
    # Progress
    progress = db.Column(db.Integer, default=0)  # 0-100
    estimated_hours = db.Column(db.Integer)
    actual_hours = db.Column(db.Integer, default=0)
    
    # Technical details
    technologies = db.Column(db.JSON)  # ['React', 'Python', 'PostgreSQL']
    repository_url = db.Column(db.String(500))
    staging_url = db.Column(db.String(500))
    production_url = db.Column(db.String(500))
    
    # Foreign keys
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    project_manager_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    client = db.relationship('Client', backref='projects')
    project_manager = db.relationship('Employee', backref='managed_projects', foreign_keys=[project_manager_id])
    team_members = db.relationship('Employee', secondary=project_team, backref='projects')
    tasks = db.relationship('Task', backref='project', cascade='all, delete-orphan')
    time_tracks = db.relationship('TimeTrack', backref='project', cascade='all, delete-orphan')
    expenses = db.relationship('Expense', backref='project', cascade='all, delete-orphan')
    invoices = db.relationship('Invoice', backref='project', cascade='all, delete-orphan')
    
    @property
    def total_hours_tracked(self):
        """Calculate total hours tracked for this project"""
        return db.session.query(func.sum(TimeTrack.hours)).filter_by(project_id=self.id).scalar() or 0
    
    @property
    def total_expenses(self):
        """Calculate total expenses for this project"""
        return db.session.query(func.sum(Expense.amount)).filter_by(project_id=self.id).scalar() or 0
    
    @property
    def completion_percentage(self):
        """Calculate completion percentage based on tasks"""
        if not self.tasks:
            return self.progress
        
        completed_tasks = sum(1 for task in self.tasks if task.status == 'completed')
        return int((completed_tasks / len(self.tasks)) * 100)
    
    @property
    def is_overdue(self):
        """Check if project is overdue"""
        if not self.end_date:
            return False
        return datetime.now().date() > self.end_date and self.status not in ['completed', 'cancelled']
    
    @property
    def is_over_budget(self):
        """Check if project is over budget"""
        if not self.budget:
            return False
        return self.actual_cost > self.budget
    
    def add_team_member(self, employee):
        """Add team member to project"""
        if employee not in self.team_members:
            self.team_members.append(employee)
    
    def remove_team_member(self, employee):
        """Remove team member from project"""
        if employee in self.team_members:
            self.team_members.remove(employee)
    
    def update_progress(self):
        """Update project progress based on tasks completion"""
        if self.tasks:
            completed_tasks = sum(1 for task in self.tasks if task.status == 'completed')
            self.progress = int((completed_tasks / len(self.tasks)) * 100)
        db.session.commit()
    
    def to_dict(self):
        """Convert project to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'project_code': self.project_code,
            'status': self.status,
            'priority': self.priority,
            'category': self.category,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'actual_start_date': self.actual_start_date.isoformat() if self.actual_start_date else None,
            'actual_end_date': self.actual_end_date.isoformat() if self.actual_end_date else None,
            'budget': float(self.budget) if self.budget else None,
            'actual_cost': float(self.actual_cost) if self.actual_cost else 0,
            'hourly_rate': float(self.hourly_rate) if self.hourly_rate else None,
            'progress': self.progress,
            'estimated_hours': self.estimated_hours,
            'actual_hours': self.actual_hours,
            'technologies': self.technologies or [],
            'repository_url': self.repository_url,
            'staging_url': self.staging_url,
            'production_url': self.production_url,
            'client_id': self.client_id,
            'client_name': self.client.name if self.client else None,
            'project_manager_id': self.project_manager_id,
            'project_manager_name': self.project_manager.full_name if self.project_manager else None,
            'team_members': [member.to_dict() for member in self.team_members],
            'total_hours_tracked': self.total_hours_tracked,
            'total_expenses': float(self.total_expenses) if self.total_expenses else 0,
            'completion_percentage': self.completion_percentage,
            'is_overdue': self.is_overdue,
            'is_over_budget': self.is_over_budget,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<Project {self.name}>' 