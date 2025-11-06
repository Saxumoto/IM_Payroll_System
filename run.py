# run.py

import os
from app import create_app, db
# FIX: Import all models required for the shell context/migration tool
from app.models.user import User, Employee, PayrollRun, Payslip, LeaveRequest, AttendanceLog, EmployeeSchedule 


app = create_app(os.environ.get('FLASK_ENV', 'default'))

@app.shell_context_processor
def make_shell_context():
    """Adds database instance and models to the Flask shell."""
    return dict(db=db, User=User, Employee=Employee, PayrollRun=PayrollRun, Payslip=Payslip, LeaveRequest=LeaveRequest, AttendanceLog=AttendanceLog, EmployeeSchedule=EmployeeSchedule)

if __name__ == '__main__':
    app.run()