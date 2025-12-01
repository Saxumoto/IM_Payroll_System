# app/__init__.py

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