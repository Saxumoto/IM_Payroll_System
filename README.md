# IM Payroll System

A comprehensive payroll management system built with Flask, featuring employee management, attendance tracking, leave management, and automated payroll processing.

## Features

- **Employee Management**: Complete employee profiles with photos, employment details, and statutory information
- **Attendance Tracking**: Clock in/out system with manual logging and schedule management
- **Leave Management**: Leave request system with balance tracking and approval workflow
- **Payroll Processing**: Automated payroll calculation with:
  - Time & Attendance integration
  - Statutory deductions (SSS, PhilHealth, Pag-IBIG)
  - Withholding tax calculation
  - Overtime and late penalty handling
- **Audit Logging**: Comprehensive audit trail of all administrative actions
- **Role-Based Access Control**: Admin and Employee roles with appropriate permissions

## Requirements

- Python 3.11+
- Flask 3.1.2+
- SQLite (development) or PostgreSQL/MySQL (production)

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd IM_Payroll_System
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows:
   venv\Scripts\activate
   
   # On Linux/Mac:
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit .env and set your SECRET_KEY and DATABASE_URL
   ```

5. **Initialize the database**
   ```bash
   flask db upgrade
   ```

6. **Run the application**
   ```bash
   python run.py
   ```

   The application will be available at `http://localhost:5000`

## Configuration

### Environment Variables

Create a `.env` file in the root directory with the following variables:

- `FLASK_ENV`: Set to `development` or `production`
- `SECRET_KEY`: A secure random key for session management (required in production)
- `DATABASE_URL`: Database connection string (required in production)

See `.env.example` for a template.

### Production Deployment

For production deployment:

1. Set `FLASK_ENV=production` in your `.env` file
2. Set a strong `SECRET_KEY` (generate with: `python -c "import secrets; print(secrets.token_hex(32))"`)
3. Configure a production database (PostgreSQL or MySQL)
4. Use a production WSGI server (e.g., Gunicorn, uWSGI)
5. Set up proper logging and monitoring

**Example with Gunicorn:**
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 "run:app"
```

## Database Migrations

The application uses Flask-Migrate for database version control.

- **Create a migration**: `flask db migrate -m "Description"`
- **Apply migrations**: `flask db upgrade`
- **Rollback**: `flask db downgrade`

## Project Structure

```
IM_Payroll_System/
├── app/
│   ├── __init__.py          # Application factory
│   ├── auth/                # Authentication routes
│   ├── employee/            # Employee self-service routes
│   ├── hr/                  # HR management routes
│   ├── payroll/             # Payroll processing routes
│   ├── attendance/          # Attendance management
│   ├── main/                # Main dashboard routes
│   ├── models/              # Database models
│   ├── static/              # Static files (CSS, JS, images)
│   └── templates/           # Jinja2 templates
├── migrations/              # Database migration scripts
├── instance/                # Instance-specific files (database, config)
├── uploads/                 # User-uploaded files
├── config.py               # Configuration classes
├── requirements.txt        # Python dependencies
└── run.py                  # Application entry point
```

## Security Features

- Password hashing with Werkzeug
- CSRF protection via Flask-WTF
- File upload validation and sanitization
- Path traversal protection
- Role-based access control
- Secure session management

## Default Roles

- **Admin**: Full system access, can manage all employees and payroll
- **Employee**: Self-service access to view payslips, file leave requests, and clock in/out

## Creating an Admin User

1. Register a user through the signup page (creates Employee role)
2. Manually update the database to change role to 'Admin':
   ```python
   from app import create_app, db
   from app.models.user import User
   
   app = create_app()
   with app.app_context():
       user = User.query.filter_by(username='your-email@example.com').first()
       user.role = 'Admin'
       db.session.commit()
   ```

## Payroll Calculation

The system calculates payroll based on:
- Basic monthly salary
- Regular hours worked (prorated if less than full month)
- Overtime hours (1.25x rate)
- Late penalties (deducted from pay)
- Statutory deductions (SSS, PhilHealth, Pag-IBIG)
- Withholding tax (BIR TRAIN Law)

## License

[Specify your license here]

## Support

For issues and questions, please open an issue in the repository.

