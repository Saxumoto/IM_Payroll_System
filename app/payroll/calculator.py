# app/payroll/calculator.py

from decimal import Decimal
from datetime import datetime, timedelta, time, date
from sqlalchemy import func

# --- PHILHEALTH CONTRIBUTION TABLE (Simplified) ---
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
        
    return (total_premium / 2).quantize(Decimal('0.01'))


# --- SSS CONTRIBUTION TABLE (Simplified) ---
SSS_TABLE = [
    (Decimal('4250.00'), Decimal('180.00')),
    (Decimal('24750.00'), Decimal('1125.00')),
    (Decimal('1000000.00'), Decimal('1350.00')),
]

def calculate_sss(basic_salary):
    """Calculates the employee's share of SSS contribution."""
    for max_bracket, contribution in SSS_TABLE:
        if basic_salary <= max_bracket:
            return contribution
    return SSS_TABLE[-1][1]


# --- PAG-IBIG (HDMF) CONTRIBUTION ---
def calculate_pagibig(basic_salary):
    """Calculates the employee's share of Pag-IBIG contribution."""
    if basic_salary <= Decimal('1500.00'):
        contribution = basic_salary * Decimal('0.01')
    else:
        contribution = basic_salary * Decimal('0.02')
    return min(contribution, Decimal('100.00')).quantize(Decimal('0.01'))


# --- WITHHOLDING TAX (Simplified) ---
TAX_TABLE = [
    (Decimal('20833.00'), Decimal('0.00'), Decimal('0.00'), 0),
    (Decimal('33332.00'), Decimal('20833.00'), Decimal('0.00'), 15),
    (Decimal('66666.00'), Decimal('33333.00'), Decimal('1875.00'), 20),
    (Decimal('166666.00'), Decimal('66667.00'), Decimal('8541.80'), 25),
]

def calculate_withholding_tax(taxable_income):
    """Calculates the monthly withholding tax."""
    if taxable_income <= TAX_TABLE[0][0]:
        return Decimal('0.00')

    for max_bracket, excess_over, base_tax, tax_rate_percent in TAX_TABLE[1:]:
        if taxable_income <= max_bracket:
            excess = taxable_income - excess_over
            tax = base_tax + (excess * (Decimal(str(tax_rate_percent)) / 100))
            return tax.quantize(Decimal('0.01'))
    
    return Decimal('0.00') 


# --- HELPER: TIME TO DECIMAL ---
def time_to_decimal_hours(t):
    """Converts time/timedelta to Decimal hours."""
    if isinstance(t, timedelta):
        total_seconds = t.total_seconds()
    elif isinstance(t, time):
        total_seconds = t.hour * 3600 + t.minute * 60 + t.second
    else:
        return Decimal('0.00')
    return Decimal(total_seconds / 3600).quantize(Decimal('0.01'))


# --- CORE LOGIC: DAILY ATTENDANCE ---
def calculate_daily_attendance(logs, schedule, target_date):
    """
    Calculates hours worked based on clock IN/OUT logs.
    """
    total_time = timedelta(0)
    
    if schedule:
        scheduled_start = datetime.combine(target_date, schedule.start_time)
        scheduled_hours = schedule.work_hours_per_day
    else:
        scheduled_start = datetime.combine(target_date, time(9, 0, 0))
        scheduled_hours = Decimal('8.00')

    # Sort and pair logs
    sorted_logs = sorted(logs, key=lambda log: log.timestamp)
    first_in = None
    in_time = None
    
    for log in sorted_logs:
        if log.event_type == 'IN':
            if not first_in: first_in = log.timestamp
            in_time = log.timestamp
        elif log.event_type == 'OUT' and in_time:
            total_time += (log.timestamp - in_time)
            in_time = None 

    if total_time == timedelta(0):
        return {
            'total_hours': Decimal('0.00'), 'regular_hours': Decimal('0.00'),
            'overtime_hours': Decimal('0.00'), 'late_minutes': 0, 'is_present': False
        }
    
    total_hours = time_to_decimal_hours(total_time)
    
    # Lateness (Grace period handling or straight calc)
    late_minutes = 0
    if first_in and first_in > scheduled_start:
        late_timedelta = first_in - scheduled_start
        # Cap late minutes at 480 (8 hours) to prevent massive outliers
        late_minutes = int(min(late_timedelta.total_seconds() / 60, 480))

    regular_hours = min(total_hours, scheduled_hours)
    overtime_hours = max(Decimal('0.00'), total_hours - scheduled_hours)
    
    return {
        'total_hours': total_hours, 
        'regular_hours': regular_hours,
        'overtime_hours': overtime_hours.quantize(Decimal('0.01')),
        'late_minutes': late_minutes,
        'is_present': True
    }


# --- UPDATED FUNCTION: PERIOD CALCULATION (Includes Leave) ---
def calculate_payroll_time_for_period(employee, pay_period_start, pay_period_end):
    """
    Aggregates attendance AND approved leave over the period.
    """
    # Dynamic imports to avoid circular dependency
    from app.models.user import AttendanceLog, LeaveRequest
    
    # 1. Fetch Logs
    all_logs = AttendanceLog.query.filter(
        AttendanceLog.employee_id == employee.id,
        func.date(AttendanceLog.timestamp) >= pay_period_start,
        func.date(AttendanceLog.timestamp) <= pay_period_end
    ).all()
    
    # 2. Fetch Approved Leaves that overlap with this period
    approved_leaves = LeaveRequest.query.filter(
        LeaveRequest.employee_id == employee.id,
        LeaveRequest.status == 'Approved',
        LeaveRequest.start_date <= pay_period_end,
        LeaveRequest.end_date >= pay_period_start
    ).all()

    # Organize logs by date
    daily_logs = {}
    for log in all_logs:
        d = log.timestamp.date()
        if d not in daily_logs: daily_logs[d] = []
        daily_logs[d].append(log)

    total_reg_hours = Decimal('0.00')
    total_ot_hours = Decimal('0.00')
    total_late_minutes = 0
    
    # Get Standard Daily Hours (default 8 if no schedule)
    standard_hours = employee.schedules.work_hours_per_day if employee.schedules else Decimal('8.00')
    
    current_date = pay_period_start
    while current_date <= pay_period_end:
        # Check if it's a weekend (0=Mon, 6=Sun). 
        # Assuming work days are Mon-Fri (0-4). Adjust if you have Sat work.
        is_weekend = current_date.weekday() >= 5 
        
        # Check if this specific day is covered by an Approved Leave
        is_on_leave = False
        for leave in approved_leaves:
            if leave.start_date <= current_date <= leave.end_date:
                is_on_leave = True
                break
        
        logs = daily_logs.get(current_date, [])
        
        if logs:
            # Case A: Employee clocked in (Presence)
            metrics = calculate_daily_attendance(logs, employee.schedules, current_date)
            total_reg_hours += metrics['regular_hours']
            total_ot_hours += metrics['overtime_hours']
            total_late_minutes += metrics['late_minutes']
            
        elif is_on_leave and not is_weekend:
            # Case B: Approved Paid Leave (No logs, but approved leave on a workday)
            # We credit them the standard daily hours so they get paid.
            total_reg_hours += standard_hours
            
        # Case C: Absent (No logs, no leave) -> 0 hours added
        
        current_date += timedelta(days=1)
        
    return {
        'total_reg_hours': total_reg_hours,
        'total_ot_hours': total_ot_hours,
        'total_late_minutes': total_late_minutes
    }


# --- MAIN PAYROLL CALCULATOR ---
def calculate_payroll_for_employee(employee, time_data):
    """
    Calculates financials based on time data.
    """
    basic_monthly_salary = employee.salary_rate
    HOURS_PER_MONTH = Decimal('160.00') # Standard divisor
    
    # Calculate Rate
    hourly_rate = basic_monthly_salary / HOURS_PER_MONTH if basic_monthly_salary else Decimal('0.00')
    
    # Extract Time Data
    total_reg_hours = time_data.get('total_reg_hours', Decimal('0.00'))
    total_ot_hours = time_data.get('total_ot_hours', Decimal('0.00'))
    total_late_minutes = time_data.get('total_late_minutes', 0)
    
    # 1. Adjustments
    late_deduction = (Decimal(total_late_minutes) * (hourly_rate / 60)).quantize(Decimal('0.01'))
    overtime_pay = (total_ot_hours * hourly_rate * Decimal('1.25')).quantize(Decimal('0.01'))
    
    # 2. Proration Logic (The Fix for Leave)
    # Since 'total_reg_hours' now includes Leave Hours, this logic works correctly.
    # If (Worked + Leave) >= 160, they get full basic salary.
    if total_reg_hours >= HOURS_PER_MONTH:
        prorated_base = basic_monthly_salary
    else:
        prorate_factor = total_reg_hours / HOURS_PER_MONTH
        prorated_base = (basic_monthly_salary * prorate_factor).quantize(Decimal('0.01'))
        
    gross_salary = (prorated_base + overtime_pay - late_deduction).quantize(Decimal('0.01'))
    
    # 3. Deductions
    statutory_base = basic_monthly_salary
    sss = calculate_sss(statutory_base)
    philhealth = calculate_philhealth(statutory_base)
    pagibig = calculate_pagibig(statutory_base)
    
    taxable_income = gross_salary - (sss + philhealth + pagibig)
    tax = calculate_withholding_tax(taxable_income)
    
    total_deductions = sss + philhealth + pagibig + tax + late_deduction
    
    # Safety check for negative net pay
    net_pay = gross_salary - total_deductions
    if net_pay < 0:
        net_pay = Decimal('0.00')
        total_deductions = gross_salary # Adjust display to match 0 net

    return {
        'gross_salary': gross_salary,
        'sss_deduction': sss,
        'philhealth_deduction': philhealth,
        'pagibig_deduction': pagibig,
        'withholding_tax': tax,
        'other_deductions': Decimal('0.00'),
        'total_deductions': total_deductions,
        'net_pay': net_pay,
        'regular_hours': total_reg_hours, # This now includes leave hours
        'overtime_hours': total_ot_hours,
        'late_deductions': late_deduction
    }