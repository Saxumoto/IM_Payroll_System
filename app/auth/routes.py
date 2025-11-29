# app/auth/routes.py

from flask import render_template, redirect, url_for, request, flash
from flask_login import current_user, login_user, logout_user
from app.auth import bp 
from app.models.user import User
from app import db
from .forms import LoginForm, RegistrationForm

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        if current_user.role == 'Admin':
            return redirect(url_for('main.admin_dashboard'))
        else:
            return redirect(url_for('employee.dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.email.data, 
            full_name=form.full_name.data,
            role='Employee' # FIX: Force all public registrations to be 'Employee'
        )
        user.set_password(form.password.data)
        
        # NOTE: Auto-admin logic removed for security.
        # To create an Admin, manually update the database row.
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please sign in.', 'success')
        return redirect(url_for('auth.signin'))
        
    return render_template('auth/signup.html', form=form)


@bp.route('/signin', methods=['GET', 'POST'])
def signin():
    if current_user.is_authenticated:
        if current_user.role == 'Admin':
            return redirect(url_for('main.admin_dashboard'))
        else:
            return redirect(url_for('employee.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.email.data).first()
        
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password.', 'danger')
            return redirect(url_for('auth.signin'))
            
        login_user(user, remember=False)
        
        if user.role == 'Admin':
            return redirect(url_for('main.admin_dashboard'))
        elif user.role == 'Employee':
            if user.employee: 
                return redirect(url_for('employee.dashboard'))
            else:
                flash('Your account is awaiting HR setup. Please contact your administrator.', 'warning')
                return redirect(url_for('main.welcome'))
        else:
            return redirect(url_for('main.welcome'))
        
    return render_template('auth/signin.html', form=form)


@bp.route('/signout')
def signout():
    logout_user()
    return redirect(url_for('main.welcome'))