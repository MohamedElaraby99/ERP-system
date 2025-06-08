from datetime import datetime, timedelta
from extensions import db

class Invoice(db.Model):
    """Invoice model for billing clients"""
    
    __tablename__ = 'invoices'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Invoice Details
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Dates
    issue_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    due_date = db.Column(db.Date, nullable=False)
    paid_date = db.Column(db.Date)
    
    # Financial Details
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)
    tax_rate = db.Column(db.Numeric(5, 2), default=15)  # VAT percentage
    tax_amount = db.Column(db.Numeric(12, 2))
    discount_amount = db.Column(db.Numeric(12, 2), default=0)
    total_amount = db.Column(db.Numeric(12, 2), nullable=False)
    paid_amount = db.Column(db.Numeric(12, 2), default=0)
    currency = db.Column(db.String(3), default='SAR')
    
    # Status
    status = db.Column(db.String(20), default='draft')  # draft, sent, paid, overdue, cancelled
    
    # Invoice Items (stored as JSON for flexibility)
    items = db.Column(db.JSON)  # [{'description': '', 'quantity': 1, 'rate': 100, 'amount': 100}]
    
    # Payment Information
    payment_method = db.Column(db.String(50))
    payment_reference = db.Column(db.String(100))
    bank_details = db.Column(db.JSON)
    
    # Notes and Terms
    notes = db.Column(db.Text)
    terms_and_conditions = db.Column(db.Text)
    
    # Foreign Keys
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    sent_at = db.Column(db.DateTime)
    
    # Relationships
    client = db.relationship('Client', backref='invoices')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_invoices')
    
    def __init__(self, **kwargs):
        super(Invoice, self).__init__(**kwargs)
        if not self.due_date and self.issue_date:
            # Default to 30 days from issue date
            payment_terms = 30
            if self.client and self.client.payment_terms:
                payment_terms = self.client.payment_terms
            self.due_date = self.issue_date + timedelta(days=payment_terms)
        
        if not self.tax_amount and self.subtotal and self.tax_rate:
            self.tax_amount = (self.subtotal * self.tax_rate) / 100
        
        if not self.total_amount:
            self.total_amount = self.subtotal + (self.tax_amount or 0) - (self.discount_amount or 0)
    
    @property
    def is_overdue(self):
        """Check if invoice is overdue"""
        if self.status in ['paid', 'cancelled']:
            return False
        return datetime.now().date() > self.due_date
    
    @property
    def days_overdue(self):
        """Calculate days overdue"""
        if not self.is_overdue:
            return 0
        return (datetime.now().date() - self.due_date).days
    
    @property
    def outstanding_amount(self):
        """Calculate outstanding amount"""
        return self.total_amount - (self.paid_amount or 0)
    
    @property
    def is_fully_paid(self):
        """Check if invoice is fully paid"""
        return self.outstanding_amount <= 0
    
    @property
    def payment_percentage(self):
        """Calculate payment percentage"""
        if self.total_amount == 0:
            return 0
        return (self.paid_amount / self.total_amount) * 100
    
    def generate_invoice_number(self):
        """Generate unique invoice number"""
        current_year = datetime.now().year
        
        # Count invoices this year
        count = db.session.query(Invoice).filter(
            db.extract('year', Invoice.created_at) == current_year
        ).count()
        
        self.invoice_number = f"INV-{current_year}-{count + 1:04d}"
    
    def add_item(self, description, quantity=1, rate=0, amount=None):
        """Add item to invoice"""
        if not self.items:
            self.items = []
        
        if amount is None:
            amount = quantity * rate
        
        item = {
            'description': description,
            'quantity': quantity,
            'rate': float(rate),
            'amount': float(amount)
        }
        
        self.items.append(item)
        self.recalculate_totals()
    
    def recalculate_totals(self):
        """Recalculate invoice totals"""
        if not self.items:
            self.subtotal = 0
        else:
            self.subtotal = sum(item['amount'] for item in self.items)
        
        self.tax_amount = (self.subtotal * (self.tax_rate or 0)) / 100
        self.total_amount = self.subtotal + (self.tax_amount or 0) - (self.discount_amount or 0)
    
    def mark_as_sent(self):
        """Mark invoice as sent"""
        self.status = 'sent'
        self.sent_at = datetime.utcnow()
    
    def record_payment(self, amount, payment_method=None, reference=None):
        """Record payment for invoice"""
        self.paid_amount = (self.paid_amount or 0) + amount
        
        if payment_method:
            self.payment_method = payment_method
        
        if reference:
            self.payment_reference = reference
        
        if self.is_fully_paid:
            self.status = 'paid'
            self.paid_date = datetime.now().date()
        
        # Update project actual cost
        if self.project:
            self.project.actual_cost = (self.project.actual_cost or 0) - amount
    
    def to_dict(self):
        """Convert invoice to dictionary"""
        return {
            'id': self.id,
            'invoice_number': self.invoice_number,
            'title': self.title,
            'description': self.description,
            'issue_date': self.issue_date.isoformat() if self.issue_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'paid_date': self.paid_date.isoformat() if self.paid_date else None,
            'subtotal': float(self.subtotal),
            'tax_rate': float(self.tax_rate or 0),
            'tax_amount': float(self.tax_amount or 0),
            'discount_amount': float(self.discount_amount or 0),
            'total_amount': float(self.total_amount),
            'paid_amount': float(self.paid_amount or 0),
            'outstanding_amount': float(self.outstanding_amount),
            'currency': self.currency,
            'status': self.status,
            'items': self.items or [],
            'payment_method': self.payment_method,
            'payment_reference': self.payment_reference,
            'bank_details': self.bank_details,
            'notes': self.notes,
            'terms_and_conditions': self.terms_and_conditions,
            'project_id': self.project_id,
            'project_name': self.project.name if self.project else None,
            'client_id': self.client_id,
            'client_name': self.client.name if self.client else None,
            'created_by': self.created_by,
            'creator_name': self.creator.full_name if self.creator else None,
            'is_overdue': self.is_overdue,
            'days_overdue': self.days_overdue,
            'is_fully_paid': self.is_fully_paid,
            'payment_percentage': self.payment_percentage,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None
        }
    
    def __repr__(self):
        return f'<Invoice {self.invoice_number} - {self.total_amount} {self.currency}>' 