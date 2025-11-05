# app/main/routes.py (Modified)

from flask import render_template, redirect, url_for, flash
from flask_login import login_required, current_user # <--- NEW IMPORTS
from app.main import bp
# ... (other imports remain the same)

@bp.route('/')
@bp.route('/welcome')
def welcome():
    """Renders the public-facing Welcome Page."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('welcome.html')


@bp.route('/dashboard')
@login_required # <--- NEW DECORATOR: Requires user to be logged in
def dashboard():
    """Renders the main Dashboard Page."""
    
    # ... (dashboard logic remains the same)
    
    # Pass user information to the template for personalization
    dashboard_data = {
        'total_employees': User.query.count(),
        'total_salary': '$0',
        'average_salary': '$0',
        'recent_payments': 0,
        'username': current_user.username
    }

    return render_template('main/dashboard.html', data=dashboard_data)