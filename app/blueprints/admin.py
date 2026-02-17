import secrets
from functools import wraps

from flask import (Blueprint, render_template, redirect, url_for, flash,
                    abort, current_app)
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from sqlalchemy import func

from app.models import (db, User, Invitation, Exercise, Lift, Skill,
                         UserSkill, Benchmark, BenchmarkResult)

admin_bp = Blueprint('admin', __name__, template_folder='../templates')


class AdminActionForm(FlaskForm):
    pass


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


# ── Dashboard ─────────────────────────────────────────────────────────

@admin_bp.route('/')
@admin_required
def index():
    stats = {
        'users': User.query.count(),
        'lifts': Lift.query.count(),
        'skills': UserSkill.query.count(),
        'benchmarks': Benchmark.query.count(),
        'results': BenchmarkResult.query.count(),
    }

    lifts_by_exercise = (
        db.session.query(Exercise.name, func.count(Lift.id))
        .join(Lift, Lift.exercise_id == Exercise.id)
        .group_by(Exercise.name)
        .order_by(func.count(Lift.id).desc())
        .all()
    )

    top_benchmarks = (
        db.session.query(Benchmark.name, func.count(BenchmarkResult.id))
        .join(BenchmarkResult, BenchmarkResult.benchmark_id == Benchmark.id)
        .group_by(Benchmark.name)
        .order_by(func.count(BenchmarkResult.id).desc())
        .limit(10)
        .all()
    )

    last_lift = (
        Lift.query
        .join(User).join(Exercise)
        .order_by(Lift.created_at.desc())
        .first()
    )

    return render_template(
        'admin/index.html',
        stats=stats,
        lifts_by_exercise=lifts_by_exercise,
        top_benchmarks=top_benchmarks,
        last_lift=last_lift,
        form=AdminActionForm(),
    )


# ── Users ─────────────────────────────────────────────────────────────

@admin_bp.route('/users')
@admin_required
def users():
    all_users = User.query.order_by(User.id).all()
    return render_template(
        'admin/users.html',
        users=all_users,
        form=AdminActionForm(),
    )


@admin_bp.route('/users/<int:id>/toggle-admin', methods=['POST'])
@admin_required
def toggle_admin(id):
    form = AdminActionForm()
    if form.validate_on_submit():
        user = User.query.get_or_404(id)
        if user.id == current_user.id:
            flash('No puedes cambiar tu propio rol de admin.', 'danger')
            return redirect(url_for('admin.users'))
        user.is_admin = not user.is_admin
        db.session.commit()
        role = 'admin' if user.is_admin else 'usuario'
        flash(f'{user.username} ahora es {role}.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:id>/toggle-active', methods=['POST'])
@admin_required
def toggle_active(id):
    form = AdminActionForm()
    if form.validate_on_submit():
        user = User.query.get_or_404(id)
        if user.id == current_user.id:
            flash('No puedes desactivarte a ti mismo.', 'danger')
            return redirect(url_for('admin.users'))
        user.is_active = not user.is_active
        db.session.commit()
        estado = 'activado' if user.is_active else 'desactivado'
        flash(f'{user.username} ha sido {estado}.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:id>/reset-password', methods=['POST'])
@admin_required
def reset_password(id):
    form = AdminActionForm()
    if form.validate_on_submit():
        user = User.query.get_or_404(id)
        temp_password = secrets.token_urlsafe(8)
        user.set_password(temp_password)
        db.session.commit()
        flash(f'Nueva password temporal para {user.username}: {temp_password}', 'warning')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:id>/delete', methods=['POST'])
@admin_required
def delete_user(id):
    form = AdminActionForm()
    if form.validate_on_submit():
        user = User.query.get_or_404(id)
        if user.id == current_user.id:
            flash('No puedes eliminarte a ti mismo.', 'danger')
            return redirect(url_for('admin.users'))
        username = user.username
        Invitation.query.filter_by(created_by=user.id).update({'created_by': None})
        Invitation.query.filter_by(used_by=user.id).update({'used_by': None})
        db.session.delete(user)
        db.session.commit()
        flash(f'Usuario {username} eliminado.', 'success')
    return redirect(url_for('admin.users'))


# ── Invitations ───────────────────────────────────────────────────────

@admin_bp.route('/invitations')
@admin_required
def invitations():
    all_invitations = (Invitation.query
                       .order_by(Invitation.created_at.desc())
                       .all())
    base_url = current_app.config['BASE_URL'].rstrip('/')
    return render_template(
        'admin/invitations.html',
        invitations=all_invitations,
        base_url=base_url,
        form=AdminActionForm(),
    )


@admin_bp.route('/invitations/generate', methods=['POST'])
@admin_required
def generate_invitation():
    form = AdminActionForm()
    if form.validate_on_submit():
        invitation = Invitation(token=secrets.token_urlsafe(32))
        db.session.add(invitation)
        db.session.commit()
        flash('Invitacion de sistema generada.', 'success')
    return redirect(url_for('admin.invitations'))


@admin_bp.route('/invitations/<int:id>/revoke', methods=['POST'])
@admin_required
def revoke_invitation(id):
    form = AdminActionForm()
    if form.validate_on_submit():
        invitation = Invitation.query.get_or_404(id)
        if not invitation.is_valid:
            flash('No se puede revocar una invitacion ya usada.', 'danger')
            return redirect(url_for('admin.invitations'))
        db.session.delete(invitation)
        db.session.commit()
        flash('Invitacion revocada.', 'success')
    return redirect(url_for('admin.invitations'))
