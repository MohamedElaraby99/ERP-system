from datetime import datetime, timedelta
from extensions import db
from sqlalchemy import func

class ClientSubscription(db.Model):
    """Client subscription model for managing monthly software subscriptions"""
    
    __tablename__ = 'client_subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign keys
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    
    # Subscription details
    subscription_plan = db.Column(db.String(50), nullable=False)  # basic, premium, enterprise
    monthly_price = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default='SAR')
    
    # Subscription period
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)  # Null for indefinite subscriptions
    trial_end_date = db.Column(db.Date)  # Free trial period
    
    # Status and billing
    status = db.Column(db.String(20), nullable=False, default='active')  # active, paused, cancelled, expired
    billing_cycle = db.Column(db.String(20), default='monthly')  # monthly, quarterly, yearly
    next_billing_date = db.Column(db.Date, nullable=False)
    payment_method = db.Column(db.String(50))  # credit_card, bank_transfer, check
    
    # Features and limits
    user_limit = db.Column(db.Integer)  # Maximum users allowed
    storage_limit_gb = db.Column(db.Integer)  # Storage limit in GB
    features_enabled = db.Column(db.JSON)  # List of enabled features
    custom_domain = db.Column(db.String(100))  # Custom domain if applicable
    
    # Payment tracking
    total_paid = db.Column(db.Numeric(12, 2), default=0)
    last_payment_date = db.Column(db.Date)
    last_payment_amount = db.Column(db.Numeric(10, 2))
    failed_payment_count = db.Column(db.Integer, default=0)
    
    # Notes and metadata
    notes = db.Column(db.Text)
    contract_reference = db.Column(db.String(100))
    renewal_reminder_sent = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    client = db.relationship('Client', backref='subscriptions')
    project = db.relationship('Project', backref='client_subscriptions')
    
    @property
    def is_trial(self):
        """Check if subscription is in trial period"""
        if self.trial_end_date:
            return datetime.now().date() <= self.trial_end_date
        return False
    
    @property
    def is_expired(self):
        """Check if subscription is expired"""
        if self.end_date:
            return datetime.now().date() > self.end_date
        return False
    
    @property
    def is_overdue(self):
        """Check if payment is overdue"""
        return datetime.now().date() > self.next_billing_date and self.status == 'active'
    
    @property
    def days_until_billing(self):
        """Calculate days until next billing"""
        delta = self.next_billing_date - datetime.now().date()
        return delta.days
    
    @property
    def subscription_duration_months(self):
        """Calculate subscription duration in months"""
        if not self.start_date:
            return 0
        
        end_date = self.end_date or datetime.now().date()
        delta = end_date - self.start_date
        return delta.days // 30
    
    @property
    def total_revenue(self):
        """Calculate total revenue from this subscription"""
        return float(self.total_paid or 0)
    
    @property
    def monthly_revenue_projection(self):
        """Calculate monthly revenue projection"""
        if self.status == 'active':
            return float(self.monthly_price)
        return 0
    
    def calculate_next_billing_date(self):
        """Calculate next billing date based on billing cycle"""
        if self.billing_cycle == 'monthly':
            return self.next_billing_date + timedelta(days=30)
        elif self.billing_cycle == 'quarterly':
            return self.next_billing_date + timedelta(days=90)
        elif self.billing_cycle == 'yearly':
            return self.next_billing_date + timedelta(days=365)
        return self.next_billing_date
    
    def record_payment(self, amount, payment_date=None):
        """Record a payment for this subscription"""
        if payment_date is None:
            payment_date = datetime.now().date()
        
        self.last_payment_date = payment_date
        self.last_payment_amount = amount
        self.total_paid = (self.total_paid or 0) + amount
        self.failed_payment_count = 0
        self.next_billing_date = self.calculate_next_billing_date()
        
        # Reset status if was paused due to failed payments
        if self.status == 'paused':
            self.status = 'active'
    
    def record_failed_payment(self):
        """Record a failed payment attempt"""
        self.failed_payment_count += 1
        
        # Pause subscription after 3 failed attempts
        if self.failed_payment_count >= 3:
            self.status = 'paused'
    
    def cancel_subscription(self, reason=None):
        """Cancel the subscription"""
        self.status = 'cancelled'
        self.end_date = datetime.now().date()
        if reason:
            self.notes = f"Cancelled: {reason}"
    
    def reactivate_subscription(self):
        """Reactivate a cancelled or paused subscription"""
        if self.status in ['cancelled', 'paused']:
            self.status = 'active'
            self.failed_payment_count = 0
            # Set next billing date to today + billing cycle
            self.next_billing_date = datetime.now().date()
            self.next_billing_date = self.calculate_next_billing_date()
    
    def update_plan(self, new_plan, new_price):
        """Update subscription plan and price"""
        self.subscription_plan = new_plan
        self.monthly_price = new_price
        self.updated_at = datetime.utcnow()
    
    def to_dict(self):
        """Convert subscription to dictionary"""
        return {
            'id': self.id,
            'client_id': self.client_id,
            'project_id': self.project_id,
            'client_name': self.client.name if self.client else None,
            'project_name': self.project.name if self.project else None,
            'subscription_plan': self.subscription_plan,
            'monthly_price': float(self.monthly_price),
            'currency': self.currency,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'trial_end_date': self.trial_end_date.isoformat() if self.trial_end_date else None,
            'status': self.status,
            'billing_cycle': self.billing_cycle,
            'next_billing_date': self.next_billing_date.isoformat() if self.next_billing_date else None,
            'payment_method': self.payment_method,
            'user_limit': self.user_limit,
            'storage_limit_gb': self.storage_limit_gb,
            'features_enabled': self.features_enabled or [],
            'custom_domain': self.custom_domain,
            'total_paid': float(self.total_paid or 0),
            'last_payment_date': self.last_payment_date.isoformat() if self.last_payment_date else None,
            'last_payment_amount': float(self.last_payment_amount or 0),
            'failed_payment_count': self.failed_payment_count,
            'notes': self.notes,
            'contract_reference': self.contract_reference,
            'is_trial': self.is_trial,
            'is_expired': self.is_expired,
            'is_overdue': self.is_overdue,
            'days_until_billing': self.days_until_billing,
            'subscription_duration_months': self.subscription_duration_months,
            'total_revenue': self.total_revenue,
            'monthly_revenue_projection': self.monthly_revenue_projection,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<ClientSubscription {self.client.name if self.client else "Unknown"} -> {self.project.name if self.project else "Unknown"}>'


class SubscriptionPayment(db.Model):
    """Payment record for subscriptions"""
    
    __tablename__ = 'subscription_payments'
    
    id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('client_subscriptions.id'), nullable=False)
    
    # Payment details
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default='SAR')
    payment_date = db.Column(db.Date, nullable=False)
    payment_method = db.Column(db.String(50))
    
    # Status and references
    status = db.Column(db.String(20), default='completed')  # completed, failed, pending, refunded
    transaction_id = db.Column(db.String(100))
    invoice_number = db.Column(db.String(50))
    receipt_url = db.Column(db.String(500))
    
    # Billing period this payment covers
    billing_period_start = db.Column(db.Date)
    billing_period_end = db.Column(db.Date)
    
    # Notes and metadata
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscription = db.relationship('ClientSubscription', backref='payment_history')
    
    def to_dict(self):
        """Convert payment to dictionary"""
        return {
            'id': self.id,
            'subscription_id': self.subscription_id,
            'amount': float(self.amount),
            'currency': self.currency,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'payment_method': self.payment_method,
            'status': self.status,
            'transaction_id': self.transaction_id,
            'invoice_number': self.invoice_number,
            'receipt_url': self.receipt_url,
            'billing_period_start': self.billing_period_start.isoformat() if self.billing_period_start else None,
            'billing_period_end': self.billing_period_end.isoformat() if self.billing_period_end else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<SubscriptionPayment {self.amount} {self.currency} on {self.payment_date}>' 