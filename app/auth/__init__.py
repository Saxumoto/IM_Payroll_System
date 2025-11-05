# app/__init__.py (Modified)

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager # <--- NEW IMPORT
from config import config

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager() # <--- NEW INSTANCE

# Set the view function for logging in (tells Flask-Login where the login page is)
login.login_view = 'auth.signin' 
# Optional: Set a message category for the default login message
login.login_message_category = 'warning' 

def create_app(config_name='default'):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])
    
    db.init_app(app)
    migrate.init_app(app, db, directory=app.config.get('MIGRATION_DIR'))
    login.init_app(app) # <--- INITIALIZE LOGIN

    # --- Register Blueprints ---
    from .auth import bp as auth_bp
    app.register_blueprint(auth_bp)
    
    from .main import bp as main_bp
    app.register_blueprint(main_bp)
    
    return app