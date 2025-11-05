# app/main/__init__.py

from flask import Blueprint

# Create a Blueprint instance named 'main'
bp = Blueprint('main', __name__, template_folder='templates')

# Import the routes to associate them with this blueprint
from . import routes

def create_app(config_name='default'):
    app = Flask(__name__, instance_relative_config=True)
    # ... (configuration and extension initialization remain the same)
    
    # --- Register Blueprints ---
    # Authentication Blueprint
    from .auth import bp as auth_bp
    app.register_blueprint(auth_bp)
    
    # Main Application Blueprint
    from .main import bp as main_bp
    app.register_blueprint(main_bp)
    
    return app