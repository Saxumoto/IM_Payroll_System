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
            return redirect(url_for('main.dashboard'))
        else:
            return redirect(url_for('employee.dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        
        # --- THIS IS THE FIX for the Admin Name ---
        # We now save the full_name from the form
        user = User(
            username=form.email.data, 
            full_name=form.full_name.data
        )
        user.set_password(form.password.data)
        
        # Assign 'Admin' role to the first user
        if User.query.count() == 0:
            user.role = 'Admin'
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please sign in.', 'success')
        return redirect(url_for('auth.signin'))
        
    return render_template('auth/signup.html', form=form)


@bp.route('/signin', methods=['GET', 'POST'])
def signin():
    if current_user.is_authenticated:
        if current_user.role == 'Admin':
            return redirect(url_for('main.dashboard'))
        else:
            return redirect(url_for('employee.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.email.data).first()
        
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password.', 'danger')
            return redirect(url_for('auth.signin'))
            
        login_user(user, remember=False)
        
        # --- THIS IS THE FIX for the Redirect ---
        if user.role == 'Admin':
            return redirect(url_for('main.dashboard'))
        elif user.role == 'Employee':
            return redirect(url_for('employee.dashboard'))
        else:
            return redirect(url_for('main.welcome'))
        
    return render_template('auth/signin.html', form=form)


@bp.route('/signout')
def signout():
    logout_user()
    return redirect(url_for('main.welcome'))