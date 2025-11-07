# app/employee/routes.py

from flask import render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.employee import bp
from app.models.user import Payslip, PayrollRun, LeaveRequest, AttendanceLog, LeaveBalance 
from app import db
from .forms import LeaveRequestForm 
from datetime import datetime
from sqlalchemy import desc
from sqlalchemy.orm import joinedload # <--- NEW IMPORT for eager loading

# Helper function to check if the user is currently clocked in
def get_current_clock_status(employee_id):
    """Checks the last attendance log to determine if the employee is currently clocked in."""
    last_log = AttendanceLog.query.filter_by(employee_id=employee_id)\
        .order_by(desc(AttendanceLog.timestamp)).first()
        
    # If no logs exist, status is OUT
    if not last_log:
        return {'status': 'OUT', 'time': None}
        
    # If last log was IN, status is IN
    if last_log.event_type == 'IN':
        return {'status': 'IN', 'time': last_log.timestamp}
    
    # If last log was OUT or ADJUST, status is OUT
    return {'status': 'OUT', 'time': last_log.timestamp}


@bp.route('/dashboard')
@login_required
def dashboard():
    """Renders the employee's personal dashboard."""
    
    # 1. Redirect Admin users away, as they don't have an employee profile
    if current_user.role == 'Admin':
        return redirect(url_for('main.admin_dashboard'))
        
    employee = current_user.employee
    
    # 2. Check if the authenticated non-admin user actually has an associated employee record
    if employee is None:
        flash('Employee profile not found. Please contact HR.', 'danger')
        return redirect(url_for('auth.signout'))
        
    # --- NEW: Get Clock Status ---
    clock_status = get_current_clock_status(employee.id)
    
    # --- NEW: Get Leave Balances (list of LeaveBalance objects for this employee) ---
    leave_balances = LeaveBalance.query.filter_by(employee_id=employee.id).all()

    # This path is 'employee/dashboard.html' (which is correct for your file structure)
    return render_template('employee/dashboard.html', employee=employee, clock_status=clock_status, leave_balances=leave_balances)


@bp.route('/clock', methods=['POST'])
@login_required
def clock():
    """Handles the employee's clock in/out action."""
    employee = current_user.employee
    
    if not employee:
        flash('Cannot clock in/out: Employee profile missing.', 'danger')
        return redirect(url_for('employee.dashboard'))
        
    status = get_current_clock_status(employee.id)
    new_event_type = 'OUT' if status['status'] == 'IN' else 'IN'
    
    try:
        new_log = AttendanceLog(
            employee_id=employee.id,
            timestamp=datetime.utcnow(),
            event_type=new_event_type,
            source='Employee Self-Service'
        )
        db.session.add(new_log)
        db.session.commit()
        
        # Display time in local timezone format (simplified by using strftime)
        flash(f"Successfully clocked {new_event_type.lower()} at {new_log.timestamp.strftime('%Y-%m-%d %I:%M:%S %p')} UTC.", 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error processing clock action: {e}", 'danger')
        
    return redirect(url_for('employee.dashboard'))


@bp.route('/my_payslips')
@login_required
def my_payslips():
    """Renders a list of the employee's own past payslips."""
    
    # --- CRITICAL FIX: Eager Load PayrollRun and Filter Corrupted Data ---
    payslips = Payslip.query.filter_by(employee_id=current_user.employee.id)\
        .options(joinedload(Payslip.payroll_run))\
        .join(PayrollRun, Payslip.payroll_run_id == PayrollRun.id)\
        .filter(
            PayrollRun.pay_period_start != None,
            PayrollRun.pay_period_end != None,
            PayrollRun.pay_date != None
        ) \
        .order_by(PayrollRun.pay_date.desc())\
        .all()
        
    return render_template('my_payslips.html', payslips=payslips)


@bp.route('/my_payslips/<int:slip_id>')
@login_required
def view_payslip_detail(slip_id):
    """Shows the detailed breakdown of a single payslip."""
    employee = current_user.employee
    
    slip = db.session.get(Payslip, slip_id)
    
    # Security check: Ensure the payslip belongs to the logged-in employee
    if slip is None or slip.employee_id != employee.id:
        flash('Payslip not found or access denied.', 'danger')
        return redirect(url_for('employee.my_payslips'))
        
    return render_template('payslip_detail.html', slip=slip)


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