# app/attendance/forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, TimeField, DateTimeField, HiddenField, DecimalField
from wtforms.validators import DataRequired, Optional, NumberRange
from datetime import datetime, time

# --- Schedule Management Forms ---

class EmployeeScheduleForm(FlaskForm):
    """Form for setting an employee's work schedule."""
    employee_id = HiddenField('Employee ID', validators=[DataRequired()])
    start_time = TimeField('Shift Start Time', format='%H:%M', validators=[DataRequired()])
    end_time = TimeField('Shift End Time', format='%H:%M', validators=[DataRequired()])
    # FIX: Changed to DecimalField and added NumberRange validator
    work_hours_per_day = DecimalField('Work Hours per Day (e.g., 8.00)', 
                                      validators=[DataRequired(), NumberRange(min=0.01)],
                                      places=2) 
    submit = SubmitField('Save Schedule')


# --- Manual Attendance Log Forms ---

class ManualAttendanceLogForm(FlaskForm):
    """Form for manually adding a clock event for an employee."""
    employee_id = SelectField('Employee', coerce=int, validators=[DataRequired()])
    # Keep timestamp field for backend, but we'll use separate date/time inputs in frontend
    timestamp = DateTimeField('Date and Time', format='%Y-%m-%d %H:%M:%S', default=datetime.now, validators=[DataRequired()])
    event_type = SelectField('Event Type', choices=[
        ('IN', 'Clock In'),
        ('OUT', 'Clock Out'),
        ('ADJUST', 'Adjustment (Special Entry)')
    ], validators=[DataRequired()])
    source = HiddenField('Source', default='HR Manual')
    submit = SubmitField('Log Event')
    
# --- NEW FORM ---
class EditAttendanceLogForm(FlaskForm):
    """Form for editing an existing attendance log entry."""
    employee_name = StringField('Employee', render_kw={'readonly': True})
    timestamp = DateTimeField('Date and Time', format='%Y-%m-%d %H:%M:%S', validators=[DataRequired()])
    event_type = SelectField('Event Type', choices=[
        ('IN', 'Clock In'),
        ('OUT', 'Clock Out'),
        ('ADJUST', 'Adjustment (Special Entry)')
    ], validators=[DataRequired()])
    source = StringField('Source', render_kw={'readonly': True})
    submit = SubmitField('Update Log Entry')