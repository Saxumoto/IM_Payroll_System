# app/payroll/calculator.py

from decimal import Decimal
from datetime import datetime, timedelta, time, date
from sqlalchemy import func

# --- PHILHEALTH CONTRIBUTION TABLE (Simplified) ---
# Based on 5% premium rate for 2025, 50/50 split (Employee/Employer)
# Salary Floor: 10,000, Ceiling: 100,000
PHILHEALTH_RATE = Decimal('0.05')
PHILHEALTH_FLOOR = Decimal('10000.00')
PHILHEALTH_CEILING = Decimal('100000.00')

def calculate_philhealth(basic_salary):
    """Calculates the employee's share of PhilHealth contribution."""
    
    if basic_salary <= PHILHEALTH_FLOOR:
        total_premium = PHILHEALTH_FLOOR * PHILHEALTH_RATE
    elif basic_salary >= PHILHEALTH_CEILING:
        total_premium = PHILHEALTH_CEILING * PHILHEALTH_RATE
    else:
        total_premium = basic_salary * PHILHEALTH_RATE
        
    # Employee share is 50%
    employee_share = total_premium / 2
    return employee_share.quantize(Decimal('0.01'))


# --- SSS CONTRIBUTION TABLE (Simplified) ---
# This is a *highly* simplified table for demonstration.
# Real table is much more complex.
# (bracket_max, employee_share)
SSS_TABLE = [
    (Decimal('4250.00'), Decimal('180.00')),
    (Decimal('24750.00'), Decimal('1125.00')),
    (Decimal('1000000.00'), Decimal('1350.00')), # Max contribution
]

def calculate_sss(basic_salary):
    """Calculates the employee's share of SSS contribution from a table."""
    for max_bracket, contribution in SSS_TABLE:
        if basic_salary <= max_bracket:
            return contribution
    return SSS_TABLE[-1][1] # Return max contribution if somehow above table


# --- PAG-IBIG (HDMF) CONTRIBUTION ---
def calculate_pagibig(basic_salary):
    """Calculates the employee's share of Pag-IBIG contribution."""
    # Standard contribution is 2% of basic salary, capped at 100
    # 1% if salary is 1,500 or less
    if basic_salary <= Decimal('1500.00'):
        contribution = basic_salary * Decimal('0.01')
    else:
        contribution = basic_salary * Decimal('0.02')
        
    # Employee share is capped at P100.00
    return min(contribution, Decimal('100.00')).quantize(Decimal('0.01'))


# --- WITHHOLDING TAX (Simplified Monthly Table) ---
# Based on simplified BIR TRAIN Law table (for demo)
# (min_bracket, excess_over, base_tax, tax_rate_percent)
TAX_TABLE = [
    # 1. 20,833 and below = 0%
    (Decimal('20833.00'), Decimal('0.00'), Decimal('0.00'), 0),
    # 2. 20,833 - 33,332 = 15% of excess over 20,833
    (Decimal('33332.00'), Decimal('20833.00'), Decimal('0.00'), 15),
    # 3. 33,333 - 66,666 = 1,875 + 20% of excess over 33,333
    (Decimal('66666.00'), Decimal('33333.00'), Decimal('1875.00'), 20),
    # 4. 66,667 - 166,666 = 8,541.80 + 25% of excess over 66,667
    (Decimal('166666.00'), Decimal('66667.00'), Decimal('8541.80'), 25),
    # ... (table continues, but this is enough for demo)
]

def calculate_withholding_tax(taxable_income):
    """Calculates the monthly withholding tax based on taxable income."""
    
    if taxable_income <= TAX_TABLE[0][0]:
        return Decimal('0.00')

    for max_bracket, excess_over, base_tax, tax_rate_percent in TAX_TABLE[1:]:
        if taxable_income <= max_bracket:
            excess = taxable_income - excess_over
            tax = base_tax + (excess * (Decimal(str(tax_rate_percent)) / 100))
            return tax.quantize(Decimal('0.01'))
    
    # Handle max bracket (not fully implemented in this demo table)
    return Decimal('0.00') # Default for incomes above our simple table

# --- MAIN CALCULATOR FUNCTION ---

def calculate_payroll_for_employee(employee, time_data):
    """
    Runs all payroll calculations for a single employee, incorporating T&A data.
    """
    
    basic_monthly_salary = employee.salary_rate
    
    # Standard for full-time salaried employees in a month (used for proration)
    HOURS_PER_MONTH = Decimal('160.00')
    hourly_rate = basic_monthly_salary / HOURS_PER_MONTH if basic_monthly_salary else Decimal('0.00')
    
    # --- T&A DATA RETRIEVAL ---
    total_reg_hours = time_data.get('total_reg_hours', Decimal('0.00'))
    total_ot_hours = time_data.get('total_ot_hours', Decimal('0.00'))
    total_late_minutes = time_data.get('total_late_minutes', 0)
    
    # --- 1. Gross Pay Adjustments based on T&A ---
    
    # LATE PENALTY (Monetary Deduction)
    late_deduction_amount = (Decimal(total_late_minutes) * (hourly_rate / 60)).quantize(Decimal('0.01'))
    
    # OVERTIME PAY (Monetary Addition)
    # Pays 1.25x the hourly rate for every calculated OT hour
    overtime_pay = (total_ot_hours * hourly_rate * Decimal('1.25')).quantize(Decimal('0.01'))
    
    # --- CORE FIX: PRORATION/UNDETIME DEDUCTION ---
    # This factor represents the proportion of expected regular hours that were actually worked.
    
    if total_reg_hours >= HOURS_PER_MONTH:
        # If employee met or exceeded standard regular hours, they get the full base salary
        prorated_base_salary = basic_monthly_salary
    else:
        # Prorate the base salary based on the actual regular hours attended
        prorate_factor = total_reg_hours / HOURS_PER_MONTH
        prorated_base_salary = (basic_monthly_salary * prorate_factor).quantize(Decimal('0.01'))
        
    # Adjusted Gross Salary: Prorated Base Salary + Overtime Pay - Late Deduction
    adjusted_gross_salary = (prorated_base_salary + overtime_pay - late_deduction_amount).quantize(Decimal('0.01'))
    
    # Use the Basic Monthly Salary for Statutory Deductions (as required by law)
    statutory_base = basic_monthly_salary
    
    # 2. Calculate Statutory Deductions (Based on unadjusted monthly rate)
    sss_deduction = calculate_sss(statutory_base)
    philhealth_deduction = calculate_philhealth(statutory_base)
    pagibig_deduction = calculate_pagibig(statutory_base)
    
    total_statutory_deductions = sss_deduction + philhealth_deduction + pagibig_deduction
    
    # Taxable income = Adjusted Gross Salary - Statutory Deductions (up to ceiling)
    # For simplicity, we use total statutory deduction as the non-taxable portion.
    taxable_income = adjusted_gross_salary - total_statutory_deductions
    withholding_tax = calculate_withholding_tax(taxable_income)
    
    # 3. Calculate Totals
    # Total deductions is Statutory + Withholding Tax + Lateness Penalty
    total_deductions = total_statutory_deductions + withholding_tax + late_deduction_amount
    net_pay = adjusted_gross_salary - total_deductions
    
    # --- FINAL SAFETY FIX: Prevent Negative Net Pay ---
    if net_pay < Decimal('0.00'):
        net_pay = Decimal('0.00')
        # If net pay is zeroed out, the employee receives the funds (0.00) but the remaining
        # uncollected deductions carry over implicitly (not implemented here, but standard).
        # We must adjust total deductions so that Gross - TotalDeductions = NetPay(0.00)
        total_deductions = adjusted_gross_salary
    
    # 4. Return results as a dictionary
    return {
        'gross_salary': adjusted_gross_salary,
        'sss_deduction': sss_deduction,
        'philhealth_deduction': philhealth_deduction,
        'pagibig_deduction': pagibig_deduction,
        'withholding_tax': withholding_tax,
        'other_deductions': Decimal('0.00'), # Placeholder for other deductions
        'total_deductions': total_deductions,
        'net_pay': net_pay,
        
        # T&A Metrics to be saved on Payslip (NEW)
        'regular_hours': total_reg_hours,
        'overtime_hours': total_ot_hours,
        'late_deductions': late_deduction_amount # Saving the monetary value of lateness
    }

# Helper function to convert time/timedelta to Decimal hours
def time_to_decimal_hours(t):
    """Converts a datetime.time or datetime.timedelta object to a Decimal representing hours."""
    if isinstance(t, timedelta):
        total_seconds = t.total_seconds()
    elif isinstance(t, time):
        total_seconds = t.hour * 3600 + t.minute * 60 + t.second
    else:
        return Decimal('0.00')
    
    return Decimal(total_seconds / 3600).quantize(Decimal('0.01'))


def calculate_daily_attendance(logs, schedule, target_date):
    """
    Processes all logs for a single employee on a single day against their schedule.
    
    Args:
        logs (list): List of AttendanceLog objects for the given employee on the target_date.
        schedule (EmployeeSchedule): The employee's standard schedule object.
        target_date (date): The day being calculated.
        
    Returns:
        dict: {
            'total_hours': Decimal, 
            'regular_hours': Decimal,
            'overtime_hours': Decimal,
            'late_minutes': int,
            'is_present': bool
        }
    """
    
    # 1. Initialize variables
    total_time = timedelta(0)
    
    # Use standard schedule times, or assume 9 AM start if schedule is missing
    if schedule:
        scheduled_start = datetime.combine(target_date, schedule.start_time)
        scheduled_hours = schedule.work_hours_per_day
    else:
        # Fallback for basic tracking if no schedule is set (cannot calculate late/OT)
        scheduled_start = datetime.combine(target_date, time(9, 0, 0))
        scheduled_hours = Decimal('8.00')

    first_in = None
    last_out = None
    
    # 2. Pair IN/OUT events and track first/last events
    
    # Sort logs by timestamp (should be implicit but good practice)
    sorted_logs = sorted(logs, key=lambda log: log.timestamp)
    
    in_time = None
    for log in sorted_logs:
        if log.event_type == 'IN':
            if not first_in:
                first_in = log.timestamp
            in_time = log.timestamp
        elif log.event_type == 'OUT' and in_time:
            # Calculate time between IN and OUT
            session_duration = log.timestamp - in_time
            total_time += session_duration
            
            last_out = log.timestamp
            in_time = None # Reset for the next pair
        elif log.event_type == 'ADJUST':
             # Simplistic way to handle ADJUST: treat it as a full workday
             # In a real system, ADJUST logs would specify hours added/subtracted
             pass

    # 3. Final calculation of metrics
    
    # Assume 0 hours if no successful clock-in/out pair was found
    if total_time == timedelta(0):
        return {
            'total_hours': Decimal('0.00'), 'regular_hours': Decimal('0.00'),
            'overtime_hours': Decimal('0.00'), 'late_minutes': 0, 'is_present': False
        }
    
    total_hours = time_to_decimal_hours(total_time)
    
    # Lateness Calculation
    late_minutes = 0
    if first_in and first_in > scheduled_start:
        late_timedelta = first_in - scheduled_start
        # Calculate late minutes, capping at 60 (to avoid massive penalty for schedule gap)
        late_minutes = int(min(late_timedelta.total_seconds() / 60, 60)) 

    # Overtime Calculation (Simplistic: Anything over scheduled hours is OT)
    regular_hours = min(total_hours, scheduled_hours)
    overtime_hours = max(Decimal('0.00'), total_hours - scheduled_hours)
    
    return {
        'total_hours': total_hours, 
        'regular_hours': regular_hours,
        'overtime_hours': overtime_hours.quantize(Decimal('0.01')),
        'late_minutes': late_minutes,
        'is_present': True
    }


def calculate_payroll_time_for_period(employee, pay_period_start, pay_period_end):
    """
    Runs daily attendance calculation for an employee over a full pay period.
    
    Returns:
        dict: {
            'total_reg_hours': Decimal, 
            'total_ot_hours': Decimal,
            'total_late_minutes': int
        }
    """
    from app.models.user import AttendanceLog # Dynamic import for model access
    
    current_date = pay_period_start
    daily_attendance_logs = {}
    
    # 1. Fetch all relevant logs for the entire period
    all_logs = AttendanceLog.query.filter(
        AttendanceLog.employee_id == employee.id,
        func.date(AttendanceLog.timestamp) >= pay_period_start,
        func.date(AttendanceLog.timestamp) <= pay_period_end
    ).order_by(AttendanceLog.timestamp.asc()).all()
    
    # Group logs by date
    for log in all_logs:
        log_date = log.timestamp.date()
        if log_date not in daily_attendance_logs:
            daily_attendance_logs[log_date] = []
        daily_attendance_logs[log_date].append(log)

    # 2. Aggregate metrics across the period
    total_reg_hours = Decimal('0.00')
    total_ot_hours = Decimal('0.00')
    total_late_minutes = 0
    
    schedule = employee.schedules
    
    while current_date <= pay_period_end:
        # Skip weekends/holidays if company policy requires it (not implemented here, assumed all days are workdays)
        
        logs_for_day = daily_attendance_logs.get(current_date, [])
        
        # Calculate for the day
        daily_metrics = calculate_daily_attendance(
            logs_for_day, 
            schedule, 
            current_date
        )
        
        if daily_metrics['is_present']:
            total_reg_hours += daily_metrics['regular_hours']
            total_ot_hours += daily_metrics['overtime_hours']
            total_late_minutes += daily_metrics['late_minutes']
        
        current_date += timedelta(days=1)
        
    return {
        'total_reg_hours': total_reg_hours.quantize(Decimal('0.01')),
        'total_ot_hours': total_ot_hours.quantize(Decimal('0.01')),
        'total_late_minutes': total_late_minutes
    }