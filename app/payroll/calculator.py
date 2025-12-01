# app/payroll/calculator.py

from decimal import Decimal
from datetime import datetime, timedelta, time, date
from sqlalchemy import func

# --- PHILHEALTH CONTRIBUTION TABLE ---
PHILHEALTH_RATE = Decimal('0.05')
PHILHEALTH_FLOOR = Decimal('10000.00')
PHILHEALTH_CEILING = Decimal('100000.00')

def calculate_philhealth(basic_salary):
    if basic_salary <= PHILHEALTH_FLOOR:
        total_premium = PHILHEALTH_FLOOR * PHILHEALTH_RATE
    elif basic_salary >= PHILHEALTH_CEILING:
        total_premium = PHILHEALTH_CEILING * PHILHEALTH_RATE
    else:
        total_premium = basic_salary * PHILHEALTH_RATE
    return (total_premium / 2).quantize(Decimal('0.01'))

# --- SSS CONTRIBUTION TABLE ---
SSS_TABLE = [
    (Decimal('4250.00'), Decimal('180.00')),
    (Decimal('24750.00'), Decimal('1125.00')),
    (Decimal('1000000.00'), Decimal('1350.00')),
]

def calculate_sss(basic_salary):
    for max_bracket, contribution in SSS_TABLE:
        if basic_salary <= max_bracket:
            return contribution
    return SSS_TABLE[-1][1]

# --- PAG-IBIG (HDMF) CONTRIBUTION ---
def calculate_pagibig(basic_salary):
    if basic_salary <= Decimal('1500.00'):
        contribution = basic_salary * Decimal('0.01')
    else:
        contribution = basic_salary * Decimal('0.02')
    return min(contribution, Decimal('100.00')).quantize(Decimal('0.01'))

# --- WITHHOLDING TAX ---
TAX_TABLE = [
    (Decimal('20833.00'), Decimal('0.00'), Decimal('0.00'), 0),
    (Decimal('33332.00'), Decimal('20833.00'), Decimal('0.00'), 15),
    (Decimal('66666.00'), Decimal('33333.00'), Decimal('1875.00'), 20),
    (Decimal('166666.00'), Decimal('66667.00'), Decimal('8541.80'), 25),
]

def calculate_withholding_tax(taxable_income):
    if taxable_income <= TAX_TABLE[0][0]:
        return Decimal('0.00')
    for max_bracket, excess_over, base_tax, tax_rate_percent in TAX_TABLE[1:]:
        if taxable_income <= max_bracket:
            excess = taxable_income - excess_over
            tax = base_tax + (excess * (Decimal(str(tax_rate_percent)) / 100))
            return tax.quantize(Decimal('0.01'))
    # For incomes above the highest bracket, use the highest bracket calculation
    # Using the last bracket (166,666+) with 25% rate
    last_bracket = TAX_TABLE[-1]
    excess = taxable_income - last_bracket[1]  # excess_over
    tax = last_bracket[2] + (excess * (Decimal(str(last_bracket[3])) / 100))  # base_tax + (excess * rate)
    return tax.quantize(Decimal('0.01')) 

# --- HELPER: TIME TO DECIMAL ---
def time_to_decimal_hours(t):
    if isinstance(t, timedelta):
        total_seconds = t.total_seconds()
    elif isinstance(t, time):
        total_seconds = t.hour * 3600 + t.minute * 60 + t.second
    else:
        return Decimal('0.00')
    return Decimal(total_seconds / 3600).quantize(Decimal('0.01'))

# --- CORE LOGIC: DAILY ATTENDANCE ---
def calculate_daily_attendance(logs, schedule, target_date):
    total_time = timedelta(0)
    if schedule:
        scheduled_start = datetime.combine(target_date, schedule.start_time)
        scheduled_hours = schedule.work_hours_per_day
    else:
        scheduled_start = datetime.combine(target_date, time(9, 0, 0))
        scheduled_hours = Decimal('8.00')

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
    late_minutes = 0
    if first_in and first_in > scheduled_start:
        late_timedelta = first_in - scheduled_start
        late_minutes = int(min(late_timedelta.total_seconds() / 60, 480))

    regular_hours = min(total_hours, scheduled_hours)
    overtime_hours = max(Decimal('0.00'), total_hours - scheduled_hours)
    
    return {
        'total_hours': total_hours, 'regular_hours': regular_hours,
        'overtime_hours': overtime_hours.quantize(Decimal('0.01')),
        'late_minutes': late_minutes, 'is_present': True
    }

# --- UPDATED FUNCTION: PERIOD CALCULATION (Includes Holidays) ---
def calculate_payroll_time_for_period(employee, pay_period_start, pay_period_end):
    from app.models.user import AttendanceLog, LeaveRequest, Holiday 
    
    all_logs = AttendanceLog.query.filter(
        AttendanceLog.employee_id == employee.id,
        func.date(AttendanceLog.timestamp) >= pay_period_start,
        func.date(AttendanceLog.timestamp) <= pay_period_end
    ).all()
    
    approved_leaves = LeaveRequest.query.filter(
        LeaveRequest.employee_id == employee.id,
        LeaveRequest.status == 'Approved',
        LeaveRequest.start_date <= pay_period_end,
        LeaveRequest.end_date >= pay_period_start
    ).all()

    period_holidays = Holiday.query.filter(
        Holiday.date >= pay_period_start,
        Holiday.date <= pay_period_end
    ).all()
    holiday_map = {h.date: h.type for h in period_holidays}

    daily_logs = {}
    for log in all_logs:
        d = log.timestamp.date()
        if d not in daily_logs: daily_logs[d] = []
        daily_logs[d].append(log)

    total_reg_hours = Decimal('0.00')
    total_ot_hours = Decimal('0.00')
    total_late_minutes = 0
    
    standard_hours = employee.schedules.work_hours_per_day if employee.schedules else Decimal('8.00')
    
    current_date = pay_period_start
    while current_date <= pay_period_end:
        is_weekend = current_date.weekday() >= 5 
        
        is_on_leave = False
        for leave in approved_leaves:
            if leave.start_date <= current_date <= leave.end_date:
                is_on_leave = True
                break
        
        holiday_type = holiday_map.get(current_date)
        logs = daily_logs.get(current_date, [])
        
        if logs:
            metrics = calculate_daily_attendance(logs, employee.schedules, current_date)
            total_reg_hours += metrics['regular_hours']
            total_ot_hours += metrics['overtime_hours']
            total_late_minutes += metrics['late_minutes']
            
        elif is_on_leave and not is_weekend and not holiday_type:
            total_reg_hours += standard_hours
            
        elif holiday_type == 'Regular' and not is_weekend:
            total_reg_hours += standard_hours
            
        current_date += timedelta(days=1)
        
    return {
        'total_reg_hours': total_reg_hours,
        'total_ot_hours': total_ot_hours,
        'total_late_minutes': total_late_minutes
    }

# --- MAIN PAYROLL CALCULATOR ---
def calculate_payroll_for_employee(employee, time_data):
    basic_monthly_salary = employee.salary_rate
    HOURS_PER_MONTH = Decimal('160.00')
    hourly_rate = basic_monthly_salary / HOURS_PER_MONTH if basic_monthly_salary else Decimal('0.00')
    
    total_reg_hours = time_data.get('total_reg_hours', Decimal('0.00'))
    total_ot_hours = time_data.get('total_ot_hours', Decimal('0.00'))
    total_late_minutes = time_data.get('total_late_minutes', 0)
    
    late_deduction = (Decimal(total_late_minutes) * (hourly_rate / 60)).quantize(Decimal('0.01'))
    overtime_pay = (total_ot_hours * hourly_rate * Decimal('1.25')).quantize(Decimal('0.01'))
    
    if total_reg_hours >= HOURS_PER_MONTH:
        prorated_base = basic_monthly_salary
    else:
        prorate_factor = total_reg_hours / HOURS_PER_MONTH
        prorated_base = (basic_monthly_salary * prorate_factor).quantize(Decimal('0.01'))
        
    # Gross salary = base pay + overtime (late deduction is handled in deductions, not here)
    gross_salary = (prorated_base + overtime_pay).quantize(Decimal('0.01'))
    
    statutory_base = basic_monthly_salary
    sss = calculate_sss(statutory_base)
    philhealth = calculate_philhealth(statutory_base)
    pagibig = calculate_pagibig(statutory_base)
    
    taxable_income = gross_salary - (sss + philhealth + pagibig)
    tax = calculate_withholding_tax(taxable_income)
    
    total_deductions = sss + philhealth + pagibig + tax + late_deduction
    
    net_pay = gross_salary - total_deductions
    if net_pay < 0:
        net_pay = Decimal('0.00')
        total_deductions = gross_salary 

    return {
        'gross_salary': gross_salary,
        'sss_deduction': sss,
        'philhealth_deduction': philhealth,
        'pagibig_deduction': pagibig,
        'withholding_tax': tax,
        'other_deductions': Decimal('0.00'),
        'total_deductions': total_deductions,
        'net_pay': net_pay,
        'regular_hours': total_reg_hours,
        'overtime_hours': total_ot_hours,
        'late_deductions': late_deduction
    }