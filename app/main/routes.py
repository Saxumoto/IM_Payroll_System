# app/main/routes.py

from flask import render_template, redirect, url_for, flash, current_app, send_from_directory
from flask_login import login_required, current_user
from app.main import bp
from app.models.user import User, Employee, LeaveRequest # Import LeaveRequest
from app import db
from sqlalchemy import func
import os

@bp.route('/')
@bp.route('/welcome')
def welcome():
    if current_user.is_authenticated:
        if current_user.role == 'Admin':
            return redirect(url_for('main.dashboard'))
        else:
            return redirect(url_for('employee.dashboard'))
    return render_template('welcome.html')


@bp.route('/dashboard')
@login_required
def dashboard():
    """Renders the main (Admin) Dashboard Page."""
    if current_user.role != 'Admin':
        return redirect(url_for('employee.dashboard'))
        
    active_employees = Employee.query.filter_by(status='Active')
    total_salary_query = active_employees.with_entities(func.sum(Employee.salary_rate)).scalar()
    total_monthly_salary = total_salary_query if total_salary_query else 0
    avg_salary_query = active_employees.with_entities(func.avg(Employee.salary_rate)).scalar()
    average_monthly_salary = avg_salary_query if avg_salary_query else 0
    employee_count = active_employees.count()
    
    recent_hires = Employee.query.order_by(Employee.date_hired.desc()).limit(5).all()
    
    pending_leave_requests = LeaveRequest.query.filter_by(status='Pending').order_by(LeaveRequest.requested_on).all()
    
    dashboard_data = {
        'total_employees': employee_count,
        'total_salary': total_monthly_salary,
        'average_salary': average_monthly_salary,
        'recent_payments': 0, 
        'username': current_user.full_name,
        'recent_hires': recent_hires,
        'pending_leave_requests': pending_leave_requests
    }

    # --- THIS IS THE FIX ---
    # We remove the 'main/' prefix. It will now correctly
    # find 'app/main/templates/dashboard.html'
    return render_template('dashboard.html', data=dashboard_data)


@bp.route('/uploads/profile_pics/<filename>')
@login_required
def get_uploaded_file(filename):
    """Securely serves files from the upload folder."""
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)