import os

from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

from app.config import config
from app.models import db, Exercise, Skill

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Por favor, inicia sesion para acceder.'
migrate = Migrate()
csrf = CSRFProtect()

DEFAULT_EXERCISES = [
    'Back Squat', 'Front Squat', 'Deadlift', 'Snatch',
    'Clean & Jerk', 'Clean', 'Overhead Press', 'Bench Press', 
    'Thruster', 'Push Press', 'Power Clean', 'Power Snatch',
]

DEFAULT_SKILLS = [
    'Pull-up', 'Chest-to-bar', 'Muscle-up (bar)', 'Muscle-up (ring)',
    'Handstand Walk', 'Handstand Push-up', 'Pistol Squat',
    'Double Under', 'Toes-to-bar', 'Rope Climb', 'L-sit', 
]


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')

    app = Flask(__name__)
    app.config.from_object(config.get(config_name, config['default']))

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    from app.blueprints.auth import auth_bp
    from app.blueprints.dashboard import dashboard_bp
    from app.blueprints.lifts import lifts_bp
    from app.blueprints.skills import skills_bp
    from app.blueprints.profile import profile_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/')
    app.register_blueprint(lifts_bp, url_prefix='/lifts')
    app.register_blueprint(skills_bp, url_prefix='/skills')
    app.register_blueprint(profile_bp, url_prefix='/profile')

    with app.app_context():
        seed_defaults()

    return app


def seed_defaults():
    """Seed default exercises and skills if they don't exist."""
    from sqlalchemy import inspect, text
    inspector = inspect(db.engine)
    if not inspector.has_table('exercises'):
        return

    try:
        db.session.execute(text('LOCK TABLE exercises IN EXCLUSIVE MODE'))
        db.session.execute(text('LOCK TABLE skills IN EXCLUSIVE MODE'))

        for name in DEFAULT_EXERCISES:
            if not Exercise.query.filter_by(name=name).first():
                db.session.add(Exercise(name=name, is_default=True))

        for name in DEFAULT_SKILLS:
            if not Skill.query.filter_by(name=name).first():
                db.session.add(Skill(name=name, is_default=True))

        db.session.commit()
    except Exception:
        db.session.rollback()
