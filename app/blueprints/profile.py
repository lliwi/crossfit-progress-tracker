import os

from flask import (Blueprint, render_template, redirect, url_for, flash,
                    current_app, make_response)
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from PIL import Image
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

from app.models import db, User

profile_bp = Blueprint('profile', __name__, template_folder='../templates')

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Password actual', validators=[DataRequired()])
    new_password = PasswordField('Nueva password', validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField('Confirmar nueva password', validators=[
        DataRequired(), EqualTo('new_password', message='Las passwords no coinciden')
    ])


class ChangeEmailForm(FlaskForm):
    email = StringField('Nuevo email', validators=[DataRequired(), Email()])

    def validate_email(self, field):
        if field.data == current_user.email:
            raise ValidationError('El email es el mismo que el actual.')
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Este email ya esta registrado.')


class ProfilePhotoForm(FlaskForm):
    photo = FileField('Foto de perfil', validators=[
        FileAllowed(ALLOWED_EXTENSIONS, 'Solo imagenes (jpg, png, gif)')
    ])


@profile_bp.route('/')
@login_required
def index():
    password_form = ChangePasswordForm()
    email_form = ChangeEmailForm()
    photo_form = ProfilePhotoForm()
    return render_template(
        'profile/index.html',
        password_form=password_form,
        email_form=email_form,
        photo_form=photo_form,
    )


@profile_bp.route('/password', methods=['POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('La password actual es incorrecta.', 'danger')
            return redirect(url_for('profile.index'))

        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash('Password actualizada correctamente.', 'success')
        return redirect(url_for('profile.index'))

    for field, errors in form.errors.items():
        for error in errors:
            flash(error, 'danger')
    return redirect(url_for('profile.index'))


@profile_bp.route('/email', methods=['POST'])
@login_required
def change_email():
    form = ChangeEmailForm()
    if form.validate_on_submit():
        current_user.email = form.email.data
        db.session.commit()
        flash('Email actualizado correctamente.', 'success')
        return redirect(url_for('profile.index'))

    for field, errors in form.errors.items():
        for error in errors:
            flash(error, 'danger')
    return redirect(url_for('profile.index'))


@profile_bp.route('/theme', methods=['POST'])
@login_required
def toggle_theme():
    current_user.dark_mode = not current_user.dark_mode
    db.session.commit()
    mode = 'oscuro' if current_user.dark_mode else 'claro'
    flash(f'Modo {mode} activado.', 'success')
    resp = make_response(redirect(url_for('profile.index')))
    resp.set_cookie('theme', 'dark' if current_user.dark_mode else 'light',
                     max_age=60 * 60 * 24 * 365, samesite='Lax',
                     httponly=True, secure=not current_app.debug)
    return resp


@profile_bp.route('/photo', methods=['POST'])
@login_required
def change_photo():
    form = ProfilePhotoForm()
    if form.validate_on_submit():
        photo = form.photo.data
        if not photo:
            flash('Selecciona una imagen.', 'warning')
            return redirect(url_for('profile.index'))

        # Validate it's a real image
        try:
            img = Image.open(photo)
            img.verify()
            photo.seek(0)
        except Exception:
            flash('El archivo no es una imagen valida.', 'danger')
            return redirect(url_for('profile.index'))

        # Delete old photo if exists
        if current_user.profile_photo:
            old_path = os.path.realpath(
                os.path.join(current_app.config['UPLOAD_FOLDER'], current_user.profile_photo)
            )
            upload_real = os.path.realpath(current_app.config['UPLOAD_FOLDER'])
            if old_path.startswith(upload_real + os.sep) and os.path.exists(old_path):
                os.remove(old_path)

        # Save new photo
        ext = photo.filename.rsplit('.', 1)[1].lower()
        filename = f"{current_user.id}.{ext}"
        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        photo.save(os.path.join(upload_folder, filename))

        current_user.profile_photo = filename
        db.session.commit()
        flash('Foto de perfil actualizada.', 'success')
        return redirect(url_for('profile.index'))

    for field, errors in form.errors.items():
        for error in errors:
            flash(error, 'danger')
    return redirect(url_for('profile.index'))
