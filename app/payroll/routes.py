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

@bp.route('/run', methods=['GET', 'POST'])
@role_required('Payroll_Admin')
def run_payroll():
    # Dynamic import to avoid circular dependency
    from .calculator import calculate_payroll_time_for_period as calculate_time_for_period 

    form = RunPayrollForm()
    
    if form.validate_on_submit():
        pay_period_start = form.pay_period_start.data
        pay_period_end = form.pay_period_end.data
        pay_date = form.pay_date.data
        
        # Validate date ranges
        if pay_period_end < pay_period_start:
            flash('Error: Pay period end date must be on or after start date.', 'danger')
            return render_template('payroll/run_payroll.html', form=form)
        
        if pay_date < pay_period_end:
            flash('Warning: Payment date is before pay period end. Please verify.', 'warning')
        
        new_run = PayrollRun(
            pay_period_start=pay_period_start,
            pay_period_end=pay_period_end,
            pay_date=pay_date,
            status='Processing'
        )
        db.session.add(new_run)
        db.session.flush()
        
        active_employees = Employee.query.filter_by(status='Active').all()
        
        if not active_employees:
            flash('No active employees found. Payroll run cancelled.', 'warning')
            db.session.rollback()
            return redirect(url_for('payroll.run_payroll'))
            
        total_gross = Decimal('0.00')
        total_deduct = Decimal('0.00')
        total_net = Decimal('0.00')

        try:
            for emp in active_employees:
                # Validate employee has salary rate
                if not emp.salary_rate or emp.salary_rate <= 0:
                    flash(f'Warning: Employee {emp.first_name} {emp.last_name} ({emp.employee_id_number}) has invalid salary rate. Skipping.', 'warning')
                    continue
                
                # Calculate Time (Includes Holidays & Leave now)
                time_data = calculate_time_for_period(emp, pay_period_start, pay_period_end)
                
                # Calculate Money
                calculations = calculator.calculate_payroll_for_employee(emp, time_data) 
                
                payslip = Payslip(
                    employee_id=emp.id,
                    payroll_run_id=new_run.id,
                    regular_hours=calculations['regular_hours'],
                    overtime_hours=calculations['overtime_hours'],
                    late_deductions=calculations['late_deductions'],
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
                
                total_gross += calculations['gross_salary']
                total_deduct += calculations['total_deductions']
                total_net += calculations['net_pay']

            new_run.total_gross_pay = total_gross
            new_run.total_deductions = total_deduct
            new_run.total_net_pay = total_net
            new_run.status = 'Processed'
            
            db.session.commit()
            
            flash(f'Payroll processed successfully for {len(active_employees)} employees.', 'success')
            return redirect(url_for('payroll.payroll_summary', run_id=new_run.id))

        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred during payroll processing: {e}', 'danger')

    return render_template('payroll/run_payroll.html', form=form)


@bp.route('/summary/<int:run_id>')
@role_required('Payroll_Admin')
def payroll_summary(run_id):
    run = db.session.get(PayrollRun, run_id)
    if not run:
        flash('Payroll run not found.', 'danger')
        return redirect(url_for('main.admin_dashboard'))
    
    payslips = Payslip.query.filter_by(payroll_run_id=run.id).all()
    return render_template('payroll/payroll_summary.html', run=run, payslips=payslips)


@bp.route('/payslip/delete/<int:slip_id>/<int:run_id>', methods=['POST'])
@role_required('Payroll_Admin')
def delete_payslip(slip_id, run_id):
    payslip = db.session.get(Payslip, slip_id)
    
    if not payslip:
        flash('Payslip not found.', 'danger')
        return redirect(url_for('payroll.payroll_summary', run_id=run_id))

    # --- FIX: DATA INTEGRITY CHECK ---
    # Prevent deletion if the payroll run is already processed
    if payslip.payroll_run.status == 'Processed': 
        flash('Cannot delete payslip: This payroll run is already processed and finalized.', 'danger')
        return redirect(url_for('payroll.payroll_summary', run_id=run_id))

    try:
        employee_name = payslip.employee.last_name
        employee_id_num = payslip.employee.employee_id_number
        
        from app.hr.routes import log_admin_action
        log_admin_action(
            action='DELETE_PAYSLIP',
            details=f"Deleted Payslip ID #{slip_id} (Run #{run_id}) for Employee: {employee_name} ({employee_id_num})."
        )
        
        db.session.delete(payslip)
        db.session.commit()
        
        flash(f'Payslip for {employee_name} deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while deleting the payslip: {e}', 'danger')

    return redirect(url_for('payroll.payroll_summary', run_id=run_id))


@bp.route('/history')
@role_required('Payroll_Admin')
def payroll_history():
    all_runs = PayrollRun.query.order_by(PayrollRun.pay_date.desc()).all()
    return render_template('payroll/payroll_history.html', all_runs=all_runs)