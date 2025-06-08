from datetime import datetime, time, timedelta
from extensions import db

class TimeTrack(db.Model):
    """Time tracking model for logging work hours"""
    
    __tablename__ = 'time_tracks'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Time Details
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    hours = db.Column(db.Float, nullable=False)  # Total hours worked
    
    # Work Details
    description = db.Column(db.Text, nullable=False)
    activity_type = db.Column(db.String(50))  # development, meeting, testing, documentation, etc.
    
    # Status
    status = db.Column(db.String(20), default='logged')  # logged, approved, rejected, billed
    is_billable = db.Column(db.Boolean, default=True)
    
    # Location and Method
    location = db.Column(db.String(50))  # office, home, client_site, etc.
    work_method = db.Column(db.String(20))  # on_site, remote
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'))
    
    # Approval
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_at = db.Column(db.DateTime)
    rejection_reason = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    approver = db.relationship('User', foreign_keys=[approved_by], backref='approved_time_tracks')
    
    @property
    def calculated_hours(self):
        """Calculate hours from start and end time"""
        if not self.start_time or not self.end_time:
            return self.hours
        
        start_datetime = datetime.combine(self.date, self.start_time)
        end_datetime = datetime.combine(self.date, self.end_time)
        
        # Handle overnight work (end time next day)
        if end_datetime < start_datetime:
            end_datetime = datetime.combine(self.date + timedelta(days=1), self.end_time)
        
        duration = end_datetime - start_datetime
        return round(duration.total_seconds() / 3600, 2)
    
    @property
    def is_overtime(self):
        """Check if this is overtime work (more than 8 hours in a day for the user)"""
        daily_hours = db.session.query(db.func.sum(TimeTrack.hours)).filter(
            TimeTrack.user_id == self.user_id,
            TimeTrack.date == self.date
        ).scalar() or 0
        return daily_hours > 8
    
    @property
    def billable_amount(self):
        """Calculate billable amount if hourly rate is available"""
        if not self.is_billable:
            return 0
        
        # Get hourly rate from project or employee
        hourly_rate = None
        if self.project and self.project.hourly_rate:
            hourly_rate = self.project.hourly_rate
        elif self.employee and self.employee.hourly_rate:
            hourly_rate = self.employee.hourly_rate
        
        if hourly_rate:
            return float(self.hours * hourly_rate)
        return 0
    
    def approve(self, approver_id):
        """Approve time entry"""
        self.status = 'approved'
        self.approved_by = approver_id
        self.approved_at = datetime.utcnow()
        
        # Update task actual hours
        if self.task:
            self.task.actual_hours = (self.task.actual_hours or 0) + self.hours
    
    def reject(self, approver_id, reason):
        """Reject time entry"""
        self.status = 'rejected'
        self.approved_by = approver_id
        self.approved_at = datetime.utcnow()
        self.rejection_reason = reason
    
    def to_dict(self):
        """Convert time track to dictionary"""
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'hours': self.hours,
            'calculated_hours': self.calculated_hours,
            'description': self.description,
            'activity_type': self.activity_type,
            'status': self.status,
            'is_billable': self.is_billable,
            'location': self.location,
            'work_method': self.work_method,
            'user_id': self.user_id,
            'user_name': self.user.full_name if self.user else None,
            'employee_id': self.employee_id,
            'employee_name': self.employee.full_name if self.employee else None,
            'project_id': self.project_id,
            'project_name': self.project.name if self.project else None,
            'task_id': self.task_id,
            'task_title': self.task.title if self.task else None,
            'approved_by': self.approved_by,
            'approver_name': self.approver.full_name if self.approver else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'rejection_reason': self.rejection_reason,
            'is_overtime': self.is_overtime,
            'billable_amount': self.billable_amount,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<TimeTrack {self.date} - {self.hours}h>' 