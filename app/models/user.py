# app/models/user.py (Final Corrected Code)

from app import db # Keep db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin 
from app import login # Correctly imports the 'login' instance from __init__.py

class User(UserMixin, db.Model): 
    """User model for authentication and role-based access control."""
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='Employee')
    
    # Relationship to be defined with Employee later
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username} - {self.role}>'

# User loader function for Flask-Login
@login.user_loader # Use the imported 'login' instance here
def load_user(id):
    """Retrieves a user from the database given their ID."""
    return User.query.get(int(id))