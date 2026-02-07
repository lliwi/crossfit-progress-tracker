from datetime import date

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import (
    SelectField, IntegerField, BooleanField, DateField,
    TextAreaField, StringField,
)
from wtforms.validators import DataRequired, Optional, NumberRange

from app.models import db, Benchmark, BenchmarkResult

benchmarks_bp = Blueprint('benchmarks', __name__, template_folder='../templates')


class BenchmarkResultForm(FlaskForm):
    benchmark_id = SelectField('Benchmark', coerce=int, validators=[DataRequired()])
    time_minutes = IntegerField('Minutos', validators=[Optional(), NumberRange(min=0)])
    time_seconds = IntegerField('Segundos', validators=[Optional(), NumberRange(min=0, max=59)])
    rounds = IntegerField('Rondas', validators=[Optional(), NumberRange(min=0)])
    reps = IntegerField('Reps extra', validators=[Optional(), NumberRange(min=0)])
    rx = BooleanField('RX', default=True)
    date = DateField('Fecha', validators=[DataRequired()], default=date.today)
    notes = TextAreaField('Notas', validators=[Optional()])


class EditBenchmarkResultForm(FlaskForm):
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


@benchmarks_bp.route('/')
@login_required
def index():
    benchmarks = Benchmark.query.order_by(Benchmark.name).all()
    benchmark_data = []
    for bm in benchmarks:
        best = get_best_result(bm)
        benchmark_data.append({'benchmark': bm, 'best': best})
    return render_template('benchmarks/index.html', benchmark_data=benchmark_data, format_time=format_time)


@benchmarks_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    form = BenchmarkResultForm()
    benchmarks = Benchmark.query.order_by(Benchmark.name).all()
    form.benchmark_id.choices = [(b.id, f"{b.name} ({b.benchmark_type.replace('_', ' ').title()})") for b in benchmarks]

    # Build type map for JS
    benchmark_types = {b.id: b.benchmark_type for b in benchmarks}

    if form.validate_on_submit():
        bm = Benchmark.query.get(form.benchmark_id.data)
        if not bm:
            flash('Benchmark no encontrado.', 'danger')
            return render_template('benchmarks/add.html', form=form, benchmark_types=benchmark_types)

        result = BenchmarkResult(
            user_id=current_user.id,
            benchmark_id=bm.id,
            rx=form.rx.data,
            date=form.date.data,
            notes=form.notes.data or None,
        )

        if bm.benchmark_type == 'for_time':
            minutes = form.time_minutes.data or 0
            seconds = form.time_seconds.data or 0
            total = minutes * 60 + seconds
            if total <= 0:
                flash('Introduce un tiempo valido.', 'warning')
                return render_template('benchmarks/add.html', form=form, benchmark_types=benchmark_types)
            result.time_seconds = total
        else:  # amrap
            if not form.rounds.data and form.rounds.data != 0:
                flash('Introduce las rondas.', 'warning')
                return render_template('benchmarks/add.html', form=form, benchmark_types=benchmark_types)
            result.rounds = form.rounds.data
            result.reps = form.reps.data or 0

        db.session.add(result)
        db.session.commit()

        if bm.benchmark_type == 'for_time':
            score = format_time(result.time_seconds)
        else:
            score = f"{result.rounds}+{result.reps}" if result.reps else f"{result.rounds} rondas"
        rx_label = 'RX' if result.rx else 'Scaled'
        flash(f'{bm.name} - {score} ({rx_label}) registrado!', 'success')
        return redirect(url_for('benchmarks.detail', benchmark_id=bm.id))

    return render_template('benchmarks/add.html', form=form, benchmark_types=benchmark_types)


@benchmarks_bp.route('/<int:benchmark_id>')
@login_required
def detail(benchmark_id):
    bm = Benchmark.query.get_or_404(benchmark_id)
    results = (
        BenchmarkResult.query
        .filter_by(user_id=current_user.id, benchmark_id=benchmark_id)
        .order_by(BenchmarkResult.date)
        .all()
    )

    chart_data = None
    if results:
        if bm.benchmark_type == 'for_time':
            chart_data = {
                'labels': [r.date.strftime('%d/%m/%Y') for r in results],
                'data': [r.time_seconds for r in results],
            }
        else:
            chart_data = {
                'labels': [r.date.strftime('%d/%m/%Y') for r in results],
                'data': [r.rounds + (r.reps or 0) / 100 for r in results],
            }

    best = get_best_result(bm)
    return render_template(
        'benchmarks/detail.html',
        benchmark=bm,
        best=best,
        chart_data=chart_data,
        format_time=format_time,
    )


@benchmarks_bp.route('/history/<int:benchmark_id>')
@login_required
def history(benchmark_id):
    bm = Benchmark.query.get_or_404(benchmark_id)
    results = (
        BenchmarkResult.query
        .filter_by(user_id=current_user.id, benchmark_id=benchmark_id)
        .order_by(BenchmarkResult.date.desc())
        .all()
    )
    return render_template('benchmarks/history.html', benchmark=bm, results=results, format_time=format_time)


@benchmarks_bp.route('/edit/<int:result_id>', methods=['GET', 'POST'])
@login_required
def edit(result_id):
    result = BenchmarkResult.query.get_or_404(result_id)
    if result.user_id != current_user.id:
        flash('No tienes permiso para editar este resultado.', 'danger')
        return redirect(url_for('benchmarks.index'))

    form = EditBenchmarkResultForm(obj=result)

    # Pre-fill time fields on GET
    if request.method == 'GET' and result.time_seconds:
        m, s = divmod(result.time_seconds, 60)
        form.time_minutes.data = m
        form.time_seconds.data = s

    if form.validate_on_submit():
        bm = result.benchmark
        if bm.benchmark_type == 'for_time':
            minutes = form.time_minutes.data or 0
            seconds = form.time_seconds.data or 0
            total = minutes * 60 + seconds
            if total <= 0:
                flash('Introduce un tiempo valido.', 'warning')
                return render_template('benchmarks/edit.html', form=form, result=result)
            result.time_seconds = total
        else:
            result.rounds = form.rounds.data
            result.reps = form.reps.data or 0

        result.rx = form.rx.data
        result.date = form.date.data
        result.notes = form.notes.data or None
        db.session.commit()
        flash('Resultado actualizado.', 'success')
        return redirect(url_for('benchmarks.history', benchmark_id=result.benchmark_id))

    return render_template('benchmarks/edit.html', form=form, result=result)


@benchmarks_bp.route('/delete/<int:result_id>', methods=['POST'])
@login_required
def delete(result_id):
    result = BenchmarkResult.query.get_or_404(result_id)
    if result.user_id != current_user.id:
        flash('No tienes permiso para borrar este resultado.', 'danger')
        return redirect(url_for('benchmarks.index'))

    benchmark_id = result.benchmark_id
    db.session.delete(result)
    db.session.commit()
    flash('Resultado eliminado.', 'info')
    return redirect(url_for('benchmarks.history', benchmark_id=benchmark_id))


def get_best_result(bm):
    """Get user's best result for a benchmark."""
    query = BenchmarkResult.query.filter_by(user_id=current_user.id, benchmark_id=bm.id)
    if bm.benchmark_type == 'for_time':
        return query.order_by(BenchmarkResult.time_seconds.asc()).first()
    else:
        return query.order_by(BenchmarkResult.rounds.desc(), BenchmarkResult.reps.desc()).first()
