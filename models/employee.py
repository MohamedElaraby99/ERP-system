from datetime import datetime
from extensions import db

class Employee(db.Model):
    """Employee model for managing company employees"""
    
    __tablename__ = 'employees'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(20), unique=True, nullable=False)
    
    # Personal Information
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    date_of_birth = db.Column(db.Date)
    national_id = db.Column(db.String(20))
    
    # Employment Information
    position = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(50), nullable=False)
    hire_date = db.Column(db.Date, nullable=False)
    employment_type = db.Column(db.String(20), default='full_time')  # full_time, part_time, contract, intern
    status = db.Column(db.String(20), default='active')  # active, inactive, vacation, terminated
    
    # Salary Information
    salary = db.Column(db.Numeric(10, 2))
    hourly_rate = db.Column(db.Numeric(8, 2))
    currency = db.Column(db.String(3), default='SAR')
    
    # Skills and Qualifications
    skills = db.Column(db.JSON)  # ['Python', 'React', 'SQL']
    education = db.Column(db.Text)
    certifications = db.Column(db.JSON)
    languages = db.Column(db.JSON)  # [{'language': 'Arabic', 'level': 'Native'}]
    
    # Emergency Contact
    emergency_contact_name = db.Column(db.String(100))
    emergency_contact_phone = db.Column(db.String(20))
    emergency_contact_relation = db.Column(db.String(50))
    
    # Banking Information
    bank_name = db.Column(db.String(100))
    bank_account = db.Column(db.String(50))
    iban = db.Column(db.String(34))
    
    # Performance
    performance_rating = db.Column(db.Float)  # 1-5 scale
    last_performance_review = db.Column(db.Date)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True)
    manager_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    manager = db.relationship('Employee', remote_side=[id], backref='subordinates')
    time_tracks = db.relationship('TimeTrack', backref='employee', cascade='all, delete-orphan')
    
    @property
    def full_name(self):
        """Get employee's full name"""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def age(self):
        """Calculate employee's age"""
        if not self.date_of_birth:
            return None
        today = datetime.now().date()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
    
    @property
    def years_of_service(self):
        """Calculate years of service"""
        if not self.hire_date:
            return None
        today = datetime.now().date()
        return today.year - self.hire_date.year - ((today.month, today.day) < (self.hire_date.month, self.hire_date.day))
    
    def get_current_projects(self):
        """Get employee's current projects"""
        try:
            # This will be implemented when project-employee relationship is added
            return []
        except:
            return []
    
    def get_total_hours_this_month(self):
        """Get total hours tracked this month"""
        try:
            from sqlalchemy import func, extract
            from models.timetrack import TimeTrack
            today = datetime.now()
            return db.session.query(func.sum(TimeTrack.hours)).filter(
                TimeTrack.employee_id == self.id,
                extract('year', TimeTrack.date) == today.year,
                extract('month', TimeTrack.date) == today.month
            ).scalar() or 0
        except:
            return 0
    
    def to_dict(self):
        """Convert employee to dictionary"""
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'age': self.age,
            'national_id': self.national_id,
            'position': self.position,
            'department': self.department,
            'hire_date': self.hire_date.isoformat() if self.hire_date else None,
            'years_of_service': self.years_of_service,
            'employment_type': self.employment_type,
            'status': self.status,
            'salary': float(self.salary) if self.salary else None,
            'hourly_rate': float(self.hourly_rate) if self.hourly_rate else None,
            'currency': self.currency,
            'skills': self.skills or [],
            'education': self.education,
            'certifications': self.certifications or [],
            'languages': self.languages or [],
            'emergency_contact_name': self.emergency_contact_name,
            'emergency_contact_phone': self.emergency_contact_phone,
            'emergency_contact_relation': self.emergency_contact_relation,
            'bank_name': self.bank_name,
            'bank_account': self.bank_account,
            'iban': self.iban,
            'performance_rating': self.performance_rating,
            'last_performance_review': self.last_performance_review.isoformat() if self.last_performance_review else None,
            'manager_id': self.manager_id,
            'manager_name': self.manager.full_name if self.manager else None,
            'user_id': self.user_id,
            'user': {
                'id': self.user.id,
                'email': self.user.email,
                'username': self.user.username,
                'role': self.user.role,
                'is_active': self.user.is_active,
                'is_verified': self.user.is_verified,
                'last_login': self.user.last_login.isoformat() if self.user.last_login else None
            } if self.user_id and self.user else None,
            'current_projects': 0,  # Will be calculated separately
            'total_hours_this_month': 0,  # Will be calculated separately
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<Employee {self.full_name}>' 