# app/main/routes.py

from flask import render_template, redirect, url_for, flash, current_app, send_from_directory, abort
from flask_login import login_required, current_user
from app.main import bp
from app.models.user import User, Employee, LeaveRequest, AuditLog # Import AuditLog
from app import db
from sqlalchemy import func
import os

@bp.route('/')
@bp.route('/welcome')
def welcome():
    if current_user.is_authenticated:
        if current_user.role == 'Admin':
            return redirect(url_for('main.admin_dashboard'))
        # FIX: Only redirect to employee dashboard if an employee profile exists.
        elif current_user.employee:
            return redirect(url_for('employee.dashboard'))
    return render_template('welcome.html')


@bp.route('/dashboard')
@login_required
def admin_dashboard(): # RENAMED from dashboard()
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

    # FIX: Explicitly use 'dashboard.html' path for TemplateNotFound fix.
    return render_template('dashboard.html', data=dashboard_data)


@bp.route('/uploads/profile_pics/<filename>')
@login_required
def get_uploaded_file(filename):
    """Securely serves files from the upload folder."""
    from werkzeug.utils import secure_filename
    
    # Sanitize filename to prevent path traversal
    safe_filename = secure_filename(filename)
    if not safe_filename or safe_filename != filename:
        abort(404)
    
    # Validate file extension
    _, ext = os.path.splitext(safe_filename)
    allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg', 'gif'})
    if ext.lower().lstrip('.') not in allowed_extensions:
        abort(404)
    
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], safe_filename)


# --- NEW ROUTE: View Audit Logs ---
@bp.route('/audit_logs')
@login_required
def view_audit_logs():
    """Shows all administrative actions tracked in the Audit Log."""
    if current_user.role != 'Admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.admin_dashboard'))
        
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).all()
    
    return render_template('audit_logs.html', logs=logs)

# --- NEW ROUTE: Delete Audit Logs Utility ---
@bp.route('/audit_logs/delete_all', methods=['POST'])
@login_required
def delete_all_audit_logs():
    """Deletes all entries in the Audit Log table."""
    if current_user.role != 'Admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.view_audit_logs'))

    try:
        num_deleted = db.session.query(AuditLog).delete()
        db.session.commit()
        flash(f'Successfully deleted {num_deleted} audit log entries.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while deleting audit logs: {e}', 'danger')

    return redirect(url_for('main.view_audit_logs'))

@bp.route('/make-me-admin/<email>')
def make_me_admin(email):
    """
    Quick admin promotion route for initial setup.
    WARNING: Remove or secure this route in production!
    """
    try:
        # Find the user by the email you registered with
        user = User.query.filter_by(username=email).first()
        
        if not user:
            flash(f'User {email} not found! Make sure you registered first.', 'danger')
            return redirect(url_for('auth.register'))
        
        # Check if already admin
        if user.role == 'Admin':
            flash(f'User {email} is already an Admin!', 'info')
            return redirect(url_for('auth.signin'))
        
        # Force their role to Admin
        user.role = 'Admin'
        db.session.commit()
        
        flash(f'SUCCESS! {email} is now an Admin. Please sign in.', 'success')
        return redirect(url_for('auth.signin'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error promoting user to Admin: {str(e)}', 'danger')
        return redirect(url_for('main.welcome'))