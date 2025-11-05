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
    return User.query.get(int(id))

def create_app(config_name='default'):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])
    
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

    # --- NEW BLUEPRINT ---
    from .employee import bp as employee_bp
    app.register_blueprint(employee_bp)

    return app