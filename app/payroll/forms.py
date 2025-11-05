# app/payroll/forms.py

from flask_wtf import FlaskForm
from wtforms import DateField, SubmitField
from wtforms.validators import DataRequired

class RunPayrollForm(FlaskForm):
    """Form for Admin to define a new payroll run."""
    pay_period_start = DateField('Pay Period Start', format='%Y-%m-%d', validators=[DataRequired()])
    pay_period_end = DateField('Pay Period End', format='%Y-%m-%d', validators=[DataRequired()])
    pay_date = DateField('Payment Date', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Generate Payroll')