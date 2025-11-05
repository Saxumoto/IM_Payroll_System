# app/auth/routes.py (Modified)

from flask import render_template, redirect, url_for, request, flash
from flask_login import current_user, login_user, logout_user, login_required # <--- NEW IMPORTS
from app.auth import bp
from app.models.user import User
from app import db

# ... (register function remains the same for now)

@bp.route('/signin', methods=['GET', 'POST'])
def signin():
    """Handles the Sign In Form Page."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard')) # Redirect if already logged in

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=email).first()
        
        if user and user.check_password(password):
            login_user(user, remember=False) # Log the user in
            return redirect(url_for('main.dashboard'))
        
        flash('Invalid email or password.', 'danger')
        return render_template('auth/signin.html')
        
    return render_template('auth/signin.html')


@bp.route('/signout')
def signout():
    logout_user()
    flash('You have been signed out.', 'info')
    return redirect(url_for('main.welcome'))