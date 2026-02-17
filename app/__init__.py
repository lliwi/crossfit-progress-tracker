import os

from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect

from app.config import config
from app.models import db, Exercise, Skill, Benchmark

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Por favor, inicia sesion para acceder.'
migrate = Migrate()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, default_limits=[])

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

DEFAULT_BENCHMARKS = [
    ('Fran', 'for_time',
     '21-15-9 reps:\n- Thrusters (43/30 kg)\n- Pull-ups'),
    ('Grace', 'for_time',
     '30 reps:\n- Clean & Jerk (61/43 kg)'),
    ('Isabel', 'for_time',
     '30 reps:\n- Snatch (61/43 kg)'),
    ('Diane', 'for_time',
     '21-15-9 reps:\n- Deadlifts (102/70 kg)\n- Handstand Push-ups'),
    ('Elizabeth', 'for_time',
     '21-15-9 reps:\n- Cleans (61/43 kg)\n- Ring Dips'),
    ('Amanda', 'for_time',
     '9-7-5 reps:\n- Muscle-ups\n- Squat Snatch (61/43 kg)'),
    ('Jackie', 'for_time',
     '- 1000m Row\n- 50 Thrusters (20/15 kg)\n- 30 Pull-ups'),
    ('Karen', 'for_time',
     '- 150 Wall Balls (9/6 kg)'),
    ('Murph', 'for_time',
     'Con chaleco (9/6 kg):\n- 1.6 km Run\n- 100 Pull-ups\n- 200 Push-ups\n- 300 Air Squats\n- 1.6 km Run'),
    ('DT', 'for_time',
     '5 rounds (70/47 kg):\n- 12 Deadlifts\n- 9 Hang Power Cleans\n- 6 Push Jerks'),
    ('Kalsu', 'for_time',
     '- 100 Thrusters (61/43 kg)\n- EMOM 5 Burpees'),
    ('Cindy', 'amrap',
     '20 min AMRAP:\n- 5 Pull-ups\n- 10 Push-ups\n- 15 Air Squats'),
    ('Mary', 'amrap',
     '20 min AMRAP:\n- 5 Handstand Push-ups\n- 10 Pistols\n- 15 Pull-ups'),
    ('Chelsea', 'amrap',
     '30 min EMOM:\n- 5 Pull-ups\n- 10 Push-ups\n- 15 Air Squats'),
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
    limiter.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    from app.blueprints.auth import auth_bp
    from app.blueprints.dashboard import dashboard_bp
    from app.blueprints.lifts import lifts_bp
    from app.blueprints.skills import skills_bp
    from app.blueprints.profile import profile_bp
    from app.blueprints.benchmarks import benchmarks_bp
    from app.blueprints.timer import timer_bp
    from app.blueprints.wods import wods_bp
    from app.blueprints.admin import admin_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/')
    app.register_blueprint(lifts_bp, url_prefix='/lifts')
    app.register_blueprint(skills_bp, url_prefix='/skills')
    app.register_blueprint(profile_bp, url_prefix='/profile')
    app.register_blueprint(benchmarks_bp, url_prefix='/benchmarks')
    app.register_blueprint(timer_bp, url_prefix='/timer')
    app.register_blueprint(wods_bp, url_prefix='/wods')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    with app.app_context():
        seed_defaults()
        _log_pending_invitations(app)

    return app


def _log_pending_invitations(app):
    """Log pending invitation URLs on startup."""
    from app.models import Invitation
    try:
        pending = Invitation.query.filter_by(used_by=None).all()
    except Exception:
        return
    if not pending:
        return
    base_url = app.config.get('BASE_URL', 'http://localhost:5000').rstrip('/')
    app.logger.info('=== Invitaciones pendientes ===')
    for inv in pending:
        app.logger.info('  %s/auth/register?token=%s', base_url, inv.token)


def seed_defaults():
    """Seed default exercises and skills if they don't exist."""
    from sqlalchemy import inspect, text
    from sqlalchemy.exc import OperationalError

    try:
        inspector = inspect(db.engine)
    except OperationalError:
        return

    if not inspector.has_table('exercises') or not inspector.has_table('benchmarks'):
        return

    try:
        db.session.execute(text('LOCK TABLE exercises IN EXCLUSIVE MODE'))
        db.session.execute(text('LOCK TABLE skills IN EXCLUSIVE MODE'))
        db.session.execute(text('LOCK TABLE benchmarks IN EXCLUSIVE MODE'))

        for name in DEFAULT_EXERCISES:
            if not Exercise.query.filter_by(name=name).first():
                db.session.add(Exercise(name=name, is_default=True))

        for name in DEFAULT_SKILLS:
            if not Skill.query.filter_by(name=name).first():
                db.session.add(Skill(name=name, is_default=True))

        for name, benchmark_type, description in DEFAULT_BENCHMARKS:
            if not Benchmark.query.filter_by(name=name).first():
                db.session.add(Benchmark(
                    name=name, benchmark_type=benchmark_type,
                    description=description, is_default=True,
                ))

        db.session.commit()
    except Exception:
        db.session.rollback()
