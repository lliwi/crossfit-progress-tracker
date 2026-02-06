from datetime import date

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import (
    SelectField, IntegerField, BooleanField, DateField,
    TextAreaField, StringField,
)
from wtforms.validators import DataRequired, Optional, NumberRange

from app.models import db, Wod, WodResult

wods_bp = Blueprint('wods', __name__, template_folder='../templates')


class WodResultForm(FlaskForm):
    wod_id = SelectField('WOD', coerce=int, validators=[DataRequired()])
    time_minutes = IntegerField('Minutos', validators=[Optional(), NumberRange(min=0)])
    time_seconds = IntegerField('Segundos', validators=[Optional(), NumberRange(min=0, max=59)])
    rounds = IntegerField('Rondas', validators=[Optional(), NumberRange(min=0)])
    reps = IntegerField('Reps extra', validators=[Optional(), NumberRange(min=0)])
    rx = BooleanField('RX', default=True)
    date = DateField('Fecha', validators=[DataRequired()], default=date.today)
    notes = TextAreaField('Notas', validators=[Optional()])


class EditWodResultForm(FlaskForm):
    time_minutes = IntegerField('Minutos', validators=[Optional(), NumberRange(min=0)])
    time_seconds = IntegerField('Segundos', validators=[Optional(), NumberRange(min=0, max=59)])
    rounds = IntegerField('Rondas', validators=[Optional(), NumberRange(min=0)])
    reps = IntegerField('Reps extra', validators=[Optional(), NumberRange(min=0)])
    rx = BooleanField('RX', default=True)
    date = DateField('Fecha', validators=[DataRequired()])
    notes = TextAreaField('Notas', validators=[Optional()])


def format_time(seconds):
    """Format seconds as MM:SS."""
    if seconds is None:
        return '-'
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"


@wods_bp.route('/')
@login_required
def index():
    wods = Wod.query.order_by(Wod.name).all()
    wod_data = []
    for wod in wods:
        best = get_best_result(wod)
        wod_data.append({'wod': wod, 'best': best})
    return render_template('wods/index.html', wod_data=wod_data, format_time=format_time)


@wods_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    form = WodResultForm()
    wods = Wod.query.order_by(Wod.name).all()
    form.wod_id.choices = [(w.id, f"{w.name} ({w.wod_type.replace('_', ' ').title()})") for w in wods]

    # Build type map for JS
    wod_types = {w.id: w.wod_type for w in wods}

    if form.validate_on_submit():
        wod = Wod.query.get(form.wod_id.data)
        if not wod:
            flash('WOD no encontrado.', 'danger')
            return render_template('wods/add.html', form=form, wod_types=wod_types)

        result = WodResult(
            user_id=current_user.id,
            wod_id=wod.id,
            rx=form.rx.data,
            date=form.date.data,
            notes=form.notes.data or None,
        )

        if wod.wod_type == 'for_time':
            minutes = form.time_minutes.data or 0
            seconds = form.time_seconds.data or 0
            total = minutes * 60 + seconds
            if total <= 0:
                flash('Introduce un tiempo valido.', 'warning')
                return render_template('wods/add.html', form=form, wod_types=wod_types)
            result.time_seconds = total
        else:  # amrap
            if not form.rounds.data and form.rounds.data != 0:
                flash('Introduce las rondas.', 'warning')
                return render_template('wods/add.html', form=form, wod_types=wod_types)
            result.rounds = form.rounds.data
            result.reps = form.reps.data or 0

        db.session.add(result)
        db.session.commit()

        if wod.wod_type == 'for_time':
            score = format_time(result.time_seconds)
        else:
            score = f"{result.rounds}+{result.reps}" if result.reps else f"{result.rounds} rondas"
        rx_label = 'RX' if result.rx else 'Scaled'
        flash(f'{wod.name} - {score} ({rx_label}) registrado!', 'success')
        return redirect(url_for('wods.detail', wod_id=wod.id))

    return render_template('wods/add.html', form=form, wod_types=wod_types)


@wods_bp.route('/<int:wod_id>')
@login_required
def detail(wod_id):
    wod = Wod.query.get_or_404(wod_id)
    results = (
        WodResult.query
        .filter_by(user_id=current_user.id, wod_id=wod_id)
        .order_by(WodResult.date)
        .all()
    )

    chart_data = None
    if results:
        if wod.wod_type == 'for_time':
            chart_data = {
                'labels': [r.date.strftime('%d/%m/%Y') for r in results],
                'data': [r.time_seconds for r in results],
            }
        else:
            chart_data = {
                'labels': [r.date.strftime('%d/%m/%Y') for r in results],
                'data': [r.rounds + (r.reps or 0) / 100 for r in results],
            }

    best = get_best_result(wod)
    return render_template(
        'wods/detail.html',
        wod=wod,
        best=best,
        chart_data=chart_data,
        format_time=format_time,
    )


@wods_bp.route('/history/<int:wod_id>')
@login_required
def history(wod_id):
    wod = Wod.query.get_or_404(wod_id)
    results = (
        WodResult.query
        .filter_by(user_id=current_user.id, wod_id=wod_id)
        .order_by(WodResult.date.desc())
        .all()
    )
    return render_template('wods/history.html', wod=wod, results=results, format_time=format_time)


@wods_bp.route('/edit/<int:result_id>', methods=['GET', 'POST'])
@login_required
def edit(result_id):
    result = WodResult.query.get_or_404(result_id)
    if result.user_id != current_user.id:
        flash('No tienes permiso para editar este resultado.', 'danger')
        return redirect(url_for('wods.index'))

    form = EditWodResultForm(obj=result)

    # Pre-fill time fields on GET
    if request.method == 'GET' and result.time_seconds:
        m, s = divmod(result.time_seconds, 60)
        form.time_minutes.data = m
        form.time_seconds.data = s

    if form.validate_on_submit():
        wod = result.wod
        if wod.wod_type == 'for_time':
            minutes = form.time_minutes.data or 0
            seconds = form.time_seconds.data or 0
            total = minutes * 60 + seconds
            if total <= 0:
                flash('Introduce un tiempo valido.', 'warning')
                return render_template('wods/edit.html', form=form, result=result)
            result.time_seconds = total
        else:
            result.rounds = form.rounds.data
            result.reps = form.reps.data or 0

        result.rx = form.rx.data
        result.date = form.date.data
        result.notes = form.notes.data or None
        db.session.commit()
        flash('Resultado actualizado.', 'success')
        return redirect(url_for('wods.history', wod_id=result.wod_id))

    return render_template('wods/edit.html', form=form, result=result)


@wods_bp.route('/delete/<int:result_id>', methods=['POST'])
@login_required
def delete(result_id):
    result = WodResult.query.get_or_404(result_id)
    if result.user_id != current_user.id:
        flash('No tienes permiso para borrar este resultado.', 'danger')
        return redirect(url_for('wods.index'))

    wod_id = result.wod_id
    db.session.delete(result)
    db.session.commit()
    flash('Resultado eliminado.', 'info')
    return redirect(url_for('wods.history', wod_id=wod_id))


def get_best_result(wod):
    """Get user's best result for a WOD."""
    query = WodResult.query.filter_by(user_id=current_user.id, wod_id=wod.id)
    if wod.wod_type == 'for_time':
        return query.order_by(WodResult.time_seconds.asc()).first()
    else:
        return query.order_by(WodResult.rounds.desc(), WodResult.reps.desc()).first()
