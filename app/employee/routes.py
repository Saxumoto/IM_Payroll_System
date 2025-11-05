# app/employee/routes.py

from flask import render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.employee import bp
from app.models.user import Payslip, PayrollRun, LeaveRequest 
from app import db
from .forms import LeaveRequestForm 

@bp.route('/dashboard')
@login_required
def dashboard():
    """Renders the employee's personal dashboard."""
    employee = current_user.employee
    
    # This path is 'employee/dashboard.html' (which is correct for your file structure)
    return render_template('employee/dashboard.html', employee=employee)


@bp.route('/my_payslips')
@login_required
def my_payslips():
    """Renders a list of the employee's own past payslips."""
    
    payslips = Payslip.query.filter_by(employee_id=current_user.employee.id)\
        .join(PayrollRun, Payslip.payroll_run_id == PayrollRun.id)\
        .order_by(PayrollRun.pay_date.desc())\
        .all()
        
    # --- THIS IS THE FIX (Change 1 of 2) ---
    # Removed the 'employee/' prefix
    # This will find 'app/employee/templates/my_payslips.html'
    return render_template('my_payslips.html', payslips=payslips)


@bp.route('/file_leave', methods=['GET', 'POST'])
@login_required
def file_leave():
    """Shows the form for an employee to file a new leave request."""
    form = LeaveRequestForm()
    
    if form.validate_on_submit():
        try:
            new_request = LeaveRequest(
                employee_id=current_user.employee.id,
                leave_type=form.leave_type.data,
                start_date=form.start_date.data,
                end_date=form.end_date.data,
                reason=form.reason.data,
                status='Pending'
            )
            db.session.add(new_request)
            db.session.commit()
            flash('Leave request submitted successfully.', 'success')
            return redirect(url_for('employee.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {e}', 'danger')

    # --- THIS IS THE FIX (Change 2 of 2) ---
    # Removed the 'employee/' prefix
    # This will find 'app/employee/templates/file_leave.html'
    return render_template('file_leave.html', form=form)


@bp.route('/my_leave_history')
@login_required
def my_leave_history():
    """Shows a list of the employee's own past leave requests."""
    
    all_requests = LeaveRequest.query.filter_by(employee_id=current_user.employee.id)\
        .order_by(LeaveRequest.requested_on.desc())\
        .all()
        
    # This path is correct
    return render_template('my_leave_history.html', all_requests=all_requests)