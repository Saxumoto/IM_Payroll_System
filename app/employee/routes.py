# app/employee/routes.py

from flask import render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.employee import bp
from app.models.user import Payslip, PayrollRun, LeaveRequest, AttendanceLog, LeaveBalance 
from app import db
from .forms import LeaveRequestForm 
from datetime import datetime
from sqlalchemy import desc
from sqlalchemy.orm import joinedload
import pytz

def get_current_clock_status(employee_id):
    """Get the current clock status for an employee based on their most recent log entry."""
    # Use fresh query to avoid caching issues
    last_log = db.session.query(AttendanceLog)\
        .filter_by(employee_id=employee_id)\
        .order_by(desc(AttendanceLog.timestamp))\
        .first()
    if not last_log:
        return {'status': 'OUT', 'time': None}
    if last_log.event_type == 'IN':
        return {'status': 'IN', 'time': last_log.timestamp}
    return {'status': 'OUT', 'time': last_log.timestamp}

@bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'Admin':
        return redirect(url_for('main.admin_dashboard'))
    employee = current_user.employee
    if employee is None:
        flash('Employee profile not found. Please contact HR.', 'danger')
        return redirect(url_for('auth.signout'))
    clock_status = get_current_clock_status(employee.id)
    leave_balances = LeaveBalance.query.filter_by(employee_id=employee.id).all()
    return render_template('employee/dashboard.html', employee=employee, clock_status=clock_status, leave_balances=leave_balances)

@bp.route('/clock', methods=['POST'])
@login_required
def clock():
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
        
        # Refresh the session to ensure we get fresh data on next query
        db.session.expire_all()
        
        # Convert UTC to local time for display (default to Asia/Manila, can be configured)
        from flask import current_app
        tz_name = current_app.config.get('TIMEZONE', 'Asia/Manila')
        local_tz = pytz.timezone(tz_name) if tz_name != 'UTC' else pytz.UTC
        # Ensure timestamp is timezone-aware (assume UTC if naive)
        if new_log.timestamp.tzinfo is None:
            utc_time = pytz.UTC.localize(new_log.timestamp)
        else:
            utc_time = new_log.timestamp
        local_time = utc_time.astimezone(local_tz)
        flash(f"Successfully clocked {new_event_type.lower()} at {local_time.strftime('%b %d, %Y at %I:%M:%S %p')}.", 'success')
    except Exception as e:
        db.session.rollback()
        flash(f"Error processing clock action: {e}", 'danger')
    return redirect(url_for('employee.dashboard'))

@bp.route('/my_payslips')
@login_required
def my_payslips():
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
    employee = current_user.employee
    slip = db.session.get(Payslip, slip_id)
    if slip is None or slip.employee_id != employee.id:
        flash('Payslip not found or access denied.', 'danger')
        return redirect(url_for('employee.my_payslips'))
    return render_template('payslip_detail.html', slip=slip)

@bp.route('/file_leave', methods=['GET', 'POST'])
@login_required
def file_leave():
    form = LeaveRequestForm()
    if form.validate_on_submit():
        # --- FIX: Check for overlapping requests ---
        existing_leave = LeaveRequest.query.filter(
            LeaveRequest.employee_id == current_user.employee.id,
            LeaveRequest.status.in_(['Pending', 'Approved']),
            LeaveRequest.start_date <= form.end_date.data,
            LeaveRequest.end_date >= form.start_date.data
        ).first()

        if existing_leave:
            flash(f'Error: You already have a {existing_leave.status} leave request overlapping with these dates.', 'danger')
            return render_template('file_leave.html', form=form)
        
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
    all_requests = LeaveRequest.query.filter_by(employee_id=current_user.employee.id)\
        .order_by(LeaveRequest.requested_on.desc())\
        .all()
    return render_template('my_leave_history.html', all_requests=all_requests)