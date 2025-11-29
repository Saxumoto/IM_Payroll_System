# app/hr/forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, DecimalField, DateField, PasswordField
from wtforms.validators import DataRequired, Email, Length, Optional, Regexp, NumberRange
from flask_wtf.file import FileField, FileAllowed

# --- Helper for file validation ---
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

class AddEmployeeForm(FlaskForm):
    """Form for Payroll Administrator to add a new employee record."""
    
    # User Creation Fields
    email = StringField('Login Email (Username)', validators=[DataRequired(), Email()])
    password = PasswordField('Initial Password', validators=[DataRequired(), Length(min=6)])
    
    photo = FileField('Employee Photo', validators=[
        FileAllowed(ALLOWED_EXTENSIONS, 'Images only!')
    ])
    
    # Employment Details
    employee_id_number = StringField('Employee ID (Company)', validators=[DataRequired(), Length(max=20)])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=64)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=64)])
    position = StringField('Position/Job Title', validators=[DataRequired(), Length(max=64)])
    date_hired = DateField('Date Hired', format='%Y-%m-%d', validators=[DataRequired()])
    salary_rate = DecimalField('Basic Salary Rate (Monthly)', validators=[DataRequired()])
    status = SelectField('Employment Status', choices=[('Active', 'Active'), ('Terminated', 'Terminated'), ('Resigned', 'Resigned')], default='Active')
    
    # Statutory
    tin = StringField('TIN', validators=[Optional(), Length(max=15)])
    sss_num = StringField('SSS No.', validators=[Optional(), Length(max=15)])
    philhealth_num = StringField('PhilHealth No.', validators=[Optional(), Length(max=15)])
    pagibig_num = StringField('Pag-IBIG No.', validators=[Optional(), Length(max=15)])
    bank_account_num = StringField('Bank Account No.', validators=[Optional(), Length(max=30)])
    
    submit = SubmitField('Add Employee')


class EditEmployeeForm(FlaskForm):
    """Form for Payroll Administrator to edit an existing employee record."""
    
    photo = FileField('Update Employee Photo', validators=[
        FileAllowed(ALLOWED_EXTENSIONS, 'Images only!')
    ])
    
    # Employment Details
    employee_id_number = StringField('Employee ID (Company)', validators=[DataRequired(), Length(max=20)])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=64)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=64)])
    position = StringField('Position/Job Title', validators=[DataRequired(), Length(max=64)])
    date_hired = DateField('Date Hired', format='%Y-%m-%d', validators=[DataRequired()])
    salary_rate = DecimalField('Basic Salary Rate (Monthly)', validators=[DataRequired()])
    status = SelectField('Employment Status', choices=[('Active', 'Active'), ('Terminated', 'Terminated'), ('Resigned', 'Resigned')])
    
    # Statutory
    tin = StringField('TIN', validators=[Optional(), Length(max=15)])
    sss_num = StringField('SSS No.', validators=[Optional(), Length(max=15)])
    philhealth_num = StringField('PhilHealth No.', validators=[Optional(), Length(max=15)])
    pagibig_num = StringField('Pag-IBIG No.', validators=[Optional(), Length(max=15)])
    bank_account_num = StringField('Bank Account No.', validators=[Optional(), Length(max=30)])
    
    submit = SubmitField('Update Employee Record')
    

class LeaveBalanceForm(FlaskForm):
    """Form for HR to set or update an employee's leave balance."""
    employee_id = StringField('Employee ID') # For display/context only
    leave_type = SelectField('Leave Type', choices=[
        ('Vacation', 'Vacation Leave'),
        ('Sick', 'Sick Leave'),
        ('Personal', 'Personal Leave'),
        ('Maternity', 'Maternity/Paternity Leave')
    ], validators=[DataRequired()])
    
    entitlement = DecimalField('Annual Entitlement (Days)', 
                               validators=[DataRequired(), NumberRange(min=0)], 
                               default=0.00)
    
    used = DecimalField('Days Used (Correction/Adjustment)', 
                        validators=[DataRequired(), NumberRange(min=0)], 
                        default=0.00)
    
    submit = SubmitField('Save Leave Balance')
    

class PasswordResetForm(FlaskForm):
    """Form for Admin to reset an employee's password."""
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Reset Password')


# --- THIS IS THE MISSING FORM ---
class HolidayForm(FlaskForm):
    """Form to add a new holiday."""
    name = StringField('Holiday Name', validators=[DataRequired(), Length(max=64)])
    date = DateField('Date', format='%Y-%m-%d', validators=[DataRequired()])
    type = SelectField('Type', choices=[
        ('Regular', 'Regular Holiday'), 
        ('Special', 'Special Non-Working')
    ], default='Regular')
    submit = SubmitField('Save Holiday')