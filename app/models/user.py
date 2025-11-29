# app/models/user.py

from app import db, login
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin 
from flask import url_for
from datetime import datetime, time 
from decimal import Decimal 
from sqlalchemy import event, select, func # Required for Triggers

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
    
    # Ensures an employee has only one balance record per leave type
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


# --- NEW: HOLIDAY TABLE ---
class Holiday(db.Model):
    __tablename__ = 'holiday'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False) 
    date = db.Column(db.Date, nullable=False)       
    type = db.Column(db.String(20), default='Regular') # 'Regular' or 'Special'
    
    def __repr__(self):
        return f'<Holiday {self.name} on {self.date}>'


# ==========================================
# DATABASE TRIGGERS (ORM EVENTS)
# ==========================================

# 1. TRIGGER: Auto-Update Payroll Run Totals
# This runs whenever a Payslip is Inserted, Updated, or Deleted
def update_payroll_run_totals(mapper, connection, target):
    """
    Trigger that recalculates the total_gross_pay, total_deductions, and total_net_pay
    of a PayrollRun whenever a specific Payslip is modified.
    """
    run_id = target.payroll_run_id
    payroll_run_table = PayrollRun.__table__
    payslip_table = Payslip.__table__

    # Calculate new totals from the database
    totals = connection.execute(
        select(
            func.sum(payslip_table.c.gross_salary),
            func.sum(payslip_table.c.total_deductions),
            func.sum(payslip_table.c.net_pay)
        ).where(payslip_table.c.payroll_run_id == run_id)
    ).first()

    # Handle case where no payslips exist (sets totals to 0)
    total_gross = totals[0] or 0
    total_deductions = totals[1] or 0
    total_net = totals[2] or 0

    # Update the parent PayrollRun record directly
    connection.execute(
        payroll_run_table.update()
        .where(payroll_run_table.c.id == run_id)
        .values(
            total_gross_pay=total_gross,
            total_deductions=total_deductions,
            total_net_pay=total_net
        )
    )

# Attach the function to Payslip events
event.listen(Payslip, 'after_insert', update_payroll_run_totals)
event.listen(Payslip, 'after_update', update_payroll_run_totals)
event.listen(Payslip, 'after_delete', update_payroll_run_totals)


# 2. TRIGGER: Auto-Initialize Leave Balances
# This runs immediately after a new Employee is inserted
@event.listens_for(Employee, 'after_insert')
def create_default_leave_balances(mapper, connection, target):
    """
    Trigger that automatically creates 'Vacation', 'Sick', and 'Personal' 
    leave balance records with 0.00 entitlement for every new employee.
    """
    leave_balance_table = LeaveBalance.__table__
    
    defaults = ['Vacation', 'Sick', 'Personal']
    
    for leave_type in defaults:
        connection.execute(
            leave_balance_table.insert().values(
                employee_id=target.id,
                leave_type=leave_type,
                entitlement=0.00,
                used=0.00
            )
        )