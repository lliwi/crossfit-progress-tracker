from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy import func

from app.models import db, Lift, Exercise

dashboard_bp = Blueprint('dashboard', __name__, template_folder='../templates')


@dashboard_bp.route('/')
@login_required
def index():
    # Last 5 PRs registered
    recent_lifts = (
        Lift.query
        .filter_by(user_id=current_user.id)
        .order_by(Lift.created_at.desc())
        .limit(5)
        .all()
    )

    # Best 1RM per exercise (subquery for max weight)
    best_1rm_subq = (
        db.session.query(
            Lift.exercise_id,
            func.max(Lift.weight).label('max_weight')
        )
        .filter_by(user_id=current_user.id, reps_type=1)
        .group_by(Lift.exercise_id)
        .subquery()
    )

    best_1rms = (
        db.session.query(Exercise.name, best_1rm_subq.c.max_weight)
        .join(best_1rm_subq, Exercise.id == best_1rm_subq.c.exercise_id)
        .order_by(Exercise.name)
        .all()
    )

    return render_template(
        'dashboard/index.html',
        recent_lifts=recent_lifts,
        best_1rms=best_1rms,
    )
