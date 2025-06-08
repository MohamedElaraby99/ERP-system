from datetime import datetime
from extensions import db, bcrypt
from flask_jwt_extended import create_access_token
from sqlalchemy.ext.hybrid import hybrid_property

class User(db.Model):
    """User model for authentication and authorization"""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    _password_hash = db.Column('password_hash', db.String(128), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20))
    avatar = db.Column(db.String(200))
    
    # Role and permissions
    role = db.Column(db.String(20), nullable=False, default='employee')  # admin, manager, employee
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    employee = db.relationship('Employee', backref='user', uselist=False, cascade='all, delete-orphan')
    created_projects = db.relationship('Project', backref='creator', foreign_keys='Project.created_by')
    assigned_tasks = db.relationship('Task', backref='assignee', foreign_keys='Task.assigned_to')
    time_tracks = db.relationship('TimeTrack', backref='user', foreign_keys='TimeTrack.user_id', cascade='all, delete-orphan')
    
    @hybrid_property
    def password(self):
        """Password property (write-only)"""
        raise AttributeError('Password is not readable')
    
    @password.setter
    def password(self, password):
        """Set password hash"""
        self._password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        return bcrypt.check_password_hash(self._password_hash, password)
    
    @property
    def full_name(self):
        """Get user's full name"""
        return f"{self.first_name} {self.last_name}"
    
    def generate_tokens(self):
        """Generate access and refresh tokens"""
        access_token = create_access_token(identity=self.id)
        return {'access_token': access_token}
    
    def has_permission(self, permission):
        """Check if user has specific permission"""
        permissions = {
            'admin': ['read', 'write', 'delete', 'manage_users', 'manage_settings'],
            'manager': ['read', 'write', 'delete', 'manage_projects'],
            'employee': ['read', 'write']
        }
        return permission in permissions.get(self.role, [])
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'phone': self.phone,
            'avatar': self.avatar,
            'role': self.role,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
    
    def __repr__(self):
        return f'<User {self.username}>' 