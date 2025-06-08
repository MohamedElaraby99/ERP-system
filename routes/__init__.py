from .auth import auth_bp
from .projects import projects_bp
from .employees import employees_bp
from .clients import clients_bp
from .tasks import tasks_bp
from .timetrack import timetrack_bp
from .expenses import expenses_bp
from .invoices import invoices_bp
from .dashboard import dashboard_bp

def register_blueprints(app):
    """Register all blueprints with the Flask app"""
    
    # API version prefix
    api_prefix = '/api/v1'
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix=f'{api_prefix}/auth')
    app.register_blueprint(projects_bp, url_prefix=f'{api_prefix}/projects')
    app.register_blueprint(employees_bp, url_prefix=f'{api_prefix}/employees')
    app.register_blueprint(clients_bp, url_prefix=f'{api_prefix}/clients')
    app.register_blueprint(tasks_bp, url_prefix=f'{api_prefix}/tasks')
    app.register_blueprint(timetrack_bp, url_prefix=f'{api_prefix}/timetrack')
    app.register_blueprint(expenses_bp, url_prefix=f'{api_prefix}/expenses')
    app.register_blueprint(invoices_bp, url_prefix=f'{api_prefix}/invoices')
    app.register_blueprint(dashboard_bp, url_prefix=f'{api_prefix}/dashboard') 