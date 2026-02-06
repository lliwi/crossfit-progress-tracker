from datetime import date

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from app.models import db, Skill, UserSkill

skills_bp = Blueprint('skills', __name__, template_folder='../templates')


@skills_bp.route('/')
@login_required
def index():
    skills = Skill.query.order_by(Skill.name).all()

    # Get user's unlocked skill IDs
    unlocked_ids = {
        us.skill_id
        for us in UserSkill.query.filter_by(user_id=current_user.id).all()
    }

    # Build list with unlock status
    skills_data = []
    for skill in skills:
        user_skill = None
        if skill.id in unlocked_ids:
            user_skill = UserSkill.query.filter_by(
                user_id=current_user.id, skill_id=skill.id
            ).first()
        skills_data.append({
            'skill': skill,
            'unlocked': skill.id in unlocked_ids,
            'user_skill': user_skill,
        })

    return render_template('skills/index.html', skills_data=skills_data)


@skills_bp.route('/toggle/<int:skill_id>', methods=['POST'])
@login_required
def toggle(skill_id):
    skill = Skill.query.get_or_404(skill_id)
    user_skill = UserSkill.query.filter_by(
        user_id=current_user.id, skill_id=skill_id
    ).first()

    if user_skill:
        db.session.delete(user_skill)
        flash(f'{skill.name} desmarcado.', 'info')
    else:
        user_skill = UserSkill(
            user_id=current_user.id,
            skill_id=skill_id,
            unlocked_date=date.today(),
        )
        db.session.add(user_skill)
        flash(f'{skill.name} desbloqueado!', 'success')

    db.session.commit()
    return redirect(url_for('skills.index'))
