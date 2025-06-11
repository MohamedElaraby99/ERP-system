from datetime import datetime
from extensions import db
from sqlalchemy import func

# Association table for project team members
project_team = db.Table('project_team',
    db.Column('project_id', db.Integer, db.ForeignKey('projects.id'), primary_key=True),
    db.Column('employee_id', db.Integer, db.ForeignKey('employees.id'), primary_key=True)
)

# Association table for project clients (for subscription projects)
project_clients = db.Table('project_clients',
    db.Column('project_id', db.Integer, db.ForeignKey('projects.id'), primary_key=True),
    db.Column('client_id', db.Integer, db.ForeignKey('clients.id'), primary_key=True)
)

class Project(db.Model):
    """Enhanced Project model for managing software projects with subscription and one-time payment support"""
    
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    project_code = db.Column(db.String(20), unique=True, nullable=False)
    
    # Project type - NEW: subscription or onetime
    project_type = db.Column(db.String(20), nullable=False, default='onetime')  # subscription, onetime
    
    # Project details
    status = db.Column(db.String(20), nullable=False, default='planning')  # planning, active, on_hold, completed, cancelled
    priority = db.Column(db.String(20), nullable=False, default='medium')  # low, medium, high, urgent
    category = db.Column(db.String(50))  # web_app, mobile_app, desktop_app, api, etc.
    
    # Dates
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    actual_start_date = db.Column(db.Date)
    actual_end_date = db.Column(db.Date)
    
    # Financial - Enhanced for both project types
    budget = db.Column(db.Numeric(12, 2))  # For one-time projects
    actual_cost = db.Column(db.Numeric(12, 2), default=0)
    hourly_rate = db.Column(db.Numeric(8, 2))
    
    # NEW: Subscription project fields
    monthly_price = db.Column(db.Numeric(10, 2))  # Monthly subscription price per client
    subscriber_count = db.Column(db.Integer, default=0)  # Number of subscribers
    
    # NEW: One-time project fields
    total_amount = db.Column(db.Numeric(12, 2))  # Total project amount
    paid_amount = db.Column(db.Numeric(12, 2), default=0)  # Amount paid so far
    
    # Progress
    progress = db.Column(db.Integer, default=0)  # 0-100
    estimated_hours = db.Column(db.Integer)
    actual_hours = db.Column(db.Integer, default=0)
    
    # Technical details - Enhanced
    technologies = db.Column(db.Text)  # Comma-separated string: 'React, Node.js, MongoDB'
    repository_url = db.Column(db.String(500))
    staging_url = db.Column(db.String(500))
    production_url = db.Column(db.String(500))
    
    # Foreign keys
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'))  # For one-time projects
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    project_manager_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Enhanced Relationships - FIXED to avoid circular imports
    client = db.relationship('Client', backref='primary_projects', foreign_keys=[client_id])
    subscription_clients = db.relationship('Client', secondary=project_clients, backref='subscription_projects')
    project_manager = db.relationship('Employee', backref='managed_projects', foreign_keys=[project_manager_id])
    team_members = db.relationship('Employee', secondary=project_team, backref='projects')
    
    # Note: These relationships are commented out to avoid import issues
    # tasks = db.relationship('Task', backref='project', cascade='all, delete-orphan')
    # time_tracks = db.relationship('TimeTrack', backref='project', cascade='all, delete-orphan')
    # expenses = db.relationship('Expense', backref='project', cascade='all, delete-orphan')
    # invoices = db.relationship('Invoice', backref='project', cascade='all, delete-orphan')
    
    @property
    def monthly_revenue(self):
        """Calculate monthly revenue for subscription projects"""
        if self.project_type == 'subscription' and self.monthly_price:
            return float(self.monthly_price) * self.subscriber_count
        return 0
    
    @property
    def remaining_amount(self):
        """Calculate remaining amount for one-time projects"""
        if self.project_type == 'onetime' and self.total_amount:
            return float(self.total_amount) - float(self.paid_amount or 0)
        return 0
    
    @property
    def payment_percentage(self):
        """Calculate payment percentage for one-time projects"""
        if self.project_type == 'onetime' and self.total_amount and self.total_amount > 0:
            return int((float(self.paid_amount or 0) / float(self.total_amount)) * 100)
        return 0
    
    @property
    def all_clients(self):
        """Get all clients associated with this project"""
        if self.project_type == 'subscription':
            return list(self.subscription_clients)
        elif self.client:
            return [self.client]
        return []
    
    @property
    def total_hours_tracked(self):
        """Calculate total hours tracked for this project - FIXED"""
        try:
            # Dynamically import to avoid circular dependency
            from models.timetrack import TimeTrack
            return db.session.query(func.sum(TimeTrack.hours)).filter_by(project_id=self.id).scalar() or 0
        except (ImportError, Exception):
            return 0
    
    @property
    def total_expenses(self):
        """Calculate total expenses for this project - FIXED"""
        try:
            # Dynamically import to avoid circular dependency  
            from models.expense import Expense
            return db.session.query(func.sum(Expense.amount)).filter_by(project_id=self.id).scalar() or 0
        except (ImportError, Exception):
            return 0
    
    @property
    def completion_percentage(self):
        """Calculate completion percentage based on tasks - FIXED"""
        try:
            from models.task import Task
            tasks = Task.query.filter_by(project_id=self.id).all()
            if not tasks:
                return self.progress
            
            completed_tasks = sum(1 for task in tasks if task.status == 'completed')
            return int((completed_tasks / len(tasks)) * 100)
        except (ImportError, Exception):
            return self.progress
    
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
    
    def add_subscription_client(self, client):
        """Add client to subscription project"""
        if self.project_type == 'subscription' and client not in self.subscription_clients:
            self.subscription_clients.append(client)
            self.subscriber_count = len(self.subscription_clients)
    
    def remove_subscription_client(self, client):
        """Remove client from subscription project"""
        if self.project_type == 'subscription' and client in self.subscription_clients:
            self.subscription_clients.remove(client)
            self.subscriber_count = len(self.subscription_clients)
    
    def update_progress(self):
        """Update project progress based on tasks completion"""
        try:
            from models.task import Task
            tasks = Task.query.filter_by(project_id=self.id).all()
            if tasks:
                completed_tasks = sum(1 for task in tasks if task.status == 'completed')
                self.progress = int((completed_tasks / len(tasks)) * 100)
            db.session.commit()
        except (ImportError, Exception):
            pass
    
    def generate_project_code(self):
        """Generate unique project code"""
        if not self.project_code:
            prefix = 'SUB' if self.project_type == 'subscription' else 'ONE'
            count = Project.query.filter_by(project_type=self.project_type).count() + 1
            self.project_code = f"{prefix}-{count:04d}"
    
    def to_dict(self):
        """Convert project to dictionary with enhanced fields"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'project_code': self.project_code,
            'project_type': self.project_type,
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
            
            # Enhanced financial fields
            'monthly_price': float(self.monthly_price) if self.monthly_price else None,
            'subscriber_count': self.subscriber_count,
            'monthly_revenue': self.monthly_revenue,
            'total_amount': float(self.total_amount) if self.total_amount else None,
            'paid_amount': float(self.paid_amount) if self.paid_amount else 0,
            'remaining_amount': self.remaining_amount,
            'payment_percentage': self.payment_percentage,
            
            'progress': self.progress,
            'estimated_hours': self.estimated_hours,
            'actual_hours': self.actual_hours,
            'technologies': self.technologies,
            'repository_url': self.repository_url,
            'staging_url': self.staging_url,
            'production_url': self.production_url,
            'client_id': self.client_id,
            'created_by': self.created_by,
            'project_manager_id': self.project_manager_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            
            # Computed properties
            'completion_percentage': self.completion_percentage,
            'is_overdue': self.is_overdue,
            'is_over_budget': self.is_over_budget,
            'total_hours_tracked': self.total_hours_tracked,
            'total_expenses': self.total_expenses,
            'all_clients': [client.name if hasattr(client, 'name') else str(client) for client in self.all_clients]
        }
    
    def __repr__(self):
        return f'<Project {self.name} ({self.project_type})>' 