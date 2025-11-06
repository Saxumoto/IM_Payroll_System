# app/attendance/routes.py

from flask import render_template, redirect, url_for, flash, request, abort
from app.attendance import bp
from app import db
from app.models.user import Employee, AttendanceLog, EmployeeSchedule 
from app.hr.routes import role_required # Import the decorator
from app.hr.routes import log_admin_action # NEW IMPORT
from .forms import EmployeeScheduleForm, ManualAttendanceLogForm, EditAttendanceLogForm
from datetime import datetime, time, date 
from sqlalchemy import func
from decimal import Decimal

# --- Schedule Management ---

@bp.route('/schedule', methods=['GET'])
@role_required('Payroll_Admin')
def manage_schedules():
    """Shows a list of employees with their current schedules."""
    # Fetch all employees and eager-load their schedule data
    employees = Employee.query.outerjoin(EmployeeSchedule).all()
    
    # FIX: Using simple filename. Template must be in app/attendance/templates/
    return render_template('manage_schedules.html', employees=employees)


@bp.route('/schedule/edit/<int:employee_id>', methods=['GET', 'POST'])
@role_required('Payroll_Admin')
def edit_schedule(employee_id):
    """Edits or creates a schedule for a single employee."""
    employee = db.session.get(Employee, employee_id)
    if not employee:
        flash('Employee not found.', 'danger')
        return redirect(url_for('attendance.manage_schedules'))
        
    # Query the existing schedule
    schedule = EmployeeSchedule.query.filter_by(employee_id=employee_id).first()
    form = EmployeeScheduleForm() # Initialize form for all paths

    if request.method == 'GET':
        # On GET, manually populate form fields from the model data
        if schedule:
            form.start_time.data = schedule.start_time
            form.end_time.data = schedule.end_time
            form.work_hours_per_day.data = schedule.work_hours_per_day
    
    # Set the hidden ID field (required for validation) manually on all paths
    form.employee_id.data = employee_id

    if form.validate_on_submit():
        if not schedule:
            # Create a new schedule entry if one does not exist
            schedule = EmployeeSchedule(employee_id=employee_id)
            db.session.add(schedule)

        try:
            # Data is reliably validated and typed by Flask-WTF fields
            schedule.start_time = form.start_time.data
            schedule.end_time = form.end_time.data
            schedule.work_hours_per_day = form.work_hours_per_day.data
            
            # --- AUDIT LOGGING ---
            action_type = 'CREATE_SCHEDULE' if not db.session.is_modified(schedule) else 'UPDATE_SCHEDULE'
            log_admin_action(
                action=action_type,
                details=f"Employee ID: {employee_id}. Schedule set to {schedule.start_time} - {schedule.end_time} ({schedule.work_hours_per_day} hrs)."
            )
            
            db.session.commit()
            flash(f"Schedule for {employee.first_name} updated successfully.", 'success')
            return redirect(url_for('attendance.manage_schedules'))
        except Exception as e:
            # Catch database/commit errors
            db.session.rollback()
            flash(f"Error updating schedule: {e}", 'danger')
            
    # FIX: Using simple filename. Template must be in app/attendance/templates/
    return render_template('edit_schedule.html', form=form, employee=employee)


# --- Manual Attendance Logging ---

@bp.route('/log/manual', methods=['GET', 'POST'])
@role_required('Payroll_Admin')
def manual_log():
    """Allows HR to manually log an attendance event for an employee."""
    form = ManualAttendanceLogForm()
    
    # Populate employee choices for the SelectField
    form.employee_id.choices = [(e.id, f"{e.first_name} {e.last_name} ({e.employee_id_number})")
                                for e in Employee.query.order_by(Employee.last_name).all()]
    
    if form.validate_on_submit():
        try:
            new_log = AttendanceLog(
                employee_id=form.employee_id.data,
                timestamp=form.timestamp.data,
                event_type=form.event_type.data,
                source=form.source.data
            )
            db.session.add(new_log)
            
            # --- AUDIT LOGGING ---
            log_admin_action(
                action='CREATE_ATTENDANCE_LOG',
                details=f"Manual log for Employee ID: {form.employee_id.data}. Event: {new_log.event_type} at {new_log.timestamp}."
            )
            
            db.session.commit()
            flash(f"Attendance event '{new_log.event_type}' logged successfully.", 'success')
            return redirect(url_for('attendance.manual_log'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error logging attendance: {e}", 'danger')

    # FIX: Using simple filename. Template must be in app/attendance/templates/
    return render_template('manual_log.html', form=form)


@bp.route('/log/history')
@role_required('Payroll_Admin')
def log_history():
    """Shows a recent history of all attendance logs."""
    
    recent_logs = AttendanceLog.query.order_by(AttendanceLog.timestamp.desc()).limit(50).all()
    
    # FIX: Using simple filename. Template must be in app/attendance/templates/
    return render_template('log_history.html', logs=recent_logs)


@bp.route('/log/edit/<int:log_id>', methods=['GET', 'POST'])
@role_required('Payroll_Admin')
def edit_log(log_id):
    """Edits an existing attendance log entry."""
    log = db.session.get(AttendanceLog, log_id)
    if not log:
        abort(404)
        
    form = EditAttendanceLogForm()
    
    if request.method == 'GET':
        # Populate form data on GET
        form.employee_name.data = f"{log.employee.first_name} {log.employee.last_name}"
        form.timestamp.data = log.timestamp
        form.event_type.data = log.event_type
        form.source.data = log.source
        
    if form.validate_on_submit():
        try:
            old_timestamp = log.timestamp
            old_event_type = log.event_type
            
            log.timestamp = form.timestamp.data
            log.event_type = form.event_type.data
            
            # --- AUDIT LOGGING ---
            log_admin_action(
                action='EDIT_ATTENDANCE_LOG',
                details=f"Edited Log ID #{log_id} for {log.employee.last_name}. Old: {old_event_type} at {old_timestamp}. New: {log.event_type} at {log.timestamp}."
            )
            
            db.session.commit()
            flash(f"Log entry #{log_id} updated successfully.", 'success')
            return redirect(url_for('attendance.log_history'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating log: {e}", 'danger')

    return render_template('edit_log.html', form=form, log=log)


@bp.route('/log/delete/<int:log_id>', methods=['POST'])
@role_required('Payroll_Admin')
def delete_log(log_id):
    """Deletes an attendance log entry."""
    log = db.session.get(AttendanceLog, log_id)
    if not log:
        flash("Log entry not found.", 'danger')
        return redirect(url_for('attendance.log_history'))
    
    # Pre-fetch data for the audit log
    employee_last_name = log.employee.last_name
    log_timestamp = log.timestamp

    try:
        # --- AUDIT LOGGING ---
        log_admin_action(
            action='DELETE_ATTENDANCE_LOG',
            details=f"Deleted Log ID #{log_id} for {employee_last_name}. Timestamp: {log_timestamp}."
        )
        
        db.session.delete(log)
        db.session.commit()
        flash(f"Log entry #{log_id} deleted successfully.", 'success')
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting log: {e}", 'danger')
        
    return redirect(url_for('attendance.log_history'))