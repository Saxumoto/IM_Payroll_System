# Payroll Processing - Detailed Walkthrough

This document provides a step-by-step explanation of how the payroll system processes employee pay, with real examples and calculations.

---

## 📋 **Overview**

When HR runs payroll, the system:
1. **Collects Data** - Attendance logs, leave requests, holidays
2. **Calculates Time** - Regular hours, overtime, late minutes
3. **Calculates Pay** - Base salary, overtime, deductions, net pay
4. **Creates Payslips** - Saves all calculations for each employee

---

## 🔍 **STEP-BY-STEP PROCESS**

### **STEP 1: HR Initiates Payroll Run**

**Route:** `/payroll/run`  
**User:** Payroll_Admin or Admin

**Input:**
- Pay Period Start: `2024-01-01`
- Pay Period End: `2024-01-31`
- Pay Date: `2024-02-05`

**System Action:**
```python
# Creates a PayrollRun record
new_run = PayrollRun(
    pay_period_start='2024-01-01',
    pay_period_end='2024-01-31',
    pay_date='2024-02-05',
    status='Processing'
)
```

---

### **STEP 2: System Processes Each Active Employee**

For each employee with `status='Active'`, the system runs two main calculations:

#### **2A. TIME & ATTENDANCE CALCULATION**
#### **2B. PAYROLL CALCULATION**

Let's follow **Employee: Juan Dela Cruz** through the process:

**Employee Details:**
- Monthly Salary: ₱30,000.00
- Schedule: 9:00 AM - 6:00 PM (8 hours/day)
- Employee ID: EMP001

---

## ⏰ **STEP 2A: TIME & ATTENDANCE CALCULATION**

### **Function:** `calculate_payroll_time_for_period(employee, pay_period_start, pay_period_end)`

### **2A.1: Data Collection**

The system queries:

**A. Attendance Logs:**
```python
all_logs = AttendanceLog.query.filter(
    AttendanceLog.employee_id == employee.id,
    func.date(AttendanceLog.timestamp) >= '2024-01-01',
    func.date(AttendanceLog.timestamp) <= '2024-01-31'
).all()
```

**Example Logs for Juan:**
```
Jan 2, 2024 09:15 AM - IN
Jan 2, 2024 06:30 PM - OUT
Jan 3, 2024 09:00 AM - IN
Jan 3, 2024 07:00 PM - OUT
Jan 5, 2024 09:30 AM - IN
Jan 5, 2024 06:00 PM - OUT
... (more logs)
```

**B. Approved Leave Requests:**
```python
approved_leaves = LeaveRequest.query.filter(
    LeaveRequest.employee_id == employee.id,
    LeaveRequest.status == 'Approved',
    LeaveRequest.start_date <= '2024-01-31',
    LeaveRequest.end_date >= '2024-01-01'
).all()
```

**Example:** Juan has approved leave on Jan 15-16 (Vacation)

**C. Holidays:**
```python
period_holidays = Holiday.query.filter(
    Holiday.date >= '2024-01-01',
    Holiday.date <= '2024-01-31'
).all()
```

**Example:** New Year's Day (Jan 1) - Regular Holiday

---

### **2A.2: Daily Processing Loop**

The system iterates through **each day** in the pay period:

```python
current_date = '2024-01-01'
while current_date <= '2024-01-31':
    # Process each day
    current_date += timedelta(days=1)
```

**For each day, the system checks:**

#### **Day Type 1: Has Attendance Logs**

**Example: January 2, 2024 (Tuesday)**

**Logs:**
- 09:15 AM - IN
- 06:30 PM - OUT

**Process:**
1. **Calculate Total Time Worked:**
   ```
   IN:  09:15 AM
   OUT: 06:30 PM
   Total Time: 9 hours 15 minutes = 9.25 hours
   ```

2. **Check for Late Arrival:**
   ```
   Scheduled Start: 09:00 AM
   Actual Start:    09:15 AM
   Late: 15 minutes
   ```

3. **Calculate Regular vs Overtime:**
   ```
   Scheduled Hours: 8.00 hours
   Total Hours:     9.25 hours
   
   Regular Hours:   min(9.25, 8.00) = 8.00 hours
   Overtime Hours:  max(0, 9.25 - 8.00) = 1.25 hours
   ```

**Code Logic:**
```python
def calculate_daily_attendance(logs, schedule, target_date):
    # Sort logs by timestamp
    sorted_logs = sorted(logs, key=lambda log: log.timestamp)
    
    # Pair IN/OUT events
    total_time = timedelta(0)
    first_in = None
    in_time = None
    
    for log in sorted_logs:
        if log.event_type == 'IN':
            if not first_in: 
                first_in = log.timestamp  # Track first IN for late calculation
            in_time = log.timestamp
        elif log.event_type == 'OUT' and in_time:
            total_time += (log.timestamp - in_time)
            in_time = None
    
    # Calculate late minutes
    if first_in > scheduled_start:
        late_minutes = (first_in - scheduled_start).total_seconds() / 60
        late_minutes = min(late_minutes, 480)  # Cap at 8 hours
    
    # Calculate regular vs overtime
    total_hours = time_to_decimal_hours(total_time)
    regular_hours = min(total_hours, scheduled_hours)
    overtime_hours = max(0, total_hours - scheduled_hours)
    
    return {
        'regular_hours': regular_hours,
        'overtime_hours': overtime_hours,
        'late_minutes': late_minutes
    }
```

**Result for Jan 2:**
- Regular Hours: 8.00
- Overtime Hours: 1.25
- Late Minutes: 15

---

#### **Day Type 2: On Approved Leave**

**Example: January 15, 2024 (Monday)**

**Condition:** Juan has approved leave (Vacation) on Jan 15-16

**Process:**
```python
if is_on_leave and not is_weekend and not holiday_type:
    total_reg_hours += standard_hours  # Adds 8.00 hours
```

**Result for Jan 15:**
- Regular Hours: 8.00 (paid leave)
- Overtime Hours: 0.00
- Late Minutes: 0

**Note:** Leave days are counted as regular hours, so employee gets paid for approved leave.

---

#### **Day Type 3: Regular Holiday**

**Example: January 1, 2024 (Monday - New Year's Day)**

**Process:**
```python
if holiday_type == 'Regular' and not is_weekend:
    total_reg_hours += standard_hours  # Adds 8.00 hours
```

**Result for Jan 1:**
- Regular Hours: 8.00 (paid holiday)
- Overtime Hours: 0.00
- Late Minutes: 0

---

#### **Day Type 4: Weekend**

**Example: January 6, 2024 (Saturday)**

**Process:**
```python
if is_weekend:  # weekday() >= 5
    # Skip - no hours added
    continue
```

**Result for Jan 6:**
- Regular Hours: 0.00
- Overtime Hours: 0.00
- Late Minutes: 0

---

### **2A.3: Aggregate Results**

After processing all days in January:

**Juan's Time Summary:**
```
Total Regular Hours:  152.00 hours
Total Overtime Hours: 12.50 hours
Total Late Minutes:   45 minutes
```

**Breakdown:**
- 19 working days with attendance = 152 regular + 12.5 OT
- 2 days on approved leave = 16 regular hours
- 1 regular holiday = 8 regular hours
- Weekends excluded
- **Total Regular: 176.00 hours** (exceeds 160, so full month salary)

---

## 💰 **STEP 2B: PAYROLL CALCULATION**

### **Function:** `calculate_payroll_for_employee(employee, time_data)`

**Input from Step 2A:**
```python
time_data = {
    'total_reg_hours': 176.00,
    'total_ot_hours': 12.50,
    'total_late_minutes': 45
}
```

---

### **2B.1: Calculate Hourly Rate**

```python
basic_monthly_salary = 30000.00
HOURS_PER_MONTH = 160.00
hourly_rate = 30000.00 / 160.00 = ₱187.50/hour
```

---

### **2B.2: Calculate Late Deduction**

```python
late_minutes = 45
late_deduction = 45 * (187.50 / 60)
              = 45 * 3.125
              = ₱140.63
```

**Note:** Late deduction is calculated per minute based on hourly rate.

---

### **2B.3: Calculate Overtime Pay**

```python
overtime_hours = 12.50
overtime_rate = hourly_rate * 1.25  # 1.25x multiplier
              = 187.50 * 1.25
              = ₱234.38/hour

overtime_pay = 12.50 * 234.38
             = ₱2,929.75
```

---

### **2B.4: Calculate Base Salary (Proration)**

```python
total_reg_hours = 176.00
HOURS_PER_MONTH = 160.00

if total_reg_hours >= HOURS_PER_MONTH:
    prorated_base = basic_monthly_salary  # Full salary
else:
    prorate_factor = total_reg_hours / HOURS_PER_MONTH
    prorated_base = basic_monthly_salary * prorate_factor

# Since 176 >= 160:
prorated_base = ₱30,000.00  # Full monthly salary
```

**If employee worked less than 160 hours:**
```
Example: 120 regular hours
prorate_factor = 120 / 160 = 0.75
prorated_base = 30000 * 0.75 = ₱22,500.00
```

---

### **2B.5: Calculate Gross Salary**

```python
# Gross = Base + Overtime (late deduction is in deductions, not here)
gross_salary = prorated_base + overtime_pay
             = 30000.00 + 2929.75
             = ₱32,929.75
```

**Important:** Late deduction is NOT subtracted from gross. It's added to deductions later.

---

### **2B.6: Calculate Statutory Deductions**

**These are based on FULL monthly salary, not prorated or adjusted gross.**

#### **SSS Deduction:**
```python
statutory_base = 30000.00  # Full monthly salary

# SSS Table lookup:
# Salary <= 4,250: ₱180.00
# Salary <= 24,750: ₱1,125.00
# Salary <= 1,000,000: ₱1,350.00 (max)

# Since 30,000 > 24,750:
sss = ₱1,350.00
```

#### **PhilHealth Deduction:**
```python
# PhilHealth: 5% of salary, split 50/50 (employee/employer)
# Floor: ₱10,000, Ceiling: ₱100,000

if salary <= 10000:
    total_premium = 10000 * 0.05 = 500
elif salary >= 100000:
    total_premium = 100000 * 0.05 = 5000
else:
    total_premium = 30000 * 0.05 = 1500

employee_share = 1500 / 2 = ₱750.00
```

#### **Pag-IBIG Deduction:**
```python
# Pag-IBIG: 2% of salary, capped at ₱100
# If salary <= 1,500: 1%

if salary <= 1500:
    contribution = salary * 0.01
else:
    contribution = salary * 0.02

contribution = 30000 * 0.02 = ₱600.00
# Capped at ₱100:
pagibig = min(600, 100) = ₱100.00
```

**Total Statutory Deductions:**
```
SSS:        ₱1,350.00
PhilHealth: ₱750.00
Pag-IBIG:   ₱100.00
─────────────────────
Total:      ₱2,200.00
```

---

### **2B.7: Calculate Withholding Tax**

```python
# Taxable Income = Gross Salary - Statutory Deductions
taxable_income = gross_salary - (sss + philhealth + pagibig)
               = 32,929.75 - 2,200.00
               = ₱30,729.75

# BIR TRAIN Law Tax Table:
# 20,833 and below: 0%
# 20,833 - 33,332: 15% of excess over 20,833
# 33,333 - 66,666: 1,875 + 20% of excess over 33,333
# 66,667 - 166,666: 8,541.80 + 25% of excess over 66,667

# Since 30,729.75 is in bracket 2 (20,833 - 33,332):
excess = 30,729.75 - 20,833.00 = 9,896.75
tax = 0 + (9,896.75 * 0.15) = ₱1,484.51
```

---

### **2B.8: Calculate Total Deductions**

```python
total_deductions = sss + philhealth + pagibig + tax + late_deduction
                 = 1,350.00 + 750.00 + 100.00 + 1,484.51 + 140.63
                 = ₱3,825.14
```

---

### **2B.9: Calculate Net Pay**

```python
net_pay = gross_salary - total_deductions
        = 32,929.75 - 3,825.14
        = ₱29,104.61
```

**Safety Check:**
```python
if net_pay < 0:
    net_pay = 0.00
    total_deductions = gross_salary  # Cap deductions at gross
```

---

## 📄 **STEP 3: Create Payslip**

The system creates a Payslip record with all calculated values:

```python
payslip = Payslip(
    employee_id=emp.id,
    payroll_run_id=new_run.id,
    
    # Time & Attendance Metrics
    regular_hours=176.00,
    overtime_hours=12.50,
    late_deductions=140.63,
    
    # Earnings
    gross_salary=32,929.75,
    
    # Deductions
    sss_deduction=1,350.00,
    philhealth_deduction=750.00,
    pagibig_deduction=100.00,
    withholding_tax=1,484.51,
    other_deductions=0.00,
    total_deductions=3,825.14,
    
    # Final
    net_pay=29,104.61
)
```

---

## 📊 **STEP 4: Aggregate Payroll Run Totals**

After processing all employees:

```python
# Sum all payslips
total_gross = sum(all_payslips.gross_salary)
total_deduct = sum(all_payslips.total_deductions)
total_net = sum(all_payslips.net_pay)

# Update PayrollRun
new_run.total_gross_pay = total_gross
new_run.total_deductions = total_deduct
new_run.total_net_pay = total_net
new_run.status = 'Processed'
```

---

## 📋 **COMPLETE EXAMPLE: Juan's Payslip**

### **Employee Information:**
- Name: Juan Dela Cruz
- Employee ID: EMP001
- Monthly Salary: ₱30,000.00
- Pay Period: January 1-31, 2024
- Pay Date: February 5, 2024

### **Time & Attendance:**
- Regular Hours: 176.00
- Overtime Hours: 12.50
- Late Minutes: 45

### **Earnings:**
```
Base Salary (Full Month):    ₱30,000.00
Overtime Pay (12.5 hrs):     ₱ 2,929.75
────────────────────────────────────────
Gross Salary:                ₱32,929.75
```

### **Deductions:**
```
SSS:                         ₱ 1,350.00
PhilHealth:                  ₱   750.00
Pag-IBIG:                    ₱   100.00
Withholding Tax:             ₱ 1,484.51
Late Deduction (45 min):     ₱   140.63
────────────────────────────────────────
Total Deductions:            ₱ 3,825.14
```

### **Net Pay:**
```
Gross Salary:                ₱32,929.75
Less: Total Deductions:      ₱ 3,825.14
────────────────────────────────────────
Net Pay:                     ₱29,104.61
```

---

## 🔑 **KEY POINTS TO REMEMBER**

### **1. Proration Logic:**
- If regular hours < 160: Salary is prorated
- If regular hours >= 160: Full monthly salary
- Overtime is always paid separately

### **2. Statutory Deductions:**
- Always based on **full monthly salary**, not prorated
- Not affected by overtime or late deductions
- Required by Philippine law

### **3. Late Deduction:**
- Calculated per minute: `(hourly_rate / 60) * late_minutes`
- Added to deductions, NOT subtracted from gross
- Capped at 480 minutes (8 hours) per day

### **4. Overtime Calculation:**
- Rate: 1.25x hourly rate
- Only hours exceeding scheduled daily hours
- Paid in addition to base salary

### **5. Leave and Holidays:**
- Approved leave: Counted as regular hours (paid)
- Regular holidays: Counted as regular hours (paid)
- Weekends: Not counted (unpaid)

### **6. Tax Calculation:**
- Based on taxable income (Gross - Statutory Deductions)
- Uses BIR TRAIN Law progressive tax table
- Calculated after all other deductions

---

## 🔄 **Data Flow Summary**

```
Payroll Run Initiated
    ↓
For Each Active Employee:
    ↓
    ┌─────────────────────────┐
    │ 1. Collect Data         │
    │    - Attendance Logs    │
    │    - Leave Requests     │
    │    - Holidays           │
    └───────────┬─────────────┘
                ↓
    ┌─────────────────────────┐
    │ 2. Calculate Time       │
    │    - Daily loop         │
    │    - Regular hours      │
    │    - Overtime hours     │
    │    - Late minutes       │
    └───────────┬─────────────┘
                ↓
    ┌─────────────────────────┐
    │ 3. Calculate Pay        │
    │    - Base salary        │
    │    - Overtime pay       │
    │    - Statutory ded.     │
    │    - Tax                │
    │    - Net pay            │
    └───────────┬─────────────┘
                ↓
    ┌─────────────────────────┐
    │ 4. Create Payslip       │
    │    - Save all values    │
    └───────────┬─────────────┘
                ↓
    ┌─────────────────────────┐
    │ 5. Aggregate Totals    │
    │    - Sum all payslips   │
    └─────────────────────────┘
                ↓
    Payroll Run Complete
```

---

This detailed walkthrough shows exactly how the system processes payroll from start to finish, with real calculations and examples.

