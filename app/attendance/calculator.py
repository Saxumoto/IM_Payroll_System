# app/payroll/calculator.py

from decimal import Decimal

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
    
    Args:
        employee (Employee): The employee record.
        time_data (dict): The result from calculate_payroll_time_for_period.
        
    Returns:
        A dictionary with all payslip values.
    """
    
    basic_monthly_salary = employee.salary_rate
    
    # Calculate Hourly Rate (Assumed 160 hours per month for simplicity)
    HOURS_PER_MONTH = Decimal('160.00')
    hourly_rate = basic_monthly_salary / HOURS_PER_MONTH if basic_monthly_salary else Decimal('0.00')
    
    # --- 1. Gross Pay Adjustments based on T&A ---
    
    # LATE PENALTY: Convert late minutes into a monetary deduction
    # Using 1/60th of the hourly rate per minute.
    late_deduction_amount = (Decimal(time_data.get('total_late_minutes', 0)) * (hourly_rate / 60)).quantize(Decimal('0.01'))
    
    # OVERTIME PAY: Calculate bonus for overtime hours (1.25x factor)
    # Note: Regular hours are assumed covered by the basic monthly salary.
    overtime_pay = (time_data.get('total_ot_hours', Decimal('0.00')) * hourly_rate * Decimal('1.25')).quantize(Decimal('0.01'))
    
    # Adjusted Gross Salary: Start with monthly salary, add OT, subtract late penalty
    adjusted_gross_salary = (basic_monthly_salary + overtime_pay - late_deduction_amount).quantize(Decimal('0.01'))
    
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
    # Total deductions is Statutory + Withholding Tax + T&A Penalty
    total_deductions = total_statutory_deductions + withholding_tax + late_deduction_amount
    net_pay = adjusted_gross_salary - total_deductions
    
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
        'regular_hours': time_data.get('total_reg_hours', Decimal('0.00')),
        'overtime_hours': time_data.get('total_ot_hours', Decimal('0.00')),
        'late_deductions': late_deduction_amount # Saving the monetary value of lateness
    }