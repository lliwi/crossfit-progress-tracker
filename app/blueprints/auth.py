from urllib.parse import urlparse

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

from app import limiter
from app.models import db, User

auth_bp = Blueprint('auth', __name__, template_folder='../templates')


class LoginForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Recordarme')


class RegisterForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField('Confirmar Password', validators=[
        DataRequired(), EqualTo('password', message='Las passwords no coinciden')
    ])

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('No se puede usar este usuario.')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('No se puede usar este email.')


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10/minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            if next_page:
                parsed = urlparse(next_page)
                if parsed.netloc or parsed.scheme:
                    next_page = None
            return redirect(next_page or url_for('dashboard.index'))
        flash('Usuario o password incorrectos.', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("5/minute")
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    form = RegisterForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Cuenta creada. Ya puedes iniciar sesion.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)


@auth_bp.route('/logout', methods=['POST'])
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
