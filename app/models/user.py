# app/models/user.py

from app import db, login
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin 
from flask import url_for
from datetime import datetime, time 
from decimal import Decimal 

class User(UserMixin, db.Model): 
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True) 
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='Employee')
    full_name = db.Column(db.String(128)) 
    
    employee = db.relationship('Employee', back_populates='user', uselist=False)
    audit_logs = db.relationship('AuditLog', backref='user', lazy='dynamic') 

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    def __repr__(self):
        return f'<User {self.username}>'


class Employee(db.Model):
    __tablename__ = 'employee'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True)
    employee_id_number = db.Column(db.String(20), index=True, unique=True) 
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    position = db.Column(db.String(64))
    date_hired = db.Column(db.Date)
    photo_filename = db.Column(db.String(128), default='default.png')
    salary_rate = db.Column(db.Numeric(10, 2), nullable=False) 
    status = db.Column(db.String(20), default='Active') 
    tin = db.Column(db.String(15)) 
    sss_num = db.Column(db.String(15))
    philhealth_num = db.Column(db.String(15))
    pagibig_num = db.Column(db.String(15))
    bank_account_num = db.Column(db.String(30))

    user = db.relationship('User', back_populates='employee')
    payslips = db.relationship('Payslip', back_populates='employee', lazy='dynamic')
    leave_requests = db.relationship('LeaveRequest', back_populates='employee', lazy='dynamic')
    schedules = db.relationship('EmployeeSchedule', back_populates='employee', uselist=False)
    attendance_logs = db.relationship('AttendanceLog', back_populates='employee', lazy='dynamic')
    leave_balances = db.relationship('LeaveBalance', back_populates='employee', lazy='select')


    def __repr__(self):
        return f'<Employee {self.employee_id_number}>'
    
    @property
    def photo_url(self):
        filename_to_use = self.photo_filename if self.photo_filename else 'default.png'
        return url_for('main.get_uploaded_file', filename=filename_to_use)


class LeaveBalance(db.Model):
    """
    Stores the accrued and used leave days for an employee.
    """
    __tablename__ = 'leave_balance'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    leave_type = db.Column(db.String(50), nullable=False) 
    entitlement = db.Column(db.Numeric(5, 2), nullable=False, default=0.00) 
    used = db.Column(db.Numeric(5, 2), nullable=False, default=0.00) 
    
    employee = db.relationship('Employee', back_populates='leave_balances')
    
    __table_args__ = (db.UniqueConstraint('employee_id', 'leave_type', name='_employee_leave_type_uc'),)
    
    @property
    def remaining(self):
        return self.entitlement - self.used

    def __repr__(self):
        return f'<Balance {self.leave_type} for {self.employee.employee_id_number}>'

class EmployeeSchedule(db.Model):
    """
    Stores employee's regular work schedule.
    """
    __tablename__ = 'employee_schedule'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), unique=True, nullable=False)
    start_time = db.Column(db.Time, nullable=False, default=time(9, 0, 0)) 
    end_time = db.Column(db.Time, nullable=False, default=time(18, 0, 0))   
    work_hours_per_day = db.Column(db.Numeric(4, 2), nullable=False, default=Decimal('8.00')) 

    employee = db.relationship('Employee', back_populates='schedules')

    def __repr__(self):
        return f'<Schedule for {self.employee.employee_id_number}>'

class AttendanceLog(db.Model):
    """
    Stores raw clock in/out data.
    """
    __tablename__ = 'attendance_log'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    event_type = db.Column(db.String(20), nullable=False) 
    source = db.Column(db.String(50), nullable=False, default='Manual') 
    
    employee = db.relationship('Employee', back_populates='attendance_logs')

    def __repr__(self):
        return f'<Log {self.event_type} at {self.timestamp} by {self.employee.employee_id_number}>'


class PayrollRun(db.Model):
    __tablename__ = 'payroll_run'
    id = db.Column(db.Integer, primary_key=True)
    # FIX: Set Date columns to nullable=True
    pay_period_start = db.Column(db.Date, nullable=True) 
    pay_period_end = db.Column(db.Date, nullable=True)   
    pay_date = db.Column(db.Date, nullable=True)         
    total_gross_pay = db.Column(db.Numeric(12, 2), default=0.00)
    total_deductions = db.Column(db.Numeric(12, 2), default=0.00)
    total_net_pay = db.Column(db.Numeric(12, 2), default=0.00)
    status = db.Column(db.String(20), default='Pending') 

    payslips = db.relationship('Payslip', back_populates='payroll_run', lazy='dynamic')
    def __repr__(self):
        return f'<PayrollRun {self.pay_period_start}>'


class Payslip(db.Model):
    __tablename__ = 'payslip'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    payroll_run_id = db.Column(db.Integer, db.ForeignKey('payroll_run.id'), nullable=False)
    employee = db.relationship('Employee', back_populates='payslips')
    payroll_run = db.relationship('PayrollRun', back_populates='payslips')
    
    # T&A Metrics
    regular_hours = db.Column(db.Numeric(10, 2), default=0.00) 
    overtime_hours = db.Column(db.Numeric(10, 2), default=0.00) 
    late_deductions = db.Column(db.Numeric(10, 2), default=0.00) 

    gross_salary = db.Column(db.Numeric(10, 2), nullable=False)
    sss_deduction = db.Column(db.Numeric(10, 2), default=0.00)
    philhealth_deduction = db.Column(db.Numeric(10, 2), default=0.00)
    pagibig_deduction = db.Column(db.Numeric(10, 2), default=0.00)
    withholding_tax = db.Column(db.Numeric(10, 2), default=0.00)
    other_deductions = db.Column(db.Numeric(10, 2), default=0.00)
    total_deductions = db.Column(db.Numeric(10, 2), nullable=False)
    net_pay = db.Column(db.Numeric(10, 2), nullable=False)
    
    def __repr__(self):
        return f'<Payslip for Employee ID {self.employee_id}>'


class LeaveRequest(db.Model):
    """
    Represents a single leave request from an employee.
    """
    __tablename__ = 'leave_request'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    leave_type = db.Column(db.String(50), nullable=False) 
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default='Pending') 
    requested_on = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    employee = db.relationship('Employee', back_populates='leave_requests')

    def __repr__(self):
        return f'<LeaveRequest {self.id} by {self.employee.first_name}>'

class AuditLog(db.Model):
    """
    Tracks sensitive administrative actions for security and compliance.
    """
    __tablename__ = 'audit_log'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) 
    action = db.Column(db.String(100), nullable=False) 
    details = db.Column(db.Text, nullable=True) 

    def __repr__(self):
        return f"<AuditLog {self.action} by {self.user_id} on {self.timestamp}>"