# app/employee/forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DateField, TextAreaField, SelectField
from wtforms.validators import DataRequired
from datetime import date

# --- THIS IS THE FIX ---
from wtforms.validators import DataRequired, Length # <-- 'Length' has been added


class LeaveRequestForm(FlaskForm):
    """Form for employees to submit a new leave request."""
    
    leave_type = SelectField('Leave Type', choices=[
        ('Vacation', 'Vacation'),
        ('Sick', 'Sick'),
        ('Personal', 'Personal'),
        ('Other', 'Other')
    ], validators=[DataRequired()])
    
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[DataRequired()], default=date.today)
    end_date = DateField('End Date', format='%Y-%m-%d', validators=[DataRequired()], default=date.today)
    
    # This line will no longer crash
    reason = TextAreaField('Reason (Optional)', validators=[Length(max=500)])
    
    submit = SubmitField('Submit Request')