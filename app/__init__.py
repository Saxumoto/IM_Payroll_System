# app/__init__.py
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager 
from config import config

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager() 

login.login_view = 'auth.signin' 
login.login_message_category = 'warning' 

@login.user_loader
def load_user(id):
    from app.models.user import User
    # Use session.get() instead of deprecated query.get() for SQLAlchemy 2.0+
    return db.session.get(User, int(id))

def create_app(config_name='default'):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])
    
    # Initialize app-specific configuration (logging, etc.)
    config[config_name].init_app(app)
    
    db.init_app(app)
    migrate.init_app(app, db, directory=app.config.get('MIGRATION_DIR'))
    login.init_app(app)
    
    # --- Register Blueprints ---
    from .auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    from .main import bp as main_bp
    app.register_blueprint(main_bp)

    from .hr import bp as hr_bp
    app.register_blueprint(hr_bp)

    from .payroll import bp as payroll_bp
    app.register_blueprint(payroll_bp)

    from .employee import bp as employee_bp
    app.register_blueprint(employee_bp)
    
    # --- NEW BLUEPRINT: Attendance ---
    from .attendance import bp as attendance_bp
    app.register_blueprint(attendance_bp)
    
    # --- Register Template Filters for Time Formatting ---
    from datetime import datetime
    import pytz
    
    @app.template_filter('localtime')
    def localtime_filter(dt, format='%b %d, %Y at %I:%M:%S %p'):
        """Convert UTC datetime to local time and format it."""
        if dt is None:
            return 'N/A'
        try:
            # Get timezone from config (default to Asia/Manila)
            tz_name = app.config.get('TIMEZONE', 'Asia/Manila')
            if tz_name == 'UTC':
                local_tz = pytz.UTC
            else:
                local_tz = pytz.timezone(tz_name)
            
            # If datetime is naive, assume it's UTC
            if dt.tzinfo is None:
                dt = pytz.UTC.localize(dt)
            
            # Convert to local timezone
            local_dt = dt.astimezone(local_tz)
            return local_dt.strftime(format)
        except Exception as e:
            # Fallback to original format if timezone conversion fails
            return dt.strftime(format) if isinstance(dt, datetime) else str(dt)
    
    @app.template_filter('datetime_format')
    def datetime_format_filter(dt, format='%b %d, %Y %I:%M %p'):
        """Format datetime with a default nice format."""
        if dt is None:
            return 'N/A'
        try:
            return dt.strftime(format)
        except:
            return str(dt)
    
    # --- Register Error Handlers ---
    from flask import render_template
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    return app