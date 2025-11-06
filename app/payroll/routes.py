# app/payroll/routes.py

from flask import render_template, redirect, url_for, flash
from flask_login import login_required
from app.payroll import bp
from app.payroll.forms import RunPayrollForm
from app.models.user import Employee, PayrollRun, Payslip
from app.hr.routes import role_required
from app import db
from . import calculator
from decimal import Decimal
# The problematic top-level import has been removed from here.

@bp.route('/run', methods=['GET', 'POST'])
@role_required('Payroll_Admin') # Protect this route
def run_payroll():
    """Shows form to start a new payroll run and processes it."""
    
    # --- FIX: Dynamic/Local Import to break the module load cycle ---
    # We now import the module and access the function via dot notation.
    from .calculator import calculate_payroll_time_for_period as calculate_time_for_period 

    form = RunPayrollForm()
    
    if form.validate_on_submit():
        pay_period_start = form.pay_period_start.data
        pay_period_end = form.pay_period_end.data
        
        # --- 1. Create the main PayrollRun record ---
        new_run = PayrollRun(
            pay_period_start=pay_period_start,
            pay_period_end=pay_period_end,
            pay_date=form.pay_date.data,
            status='Processing'
        )
        db.session.add(new_run)
        db.session.flush() # Get the ID for the new_run
        
        # --- 2. Get all active employees ---
        active_employees = Employee.query.filter_by(status='Active').all()
        
        if not active_employees:
            flash('No active employees found. Payroll run cancelled.', 'warning')
            return redirect(url_for('payroll.run_payroll'))
            
        total_gross = Decimal('0.00')
        total_deduct = Decimal('0.00')
        total_net = Decimal('0.00')

        try:
            # --- 3. Loop, Calculate, and Save Payslips ---
            for emp in active_employees:
                
                # --- NEW: CALCULATE T&A DATA (Time worked, late minutes) ---
                # Use the aliased local function
                time_data = calculate_time_for_period(emp, pay_period_start, pay_period_end)
                
                # Calculate payroll for this employee (Adjusted Gross Pay, Deductions)
                calculations = calculator.calculate_payroll_for_employee(emp, time_data) 
                
                # Create the Payslip record
                payslip = Payslip(
                    employee_id=emp.id,
                    payroll_run_id=new_run.id,
                    
                    # T&A Metrics (NEW)
                    regular_hours=calculations['regular_hours'],
                    overtime_hours=calculations['overtime_hours'],
                    late_deductions=calculations['late_deductions'],
                    
                    # Financial Metrics
                    gross_salary=calculations['gross_salary'],
                    sss_deduction=calculations['sss_deduction'],
                    philhealth_deduction=calculations['philhealth_deduction'],
                    pagibig_deduction=calculations['pagibig_deduction'],
                    withholding_tax=calculations['withholding_tax'],
                    other_deductions=calculations['other_deductions'],
                    total_deductions=calculations['total_deductions'],
                    net_pay=calculations['net_pay']
                )
                db.session.add(payslip)
                
                # Update totals for the main run
                total_gross += calculations['gross_salary']
                total_deduct += calculations['total_deductions']
                total_net += calculations['net_pay']

            # --- 4. Update the main PayrollRun with totals ---
            new_run.total_gross_pay = total_gross
            new_run.total_deductions = total_deduct
            new_run.total_net_pay = total_net
            new_run.status = 'Processed'
            
            db.session.commit() # Commit all changes
            
            flash(f'Payroll processed successfully for {len(active_employees)} employees.', 'success')
            # We will create this 'payroll_summary' page next
            return redirect(url_for('payroll.payroll_summary', run_id=new_run.id))

        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred during payroll processing: {e}', 'danger')

    return render_template('payroll/run_payroll.html', form=form)


@bp.route('/summary/<int:run_id>')
@role_required('Payroll_Admin')
def payroll_summary(run_id):
    """Shows the summary of a completed payroll run."""
    run = db.session.get(PayrollRun, run_id)
    if not run:
        flash('Payroll run not found.', 'danger')
        return redirect(url_for('main.admin_dashboard'))
        
    # Get all payslips associated with this run
    payslips = Payslip.query.filter_by(payroll_run_id=run.id).all()
    
    return render_template('payroll/payroll_summary.html', run=run, payslips=payslips)

# --- FIX: Delete Payslip Route ---
@bp.route('/payslip/delete/<int:slip_id>/<int:run_id>', methods=['POST'])
@role_required('Payroll_Admin')
def delete_payslip(slip_id, run_id):
    """Deletes a specific payslip record."""
    payslip = db.session.get(Payslip, slip_id)
    
    if not payslip:
        flash('Payslip not found.', 'danger')
        return redirect(url_for('payroll.payroll_summary', run_id=run_id))

    try:
        # FIX: Force load employee name *before* deleting/detaching the object
        employee_name = payslip.employee.last_name
        employee_id_num = payslip.employee.employee_id_number
        
        # --- AUDIT LOGGING ---
        from app.hr.routes import log_admin_action # Dynamic import for helper
        log_admin_action(
            action='DELETE_PAYSLIP',
            details=f"Deleted Payslip ID #{slip_id} (Run #{run_id}) for Employee: {employee_name} ({employee_id_num})."
        )
        
        db.session.delete(payslip)
        db.session.commit()
        
        # Use the cached name in the flash message
        flash(f'Payslip for {employee_name} deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while deleting the payslip: {e}', 'danger')

    return redirect(url_for('payroll.payroll_summary', run_id=run_id))


@bp.route('/history')
@role_required('Payroll_Admin') # Protect this route
def payroll_history():
    """Shows a list of all past payroll runs."""
    
    # Query the database for all PayrollRun records, order by most recent first
    all_runs = PayrollRun.query.order_by(PayrollRun.pay_date.desc()).all()
    
    return render_template('payroll/payroll_history.html', all_runs=all_runs)