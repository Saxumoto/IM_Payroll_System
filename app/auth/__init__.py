# app/__init__.py (Modified)

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager 
from config import config

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager() 

# Set the view function for logging in
login.login_view = 'auth.signin' 
login.login_message_category = 'warning' 

# CRITICAL FIX: The user_loader callback MUST be defined where the login manager is initialized.
@login.user_loader
def load_user(id):
    """Retrieves a user from the database given their ID."""
    # Import model locally here to avoid circular dependency
    from app.models.user import User
    return User.query.get(int(id))

def create_app(config_name='default'):
    # ... (rest of the function remains the same)
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])
    
    db.init_app(app)
    migrate.init_app(app, db, directory=app.config.get('MIGRATION_DIR'))
    login.init_app(app) # INITIALIZE LOGIN

    # ... (rest of blueprint registration remains the same)
    
    return app