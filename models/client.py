from datetime import datetime
from extensions import db

class Client(db.Model):
    """Client model for managing both company and individual clients"""
    
    __tablename__ = 'clients'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Client Type - NEW FIELD
    client_type = db.Column(db.String(20), nullable=False, default='company')  # 'company' or 'individual'
    
    # Basic Information
    name = db.Column(db.String(200), nullable=False)  # For individuals: full name, For companies: company name
    
    # Individual-specific fields
    first_name = db.Column(db.String(100))  # For individuals only
    last_name = db.Column(db.String(100))   # For individuals only
    national_id = db.Column(db.String(50))   # For individuals (national ID, passport, etc.)
    date_of_birth = db.Column(db.Date)       # For individuals only
    gender = db.Column(db.String(10))        # For individuals only
    
    # Company-specific fields
    company_name = db.Column(db.String(200))  # For companies only
    tax_number = db.Column(db.String(50))     # For companies only
    registration_number = db.Column(db.String(50))  # For companies only
    industry = db.Column(db.String(100))      # For companies only
    company_size = db.Column(db.String(50))   # For companies: startup, small, medium, large, enterprise
    
    # Common contact information
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    secondary_phone = db.Column(db.String(20))  # Additional phone number
    website = db.Column(db.String(200))  # More relevant for companies
    
    # Address Information
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    country = db.Column(db.String(100))
    postal_code = db.Column(db.String(20))
    
    # Contact Person (for companies only)
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
    
    # Relationships - commented out to avoid conflicts
    # Relationships are handled by other models' backref definitions
    
    @property
    def display_name(self):
        """Get appropriate display name based on client type"""
        if self.client_type == 'individual':
            if self.first_name and self.last_name:
                return f"{self.first_name} {self.last_name}"
            return self.name
        else:  # company
            return self.company_name or self.name
    
    @property
    def full_name(self):
        """Get full name for individuals or company name for companies"""
        return self.display_name
    
    @property
    def is_individual(self):
        """Check if client is an individual"""
        return self.client_type == 'individual'
    
    @property
    def is_company(self):
        """Check if client is a company"""
        return self.client_type == 'company'
    
    @property
    def total_project_value(self):
        """Calculate total value of all projects for this client"""
        # Return 0 for now to avoid database query issues
        return 0
    
    @property
    def active_projects_count(self):
        """Count active projects for this client"""
        # Return 0 for now to avoid relationship issues
        return 0
    
    @property
    def completed_projects_count(self):
        """Count completed projects for this client"""
        # Return 0 for now to avoid relationship issues
        return 0
    
    @property
    def outstanding_invoices(self):
        """Get unpaid invoices for this client"""
        # Return empty list for now to avoid relationship issues
        return []
    
    @property
    def outstanding_amount(self):
        """Calculate total outstanding amount"""
        # Return 0 for now to avoid calculation issues
        return 0
    
    def get_project_history(self):
        """Get chronological list of projects"""
        try:
            return sorted(self.primary_projects, key=lambda x: x.created_at, reverse=True)
        except:
            return []
    
    def to_dict(self):
        """Convert client to dictionary"""
        return {
            'id': self.id,
            'client_type': self.client_type,
            'name': self.name,
            'display_name': self.display_name,
            'full_name': self.full_name,
            
            # Individual fields
            'first_name': self.first_name,
            'last_name': self.last_name,
            'national_id': self.national_id,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'gender': self.gender,
            
            # Company fields
            'company_name': self.company_name,
            'tax_number': self.tax_number,
            'registration_number': self.registration_number,
            'industry': self.industry,
            'company_size': self.company_size,
            
            # Common fields
            'email': self.email,
            'phone': self.phone,
            'secondary_phone': self.secondary_phone,
            'website': self.website,
            'address': self.address,
            'city': self.city,
            'country': self.country,
            'postal_code': self.postal_code,
            
            # Contact person (for companies)
            'contact_person': self.contact_person,
            'contact_position': self.contact_position,
            'contact_phone': self.contact_phone,
            'contact_email': self.contact_email,
            
            # Business details
            'status': self.status,
            'source': self.source,
            'priority': self.priority,
            'credit_limit': float(self.credit_limit) if self.credit_limit else None,
            'currency': self.currency,
            'payment_terms': self.payment_terms,
            'notes': self.notes,
            'tags': self.tags or [],
            
            # Timestamps
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_contact_date': self.last_contact_date.isoformat() if self.last_contact_date else None
        }
    
    def __repr__(self):
        return f'<Client {self.display_name} ({self.client_type})>' 