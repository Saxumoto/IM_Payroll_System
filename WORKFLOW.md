# IM Payroll System - Complete Workflow Guide

This document walks through the complete workflow of the payroll system from different user perspectives.

---

## 🏗️ **PHASE 1: Initial Setup**

### 1.1 System Installation
1. Install dependencies: `pip install -r requirements.txt`
2. Set up environment variables in `.env` file
3. Initialize database: `flask db upgrade`
4. Run the application: `python run.py`

### 1.2 Create First Admin User
1. **Register a user** via `/auth/register` (creates Employee role by default)
2. **Manually promote to Admin** via database:
   ```python
   from app import create_app, db
   from app.models.user import User
   
   app = create_app()
   with app.app_context():
       user = User.query.filter_by(username='admin@example.com').first()
       user.role = 'Admin'
       db.session.commit()
   ```
3. **Login** as Admin → Redirected to Admin Dashboard

---

## 👥 **PHASE 2: Employee Onboarding (HR/Admin Workflow)**

### 2.1 Add New Employee
**Route:** `/hr/employee/add`  
**Access:** Payroll_Admin or Admin role

**Process:**
1. Fill out employee form:
   - **User Account**: Email (username), Initial Password
   - **Employee Details**: ID Number, Name, Position, Date Hired
   - **Compensation**: Monthly Salary Rate
   - **Statutory Info**: TIN, SSS, PhilHealth, Pag-IBIG, Bank Account
   - **Photo**: Upload employee photo (optional)
   - **Status**: Active/Terminated/Resigned

2. **System Actions:**
   - Creates `User` record with role='Employee'
   - Creates `Employee` record linked to User
   - **Auto-creates Leave Balances** (Vacation, Sick, Personal) via database trigger
   - Saves photo securely with UUID filename
   - Logs action in Audit Log

3. **Result:** Employee can now login and access their dashboard

### 2.2 Set Employee Schedule
**Route:** `/attendance/schedule/edit/<employee_id>`  
**Access:** Payroll_Admin or Admin

**Process:**
1. Set work schedule:
   - Start Time (e.g., 9:00 AM)
   - End Time (e.g., 6:00 PM)
   - Work Hours Per Day (e.g., 8.00 hours)

2. **Purpose:** Used for:
   - Calculating late arrivals
   - Determining regular vs overtime hours
   - Payroll calculations

### 2.3 Set Leave Entitlements
**Route:** `/hr/leave_balances/edit/<employee_id>/<leave_type>`  
**Access:** Payroll_Admin or Admin

**Process:**
1. Set leave entitlements for each type:
   - Vacation Leave
   - Sick Leave
   - Personal Leave

2. **Fields:**
   - Entitlement: Total days allocated
   - Used: Days already taken (auto-updated by system)

---

## 📅 **PHASE 3: Daily Operations**

### 3.1 Employee Clock In/Out
**Route:** `/employee/dashboard` → Click "Clock In/Out" button  
**Access:** Employee (self-service)

**Process:**
1. Employee clicks clock button
2. System checks last log:
   - If last was "IN" → Creates "OUT" log
   - If last was "OUT" or no log → Creates "IN" log
3. **AttendanceLog** record created with:
   - Timestamp (UTC)
   - Event Type (IN/OUT)
   - Source: "Employee Self-Service"

4. **Dashboard shows:**
   - Current clock status
   - Last clock time
   - Leave balances

### 3.2 Manual Attendance Logging (HR)
**Route:** `/attendance/log/manual`  
**Access:** Payroll_Admin or Admin

**Use Cases:**
- Correcting missed clock entries
- Adding attendance for remote workers
- Adjusting timestamps

**Process:**
1. Select employee
2. Enter timestamp
3. Select event type (IN/OUT/ADJUST)
4. System creates log entry
5. Action logged in Audit Log

### 3.3 Manage Holidays
**Route:** `/hr/holidays`  
**Access:** Payroll_Admin or Admin

**Process:**
1. Add holiday:
   - Name (e.g., "New Year's Day")
   - Date
   - Type: Regular or Special

2. **Impact on Payroll:**
   - Regular holidays: Counted as paid working days
   - Excluded from leave balance calculations
   - Included in payroll time calculations

---

## 🏖️ **PHASE 4: Leave Management**

### 4.1 Employee Files Leave Request
**Route:** `/employee/file_leave`  
**Access:** Employee

**Process:**
1. Fill leave request form:
   - Leave Type (Vacation/Sick/Personal)
   - Start Date
   - End Date
   - Reason

2. **System Validations:**
   - Checks for overlapping leave requests
   - Validates date range
   - Creates `LeaveRequest` with status='Pending'

3. **Result:** Request appears in HR's pending queue

### 4.2 HR Approves/Rejects Leave
**Route:** `/hr/leave_requests`  
**Access:** Payroll_Admin or Admin

**Process:**
1. View all leave requests (sorted by status)
2. Click Approve/Reject button
3. **System Actions on Approval:**
   - Validates sufficient leave balance (working days only)
   - Updates status to 'Approved'
   - **Database trigger automatically:**
     - Calculates working days (excludes weekends/holidays)
     - Deducts from `LeaveBalance.used`
   - Logs action in Audit Log

4. **On Rejection:**
   - Updates status to 'Rejected'
   - No balance deduction
   - Logs action

### 4.3 Leave Balance Tracking
- **Automatic:** System auto-updates when leave is approved/rejected
- **Manual Override:** HR can manually adjust balances at `/hr/leave_balances`
- **View:** Employees see balances on their dashboard

---

## 💰 **PHASE 5: Payroll Processing**

### 5.1 Run Payroll
**Route:** `/payroll/run`  
**Access:** Payroll_Admin or Admin

**Process:**

#### Step 1: Enter Pay Period Details
- Pay Period Start Date
- Pay Period End Date
- Pay Date

#### Step 2: System Processing (Automatic)
For each **Active** employee:

1. **Calculate Time & Attendance:**
   ```
   - Retrieves all attendance logs in period
   - Retrieves approved leave requests
   - Retrieves holidays in period
   - For each day in period:
     * If has attendance logs → Calculate hours worked
     * If on approved leave → Add standard hours
     * If regular holiday → Add standard hours
     * Skip weekends
   - Calculates:
     * Total Regular Hours
     * Total Overtime Hours (hours > scheduled hours)
     * Total Late Minutes
   ```

2. **Calculate Payroll:**
   ```
   Base Salary Calculation:
   - If regular_hours >= 160: Full monthly salary
   - Else: Prorated (regular_hours / 160 * monthly_salary)
   
   Adjustments:
   - Overtime Pay = overtime_hours * hourly_rate * 1.25
   - Late Deduction = late_minutes * (hourly_rate / 60)
   - Gross Salary = Base + Overtime - Late (in deductions, not gross)
   
   Statutory Deductions (based on full monthly salary):
   - SSS: From contribution table
   - PhilHealth: 5% of salary (capped at ceiling)
   - Pag-IBIG: 2% of salary (capped at ₱100)
   
   Tax Calculation:
   - Taxable Income = Gross - Statutory Deductions
   - Withholding Tax: From BIR TRAIN Law table
   
   Final Calculation:
   - Total Deductions = SSS + PhilHealth + Pag-IBIG + Tax + Late
   - Net Pay = Gross Salary - Total Deductions
   ```

3. **Create Payslip:**
   - Saves all calculated values
   - Links to PayrollRun
   - Includes T&A metrics (regular_hours, overtime_hours, late_deductions)

4. **Update PayrollRun Totals:**
   - Sums all payslips
   - Updates total_gross_pay, total_deductions, total_net_pay
   - Sets status to 'Processed'

#### Step 3: Review Results
- View summary at `/payroll/summary/<run_id>`
- See individual payslips
- Can delete payslips (if run not finalized)

### 5.2 Payroll History
**Route:** `/payroll/history`  
**Access:** Payroll_Admin or Admin

- View all past payroll runs
- Access summaries and individual payslips

---

## 👤 **PHASE 6: Employee Self-Service**

### 6.1 Employee Dashboard
**Route:** `/employee/dashboard`  
**Access:** Employee

**Features:**
- **Clock Status:** Current IN/OUT status with timestamp
- **Quick Actions:** Clock In/Out button
- **Leave Balances:** Remaining days for each leave type
- **Navigation:** Links to payslips, leave requests

### 6.2 View Payslips
**Route:** `/employee/my_payslips`  
**Access:** Employee

**Features:**
- List of all payslips (sorted by pay date)
- Click to view detailed payslip:
  - Pay period dates
  - Hours worked (regular, overtime)
  - Gross salary breakdown
  - All deductions
  - Net pay

### 6.3 Leave Management
**Routes:**
- `/employee/file_leave` - Submit new leave request
- `/employee/my_leave_history` - View all past requests

**Features:**
- Submit leave requests
- View request status (Pending/Approved/Rejected)
- See leave history

---

## 🔍 **PHASE 7: Administrative Functions**

### 7.1 Manage Staff
**Route:** `/hr/manage_staff`  
**Access:** Payroll_Admin or Admin

**Actions:**
- View all employees
- Edit employee details
- Reset employee passwords
- Delete employees (cascades to user account)

### 7.2 Audit Logs
**Route:** `/dashboard/audit_logs`  
**Access:** Admin only

**Features:**
- View all administrative actions
- Filter by user, action type, date
- Delete all logs (Admin only)

**Tracked Actions:**
- Employee creation/deletion
- Leave request approvals/rejections
- Password resets
- Attendance log edits
- Schedule changes
- Leave balance updates
- Holiday management
- Payslip deletions

---

## 🔄 **Data Flow Diagram**

```
┌─────────────────┐
│  Employee       │
│  Clock In/Out    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ AttendanceLog   │
│ (IN/OUT events) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Payroll Run    │
│  (Period)       │
└────────┬────────┘
         │
         ├──► Calculate Time & Attendance
         │    ├──► Regular Hours
         │    ├──► Overtime Hours
         │    └──► Late Minutes
         │
         ├──► Calculate Payroll
         │    ├──► Base Salary (prorated)
         │    ├──► Overtime Pay
         │    ├──► Statutory Deductions
         │    ├──► Withholding Tax
         │    └──► Net Pay
         │
         ▼
┌─────────────────┐
│    Payslip      │
│  (Per Employee) │
└─────────────────┘
```

---

## 🔐 **Security & Access Control**

### Role-Based Access:

**Admin:**
- Full system access
- Can manage all employees
- Can run payroll
- Can view audit logs
- Can delete audit logs

**Payroll_Admin:**
- All HR functions
- Can run payroll
- Cannot delete audit logs

**Employee:**
- Self-service only
- View own payslips
- File leave requests
- Clock in/out
- View own leave history

---

## 📊 **Key Database Relationships**

```
User (1) ──── (1) Employee
                │
                ├─── (M) Payslip
                ├─── (M) LeaveRequest
                ├─── (M) AttendanceLog
                ├─── (M) LeaveBalance
                └─── (1) EmployeeSchedule

PayrollRun (1) ──── (M) Payslip
```

---

## 🎯 **Common Workflows Summary**

### Monthly Payroll Cycle:
1. Employees clock in/out daily
2. HR manages leave requests
3. HR adds holidays
4. At month end: HR runs payroll
5. System calculates all payslips
6. Employees view their payslips

### Leave Request Cycle:
1. Employee files leave request
2. HR reviews and approves/rejects
3. System auto-deducts from balance (if approved)
4. Employee sees updated balance

### New Employee Onboarding:
1. HR adds employee (creates user + employee record)
2. System auto-creates leave balances
3. HR sets work schedule
4. HR sets leave entitlements
5. Employee can login and use system

---

## ⚠️ **Important Notes**

1. **Leave Balance Calculation:**
   - Uses **working days** (excludes weekends and holidays)
   - Automatically updated via database triggers
   - HR validation matches trigger logic

2. **Payroll Calculation:**
   - Late deductions are in deductions, not subtracted from gross
   - Statutory deductions based on full monthly salary (not prorated)
   - Overtime rate: 1.25x hourly rate

3. **Attendance Tracking:**
   - Requires matching IN/OUT pairs
   - Overtime calculated if total hours > scheduled hours per day
   - Late minutes capped at 480 (8 hours)

4. **Data Integrity:**
   - All actions logged in Audit Log
   - Database triggers maintain consistency
   - Cascading deletes for employee-user relationship

---

This workflow ensures accurate payroll processing, proper leave management, and comprehensive audit trails for all administrative actions.

