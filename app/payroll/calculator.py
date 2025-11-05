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

def calculate_payroll_for_employee(employee):
    """
    Runs all payroll calculations for a single employee.
    Returns a dictionary with all payslip values.
    """
    
    # We assume basic_salary is the monthly rate from the Employee model
    basic_salary = employee.salary_rate
    
    # 1. Calculate Deductions
    sss_deduction = calculate_sss(basic_salary)
    philhealth_deduction = calculate_philhealth(basic_salary)
    pagibig_deduction = calculate_pagibig(basic_salary)
    
    total_statutory_deductions = sss_deduction + philhealth_deduction + pagibig_deduction
    
    # Taxable income = Gross Salary - All Statutory Deductions
    taxable_income = basic_salary - total_statutory_deductions
    
    withholding_tax = calculate_withholding_tax(taxable_income)
    
    # 2. Calculate Totals
    total_deductions = total_statutory_deductions + withholding_tax
    net_pay = basic_salary - total_deductions
    
    # 3. Return results as a dictionary
    return {
        'gross_salary': basic_salary,
        'sss_deduction': sss_deduction,
        'philhealth_deduction': philhealth_deduction,
        'pagibig_deduction': pagibig_deduction,
        'withholding_tax': withholding_tax,
        'other_deductions': Decimal('0.00'), # Placeholder
        'total_deductions': total_deductions,
        'net_pay': net_pay
    }