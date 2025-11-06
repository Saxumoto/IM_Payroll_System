# app/hr/routes.py

from flask import render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_required, current_user
from app.hr import bp
from app import db
from app.models.user import User, Employee, LeaveRequest, LeaveBalance, AuditLog
from functools import wraps
from app.hr.forms import AddEmployeeForm, EditEmployeeForm, LeaveBalanceForm, PasswordResetForm
from datetime import date
from decimal import Decimal

# File Upload Imports
import os
import uuid
from werkzeug.utils import secure_filename

# --- AUDIT LOG HELPER FUNCTION ---
def log_admin_action(action, details):
    """Records a critical administrative action in the AuditLog."""
    log = AuditLog(
        user_id=current_user.id,
        action=action,
        details=details
    )
    db.session.add(log)
    # Note: Commit is handled by the calling route's try/except block

def calculate_leave_days(start_date, end_date):
    """Calculates the number of full days between two dates, inclusive."""
    if start_date is None or end_date is None:
        return 0
    # Calculate difference in days and add 1 (to include the start day)
    return (end_date - start_date).days + 1

def save_picture(form_picture):
    random_hex = uuid.uuid4().hex
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.config['UPLOAD_FOLDER'], picture_fn)
    form_picture.save(picture_path)
    return picture_fn

# --- DECORATOR ---
def role_required(role):
    def decorator(f):
        @login_required
        @wraps(f) 
        def wrapper(*args, **kwargs):
            if current_user.is_authenticated and current_user.role in (role, 'Admin'):
                return f(*args, **kwargs)
            else:
                flash('Access denied: You do not have permission to view this page.', 'danger')
                return redirect(url_for('main.admin_dashboard'))
        return wrapper
    return decorator


@bp.route('/employee/add', methods=['GET', 'POST'])
@role_required('Payroll_Admin')
def add_new_employee():
    form = AddEmployeeForm()
    if form.validate_on_submit():
        photo_filename = 'default.png'
        if form.photo.data:
            photo_filename = save_picture(form.photo.data)
        if User.query.filter_by(username=form.email.data).first():
            flash('Error: A user with this email/username already exists.', 'danger')
            return render_template('add_employee.html', form=form)
        if Employee.query.filter_by(employee_id_number=form.employee_id_number.data).first():
            flash('Error: An employee with this ID number already exists.', 'danger')
            return render_template('add_employee.html', form=form)
        try:
            user = User(username=form.email.data, role='Employee', full_name=f"{form.first_name.data} {form.last_name.data}")
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.flush() 
            employee = Employee(
                user_id=user.id,
                photo_filename=photo_filename,
                employee_id_number=form.employee_id_number.data,
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                position=form.position.data,
                date_hired=form.date_hired.data,
                salary_rate=form.salary_rate.data,
                status=form.status.data,
                tin=form.tin.data,
                sss_num=form.sss_num.data,
                philhealth_num=form.philhealth_num.data,
                pagibig_num=form.pagibig_num.data,
                bank_account_num=form.bank_account_num.data
            )
            db.session.add(employee)
            db.session.commit()
            flash(f'Employee {employee.last_name} ({employee.employee_id_number}) added successfully!', 'success')
            return redirect(url_for('main.admin_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while saving the employee data: {e}', 'danger')
    
    # Renders 'app/hr/templates/add_employee.html'
    return render_template('add_employee.html', form=form)


@bp.route('/manage_staff')
@role_required('Payroll_Admin')
def manage_all_staff():
    """Shows a full list of all employee records."""
    employees = db.session.query(Employee).join(User, Employee.user_id == User.id)\
        .filter(User.role != 'Admin')\
        .all()
    # Renders 'app/hr/templates/manage_staff.html'
    return render_template('manage_staff.html', employees=employees)

# --- NEW ROUTE: Password Reset Utility ---
@bp.route('/employee/reset_password/<int:id>', methods=['GET', 'POST'])
@role_required('Admin') # Only Admin role can reset passwords
def reset_employee_password(id):
    employee = db.session.get(Employee, id)
    if not employee:
        flash('Employee not found.', 'danger')
        return redirect(url_for('hr.manage_all_staff'))
    
    user = db.session.get(User, employee.user_id)
    if not user:
        flash('User account not found for this employee.', 'danger')
        return redirect(url_for('hr.manage_all_staff'))

    form = PasswordResetForm()
    
    if form.validate_on_submit():
        try:
            user.set_password(form.new_password.data)
            # --- AUDIT LOGGING ---
            log_admin_action(
                action='PASSWORD_RESET',
                details=f"Reset password for Employee ID: {employee.employee_id_number} ({employee.user.username})"
            )
            db.session.commit()
            flash(f"Password for {employee.first_name} {employee.last_name} has been successfully reset.", 'success')
            return redirect(url_for('hr.manage_all_staff'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error resetting password: {e}", 'danger')
    
    return render_template('reset_password.html', form=form, employee=employee)


@bp.route('/employee/edit/<int:id>', methods=['GET', 'POST'])
@role_required('Payroll_Admin')
def edit_staff_member(id):
    employee = db.session.get(Employee, id)
    if not employee:
        abort(404) 
    form = EditEmployeeForm() 
    if form.validate_on_submit():
        if form.photo.data:
            if employee.photo_filename != 'default.png':
                old_photo_path = os.path.join(current_app.config['UPLOAD_FOLDER'], employee.photo_filename)
                if os.path.exists(old_photo_path):
                    os.remove(old_photo_path)
            employee.photo_filename = save_picture(form.photo.data)
        employee.employee_id_number = form.employee_id_number.data
        employee.first_name = form.first_name.data
        employee.last_name = form.last_name.data
        # --- SYNTAX ERROR FIX WAS HERE ---
        employee.position = form.position.data 
        employee.date_hired = form.date_hired.data
        employee.salary_rate = form.salary_rate.data
        employee.status = form.status.data
        employee.tin = form.tin.data
        employee.sss_num = form.sss_num.data
        employee.philhealth_num = form.philhealth_num.data
        employee.pagibig_num = form.pagibig_num.data
        employee.bank_account_num = form.bank_account_num.data
        db.session.commit() 
        flash(f'Employee {employee.last_name} ({employee.employee_id_number}) updated successfully!', 'success')
        return redirect(url_for('hr.manage_all_staff'))
    elif request.method == 'GET':
        form.employee_id_number.data = employee.employee_id_number
        form.first_name.data = employee.first_name
        form.last_name.data = employee.last_name
        form.position.data = employee.position
        form.date_hired.data = employee.date_hired
        form.salary_rate.data = employee.salary_rate
        form.status.data = employee.status
        form.tin.data = employee.tin
        form.sss_num.data = employee.sss_num
        form.philhealth_num.data = employee.philhealth_num
        form.pagibig_num.data = employee.pagibig_num
        form.bank_account_num.data = employee.bank_account_num
    
    # Renders 'app/hr/templates/edit_employee.html'
    return render_template('edit_employee.html', form=form, employee=employee)


@bp.route('/employee/delete/<int:id>', methods=['POST'])
@role_required('Payroll_Admin')
def delete_staff_member(id):
    employee = db.session.get(Employee, id)
    if not employee:
        flash('Error: Employee not found.', 'danger')
        return redirect(url_for('hr.manage_all_staff'))
    
    # Pre-fetch data for the audit log
    employee_id_num = employee.employee_id_number
    employee_last_name = employee.last_name

    try:
        user = db.session.get(User, employee.user_id)
        if employee.photo_filename != 'default.png':
            photo_path = os.path.join(current_app.config['UPLOAD_FOLDER'], employee.photo_filename)
            if os.path.exists(photo_path):
                os.remove(photo_path)
                
        # --- AUDIT LOGGING ---
        log_admin_action(
            action='DELETE_EMPLOYEE',
            details=f"Deleted employee record and user account for ID: {employee_id_num} ({employee_last_name})."
        )
        
        db.session.delete(employee)
        if user:
            db.session.delete(user)
        db.session.commit()
        flash(f'Employee {employee_last_name} ({employee_id_num}) and their login have been deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while deleting the employee: {e}', 'danger')
    return redirect(url_for('hr.manage_all_staff'))


@bp.route('/leave_requests')
@role_required('Payroll_Admin')
def manage_all_leave_requests():
    """Shows a full list of all leave requests (pending, approved, etc)."""
    all_requests = LeaveRequest.query.join(Employee, LeaveRequest.employee_id == Employee.id)\
        .order_by(LeaveRequest.status.asc(), LeaveRequest.requested_on.desc())\
        .all()
        
    # --- TEMPLATE PATH FIX ---
    # Renders 'app/hr/templates/manage_leave_requests.html'
    return render_template('manage_leave_requests.html', all_requests=all_requests)


@bp.route('/leave_requests/update/<int:request_id>/<string:new_status>', methods=['POST'])
@role_required('Payroll_Admin')
def update_leave_request_final_status(request_id, new_status):
    """Approves or Rejects a leave request and updates the balance."""
    leave_request = db.session.get(LeaveRequest, request_id)
    
    if not leave_request:
        flash('Leave request not found.', 'danger')
        return redirect(url_for('hr.manage_all_leave_requests'))
    if new_status not in ['Approved', 'Rejected']:
        flash('Invalid status.', 'danger')
        return redirect(url_for('hr.manage_all_leave_requests'))

    try:
        details_log = f"Status changed to {new_status} for Leave ID #{leave_request.id} ({leave_request.leave_type}). Employee: {leave_request.employee.last_name}."
        
        # --- CRITICAL NEW LOGIC: Deduct Balance on Approval ---
        if new_status == 'Approved':
            
            leave_days = calculate_leave_days(leave_request.start_date, leave_request.end_date)
            
            # Find the employee's leave balance record for this leave type
            balance = LeaveBalance.query.filter_by(
                employee_id=leave_request.employee_id,
                leave_type=leave_request.leave_type
            ).first()

            if not balance:
                flash(f"Error: No balance found for {leave_request.leave_type}. Cannot approve.", 'danger')
                return redirect(url_for('hr.manage_all_leave_requests'))

            # Check for sufficient remaining balance
            if balance.remaining < leave_days:
                flash(f"Error: Insufficient balance ({balance.remaining} days remaining). Cannot approve.", 'danger')
                return redirect(url_for('hr.manage_all_leave_requests'))
            
            # Deduct the used days
            balance.used += Decimal(leave_days)
            db.session.add(balance)
            
            details_log += f" Deducted {leave_days} days. New used balance: {balance.used}."


        # --- Update Request Status ---
        leave_request.status = new_status
        
        # --- AUDIT LOGGING ---
        log_admin_action(
            action='UPDATE_LEAVE_STATUS',
            details=details_log
        )
        
        db.session.commit()
        flash(f'Leave request has been {new_status.lower()}.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {e}', 'danger')
        
    return redirect(url_for('hr.manage_all_leave_requests'))


# --- NEW ROUTES for Leave Balance Management ---

@bp.route('/leave_balances')
@role_required('Payroll_Admin')
def manage_leave_balances():
    """Shows all employees' leave balances."""
    # Fetch employees and eagerly load their balances for display
    employees = Employee.query.options(db.joinedload(Employee.leave_balances)).all()
    
    return render_template('manage_leave_balances.html', employees=employees)


@bp.route('/leave_balances/edit/<int:employee_id>/<string:leave_type>', methods=['GET', 'POST'])
@role_required('Payroll_Admin')
def edit_leave_balance(employee_id, leave_type):
    """Edits or creates a specific leave balance record for an employee."""
    employee = db.session.get(Employee, employee_id)
    if not employee:
        flash('Employee not found.', 'danger')
        return redirect(url_for('hr.manage_leave_balances'))
        
    balance = LeaveBalance.query.filter_by(employee_id=employee_id, leave_type=leave_type).first()
    
    # Initialize form. If balance exists, pass the object for pre-population.
    form = LeaveBalanceForm(obj=balance)
    
    # Manually set the leave_type field to the current type and disable it
    form.leave_type.data = leave_type
    
    # Set context for the form template
    form.employee_id.data = employee.employee_id_number 

    if form.validate_on_submit():
        try:
            if not balance:
                # Create new record if one doesn't exist
                balance = LeaveBalance(
                    employee_id=employee_id,
                    leave_type=leave_type
                )
                
            balance.entitlement = form.entitlement.data
            balance.used = form.used.data
            
            # --- AUDIT LOGGING ---
            log_admin_action(
                action='UPDATE_LEAVE_BALANCE',
                details=f"Updated {leave_type} balance for Employee ID: {employee.employee_id_number}. Entitlement: {balance.entitlement}, Used: {balance.used}"
            )
            
            db.session.add(balance)
            db.session.commit()
            
            flash(f"Leave balance for {employee.first_name} ({leave_type}) updated successfully.", 'success')
            return redirect(url_for('hr.manage_leave_balances'))
            
        except Exception as e:
            db.session.rollback()
            flash(f"Error saving leave balance: {e}", 'danger')
            
    return render_template('edit_leave_balance.html', form=form, employee=employee, leave_type=leave_type)