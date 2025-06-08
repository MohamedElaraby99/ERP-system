from datetime import datetime
from extensions import db

class Expense(db.Model):
    """Expense model for tracking project and company expenses"""
    
    __tablename__ = 'expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Basic Information
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), nullable=False)  # travel, equipment, software, training, etc.
    
    # Financial Details
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(3), default='SAR')
    tax_amount = db.Column(db.Numeric(12, 2), default=0)
    total_amount = db.Column(db.Numeric(12, 2))  # amount + tax
    
    # Date Information
    expense_date = db.Column(db.Date, nullable=False)
    
    # Status and Approval
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected, reimbursed
    is_reimbursable = db.Column(db.Boolean, default=True)
    is_billable_to_client = db.Column(db.Boolean, default=False)
    
    # Receipt and Documentation
    receipt_number = db.Column(db.String(100))
    vendor = db.Column(db.String(200))
    payment_method = db.Column(db.String(50))  # cash, credit_card, bank_transfer, etc.
    receipt_file = db.Column(db.String(500))  # File path for receipt image/PDF
    
    # Foreign Keys
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Approval Details
    approved_at = db.Column(db.DateTime)
    rejection_reason = db.Column(db.Text)
    reimbursed_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    employee = db.relationship('Employee', backref='expenses')
    approver = db.relationship('User', foreign_keys=[approved_by], backref='approved_expenses')
    
    def __init__(self, **kwargs):
        super(Expense, self).__init__(**kwargs)
        if not self.total_amount:
            self.total_amount = self.amount + (self.tax_amount or 0)
    
    @property
    def is_overdue_for_approval(self):
        """Check if expense is pending approval for too long (more than 7 days)"""
        if self.status != 'pending':
            return False
        return (datetime.utcnow() - self.created_at).days > 7
    
    @property
    def formatted_amount(self):
        """Get formatted amount with currency"""
        return f"{self.total_amount} {self.currency}"
    
    def approve(self, approver_id):
        """Approve expense"""
        self.status = 'approved'
        self.approved_by = approver_id
        self.approved_at = datetime.utcnow()
        
        # Update project actual cost if project-related
        if self.project:
            self.project.actual_cost = (self.project.actual_cost or 0) + self.total_amount
    
    def reject(self, approver_id, reason):
        """Reject expense"""
        self.status = 'rejected'
        self.approved_by = approver_id
        self.approved_at = datetime.utcnow()
        self.rejection_reason = reason
    
    def reimburse(self):
        """Mark expense as reimbursed"""
        if self.status == 'approved' and self.is_reimbursable:
            self.status = 'reimbursed'
            self.reimbursed_at = datetime.utcnow()
    
    def to_dict(self):
        """Convert expense to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'amount': float(self.amount),
            'currency': self.currency,
            'tax_amount': float(self.tax_amount or 0),
            'total_amount': float(self.total_amount),
            'formatted_amount': self.formatted_amount,
            'expense_date': self.expense_date.isoformat() if self.expense_date else None,
            'status': self.status,
            'is_reimbursable': self.is_reimbursable,
            'is_billable_to_client': self.is_billable_to_client,
            'receipt_number': self.receipt_number,
            'vendor': self.vendor,
            'payment_method': self.payment_method,
            'receipt_file': self.receipt_file,
            'project_id': self.project_id,
            'project_name': self.project.name if self.project else None,
            'employee_id': self.employee_id,
            'employee_name': self.employee.full_name if self.employee else None,
            'approved_by': self.approved_by,
            'approver_name': self.approver.full_name if self.approver else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'rejection_reason': self.rejection_reason,
            'reimbursed_at': self.reimbursed_at.isoformat() if self.reimbursed_at else None,
            'is_overdue_for_approval': self.is_overdue_for_approval,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<Expense {self.title} - {self.total_amount} {self.currency}>' 