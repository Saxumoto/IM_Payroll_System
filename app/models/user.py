# app/models/user.py (Modified)

from app import db, login # <--- Import 'login' from the factory
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin # <--- NEW IMPORT

class User(UserMixin, db.Model): # <--- Inherit from UserMixin
    """User model for authentication and role-based access control."""
    __tablename__ = 'user'
    
    # ... (rest of model attributes remain the same)

    # ... (set_password and check_password methods remain the same)

    def __repr__(self):
        return f'<User {self.username} - {self.role}>'

# User loader function for Flask-Login
@login.user_loader
def load_user(id):
    """Retrieves a user from the database given their ID."""
    return User.query.get(int(id))