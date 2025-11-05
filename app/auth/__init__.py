# app/models/user.py (Final Correction)

from app import db # Keep db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin 
from app import login # <--- Import 'login' via its definition in __init__.py

class User(UserMixin, db.Model): 
    # ... (rest of the class remains the same)

# User loader function for Flask-Login
@login.user_loader # <--- Use the imported 'login' instance here
def load_user(id):
    """Retrieves a user from the database given their ID."""
    return User.query.get(int(id))