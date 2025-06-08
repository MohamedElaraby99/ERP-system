from datetime import datetime
from extensions import db

class Client(db.Model):
    """Client model for managing company clients"""
    
    __tablename__ = 'clients'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Basic Information
    name = db.Column(db.String(200), nullable=False)
    company_name = db.Column(db.String(200))
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    website = db.Column(db.String(200))
    
    # Address Information
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    country = db.Column(db.String(100))
    postal_code = db.Column(db.String(20))
    
    # Business Information
    industry = db.Column(db.String(100))
    company_size = db.Column(db.String(50))  # startup, small, medium, large, enterprise
    tax_number = db.Column(db.String(50))
    registration_number = db.Column(db.String(50))
    
    # Contact Person
    contact_person = db.Column(db.String(100))
    contact_position = db.Column(db.String(100))
    contact_phone = db.Column(db.String(20))
    contact_email = db.Column(db.String(120))
    
    # Business Details
    status = db.Column(db.String(20), default='active')  # active, inactive, potential, lost
    source = db.Column(db.String(50))  # referral, website, marketing, social_media, etc.
    priority = db.Column(db.String(20), default='medium')  # low, medium, high
    
    # Financial Information
    credit_limit = db.Column(db.Numeric(12, 2))
    currency = db.Column(db.String(3), default='SAR')
    payment_terms = db.Column(db.Integer, default=30)  # days
    
    # Relationships and Communication
    notes = db.Column(db.Text)
    tags = db.Column(db.JSON)  # ['enterprise', 'long-term', 'strategic']
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_contact_date = db.Column(db.DateTime)
    
    @property
    def total_project_value(self):
        """Calculate total value of all projects for this client"""
        from sqlalchemy import func
        return db.session.query(func.sum(Project.budget)).filter_by(client_id=self.id).scalar() or 0
    
    @property
    def active_projects_count(self):
        """Count active projects for this client"""
        return len([p for p in self.projects if p.status in ['planning', 'active']])
    
    @property
    def completed_projects_count(self):
        """Count completed projects for this client"""
        return len([p for p in self.projects if p.status == 'completed'])
    
    @property
    def outstanding_invoices(self):
        """Get unpaid invoices for this client"""
        unpaid_invoices = []
        for project in self.projects:
            unpaid_invoices.extend([inv for inv in project.invoices if inv.status in ['draft', 'sent']])
        return unpaid_invoices
    
    @property
    def outstanding_amount(self):
        """Calculate total outstanding amount"""
        return sum(inv.total_amount for inv in self.outstanding_invoices)
    
    def get_project_history(self):
        """Get chronological list of projects"""
        return sorted(self.projects, key=lambda x: x.created_at, reverse=True)
    
    def to_dict(self):
        """Convert client to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'company_name': self.company_name,
            'email': self.email,
            'phone': self.phone,
            'website': self.website,
            'address': self.address,
            'city': self.city,
            'country': self.country,
            'postal_code': self.postal_code,
            'industry': self.industry,
            'company_size': self.company_size,
            'tax_number': self.tax_number,
            'registration_number': self.registration_number,
            'contact_person': self.contact_person,
            'contact_position': self.contact_position,
            'contact_phone': self.contact_phone,
            'contact_email': self.contact_email,
            'status': self.status,
            'source': self.source,
            'priority': self.priority,
            'credit_limit': float(self.credit_limit) if self.credit_limit else None,
            'currency': self.currency,
            'payment_terms': self.payment_terms,
            'notes': self.notes,
            'tags': self.tags or [],
            'total_project_value': float(self.total_project_value),
            'active_projects_count': self.active_projects_count,
            'completed_projects_count': self.completed_projects_count,
            'outstanding_amount': float(self.outstanding_amount),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_contact_date': self.last_contact_date.isoformat() if self.last_contact_date else None
        }
    
    def __repr__(self):
        return f'<Client {self.name}>' 