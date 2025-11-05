# app/hr/routes.py

from flask import render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_required, current_user
from app.hr import bp
from app import db
from app.models.user import User, Employee, LeaveRequest
from functools import wraps
from app.hr.forms import AddEmployeeForm, EditEmployeeForm

# File Upload Imports
import os
import uuid
from werkzeug.utils import secure_filename

# --- HELPER FUNCTION ---
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
                return redirect(url_for('main.dashboard'))
        return wrapper
    return decorator


@bp.route('/employee/add', methods=['GET', 'POST'])
@role_required('Payroll_Admin')
def add_employee():
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
            return redirect(url_for('main.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while saving the employee data: {e}', 'danger')
    
    # Renders 'app/hr/templates/add_employee.html'
    return render_template('add_employee.html', form=form)


@bp.route('/manage_staff')
@role_required('Payroll_Admin')
def manage_staff():
    employees = db.session.query(Employee).join(User, Employee.user_id == User.id)\
        .filter(User.role != 'Admin')\
        .all()
    # Renders 'app/hr/templates/manage_staff.html'
    return render_template('manage_staff.html', employees=employees)


@bp.route('/employee/edit/<int:id>', methods=['GET', 'POST'])
@role_required('Payroll_Admin')
def edit_employee(id):
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
        return redirect(url_for('hr.manage_staff'))
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
def delete_employee(id):
    employee = db.session.get(Employee, id)
    if not employee:
        flash('Error: Employee not found.', 'danger')
        return redirect(url_for('hr.manage_staff'))
    try:
        user = db.session.get(User, employee.user_id)
        if employee.photo_filename != 'default.png':
            photo_path = os.path.join(current_app.config['UPLOAD_FOLDER'], employee.photo_filename)
            if os.path.exists(photo_path):
                os.remove(photo_path)
        db.session.delete(employee)
        if user:
            db.session.delete(user)
        db.session.commit()
        flash(f'Employee {employee.last_name} ({employee.employee_id_number}) and their login have been deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while deleting the employee: {e}', 'danger')
    return redirect(url_for('hr.manage_staff'))


@bp.route('/leave_requests')
@role_required('Payroll_Admin')
def manage_leave_requests():
    """Shows a full list of all leave requests (pending, approved, etc)."""
    all_requests = LeaveRequest.query.join(Employee, LeaveRequest.employee_id == Employee.id)\
        .order_by(LeaveRequest.status.asc(), LeaveRequest.requested_on.desc())\
        .all()
        
    # --- TEMPLATE PATH FIX ---
    # Renders 'app/hr/templates/manage_leave_requests.html'
    return render_template('manage_leave_requests.html', all_requests=all_requests)


@bp.route('/leave_requests/update/<int:request_id>/<string:new_status>', methods=['POST'])
@role_required('Payroll_Admin')
def update_leave_status(request_id, new_status):
    """Approves or Rejects a leave request."""
    leave_request = db.session.get(LeaveRequest, request_id)
    
    if not leave_request:
        flash('Leave request not found.', 'danger')
        return redirect(url_for('hr.manage_leave_requests'))
    if new_status not in ['Approved', 'Rejected']:
        flash('Invalid status.', 'danger')
        return redirect(url_for('hr.manage_leave_requests'))

    try:
        leave_request.status = new_status
        db.session.commit()
        flash(f'Leave request has been {new_status.lower()}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {e}', 'danger')
        
    return redirect(url_for('hr.manage_leave_requests'))