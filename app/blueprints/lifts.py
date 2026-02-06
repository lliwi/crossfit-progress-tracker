from datetime import date

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from sqlalchemy import func
from wtforms import FloatField, SelectField, DateField, StringField, IntegerField
from wtforms.validators import DataRequired, NumberRange, Optional

from app.models import db, Lift, Exercise

lifts_bp = Blueprint('lifts', __name__, template_folder='../templates')


class LiftForm(FlaskForm):
    exercise_id = SelectField('Ejercicio', coerce=int, validators=[Optional()])
    new_exercise = StringField('Ejercicio personalizado')
    weight = FloatField('Peso (kg)', validators=[DataRequired(), NumberRange(min=0.5)])
    reps_type = SelectField('Tipo', coerce=int, choices=[(1, '1RM'), (3, '3RM')],
                            validators=[DataRequired()])
    date = DateField('Fecha', validators=[DataRequired()], default=date.today)


class EditLiftForm(FlaskForm):
    weight = FloatField('Peso (kg)', validators=[DataRequired(), NumberRange(min=0.5)])
    reps_type = SelectField('Tipo', coerce=int, choices=[(1, '1RM'), (3, '3RM')],
                            validators=[DataRequired()])
    date = DateField('Fecha', validators=[DataRequired()])


def calculate_percentages(weight):
    percentages = [0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95]
    return {f"{int(p * 100)}%": round(weight * p, 1) for p in percentages}


@lifts_bp.route('/')
@login_required
def index():
    """List exercises with best 1RM and 3RM for each."""
    # Get all exercises that the user has lifts for
    user_exercises = (
        db.session.query(Exercise)
        .join(Lift)
        .filter(Lift.user_id == current_user.id)
        .distinct()
        .order_by(Exercise.name)
        .all()
    )

    exercise_data = []
    for ex in user_exercises:
        best_1rm = (
            Lift.query
            .filter_by(user_id=current_user.id, exercise_id=ex.id, reps_type=1)
            .order_by(Lift.weight.desc())
            .first()
        )
        best_3rm = (
            Lift.query
            .filter_by(user_id=current_user.id, exercise_id=ex.id, reps_type=3)
            .order_by(Lift.weight.desc())
            .first()
        )
        exercise_data.append({
            'exercise': ex,
            'best_1rm': best_1rm,
            'best_3rm': best_3rm,
        })

    return render_template('lifts/index.html', exercise_data=exercise_data)


@lifts_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    form = LiftForm()

    # Populate exercise choices
    exercises = Exercise.query.order_by(Exercise.name).all()
    form.exercise_id.choices = [(0, '-- Seleccionar --')] + [(e.id, e.name) for e in exercises]

    if form.validate_on_submit():
        # Determine exercise: existing or new custom one
        if form.new_exercise.data and form.new_exercise.data.strip():
            exercise_name = form.new_exercise.data.strip()
            exercise = Exercise.query.filter(
                func.lower(Exercise.name) == func.lower(exercise_name)
            ).first()
            if not exercise:
                exercise = Exercise(name=exercise_name, is_default=False)
                db.session.add(exercise)
                db.session.flush()
        elif form.exercise_id.data and form.exercise_id.data > 0:
            exercise = Exercise.query.get(form.exercise_id.data)
            if not exercise:
                flash('Ejercicio no encontrado.', 'danger')
                return render_template('lifts/add.html', form=form)
        else:
            flash('Selecciona un ejercicio o introduce uno nuevo.', 'warning')
            return render_template('lifts/add.html', form=form)

        lift = Lift(
            user_id=current_user.id,
            exercise_id=exercise.id,
            weight=form.weight.data,
            reps_type=form.reps_type.data,
            date=form.date.data,
        )
        db.session.add(lift)
        db.session.commit()

        flash(f'{exercise.name} - {form.weight.data} kg ({form.reps_type.data}RM) registrado!', 'success')
        return redirect(url_for('lifts.exercise_detail', exercise_id=exercise.id))

    return render_template('lifts/add.html', form=form)


@lifts_bp.route('/exercise/<int:exercise_id>')
@login_required
def exercise_detail(exercise_id):
    exercise = Exercise.query.get_or_404(exercise_id)

    # Best 1RM for percentage table
    best_1rm = (
        Lift.query
        .filter_by(user_id=current_user.id, exercise_id=exercise_id, reps_type=1)
        .order_by(Lift.weight.desc())
        .first()
    )

    percentages = None
    if best_1rm:
        percentages = calculate_percentages(best_1rm.weight)

    # All lifts for chart (ordered by date)
    lifts_1rm = (
        Lift.query
        .filter_by(user_id=current_user.id, exercise_id=exercise_id, reps_type=1)
        .order_by(Lift.date)
        .all()
    )
    lifts_3rm = (
        Lift.query
        .filter_by(user_id=current_user.id, exercise_id=exercise_id, reps_type=3)
        .order_by(Lift.date)
        .all()
    )

    # Chart data
    chart_data = {
        '1rm': {
            'labels': [l.date.strftime('%d/%m/%Y') for l in lifts_1rm],
            'data': [l.weight for l in lifts_1rm],
        },
        '3rm': {
            'labels': [l.date.strftime('%d/%m/%Y') for l in lifts_3rm],
            'data': [l.weight for l in lifts_3rm],
        },
    }

    return render_template(
        'lifts/exercise.html',
        exercise=exercise,
        best_1rm=best_1rm,
        percentages=percentages,
        chart_data=chart_data,
    )


@lifts_bp.route('/history/<int:exercise_id>')
@login_required
def history(exercise_id):
    exercise = Exercise.query.get_or_404(exercise_id)
    lifts = (
        Lift.query
        .filter_by(user_id=current_user.id, exercise_id=exercise_id)
        .order_by(Lift.date.desc())
        .all()
    )
    return render_template('lifts/history.html', exercise=exercise, lifts=lifts)


@lifts_bp.route('/edit/<int:lift_id>', methods=['GET', 'POST'])
@login_required
def edit(lift_id):
    lift = Lift.query.get_or_404(lift_id)
    if lift.user_id != current_user.id:
        flash('No tienes permiso para editar esta marca.', 'danger')
        return redirect(url_for('lifts.index'))

    form = EditLiftForm(obj=lift)

    if form.validate_on_submit():
        lift.weight = form.weight.data
        lift.reps_type = form.reps_type.data
        lift.date = form.date.data
        db.session.commit()
        flash('Marca actualizada.', 'success')
        return redirect(url_for('lifts.history', exercise_id=lift.exercise_id))

    return render_template('lifts/edit.html', form=form, lift=lift)


@lifts_bp.route('/delete/<int:lift_id>', methods=['POST'])
@login_required
def delete(lift_id):
    lift = Lift.query.get_or_404(lift_id)
    if lift.user_id != current_user.id:
        flash('No tienes permiso para borrar esta marca.', 'danger')
        return redirect(url_for('lifts.index'))

    exercise_id = lift.exercise_id
    db.session.delete(lift)
    db.session.commit()
    flash('Marca eliminada.', 'info')
    return redirect(url_for('lifts.history', exercise_id=exercise_id))
