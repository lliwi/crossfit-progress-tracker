from datetime import date, datetime

import bcrypt
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    profile_photo = db.Column(db.String(200), nullable=True)
    dark_mode = db.Column(db.Boolean, default=True, nullable=False, server_default='true')
    is_admin = db.Column(db.Boolean, default=False, nullable=False, server_default='false')
    is_active = db.Column(db.Boolean, default=True, nullable=False, server_default='true')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    lifts = db.relationship('Lift', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    user_skills = db.relationship('UserSkill', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    benchmark_results = db.relationship('BenchmarkResult', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    invitations_created = db.relationship(
        'Invitation', foreign_keys='Invitation.created_by',
        backref='creator', lazy='dynamic',
    )

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'), bcrypt.gensalt()
        ).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(
            password.encode('utf-8'),
            self.password_hash.encode('utf-8')
        )


class Exercise(db.Model):
    __tablename__ = 'exercises'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    is_default = db.Column(db.Boolean, default=False)

    lifts = db.relationship('Lift', backref='exercise', lazy='dynamic')


class Lift(db.Model):
    __tablename__ = 'lifts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercises.id'), nullable=False)
    weight = db.Column(db.Float, nullable=False)
    reps_type = db.Column(db.Integer, nullable=False)  # 1 = 1RM, 3 = 3RM
    date = db.Column(db.Date, nullable=False, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Skill(db.Model):
    __tablename__ = 'skills'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    is_default = db.Column(db.Boolean, default=False)

    user_skills = db.relationship('UserSkill', backref='skill', lazy='dynamic')


class UserSkill(db.Model):
    __tablename__ = 'user_skills'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    skill_id = db.Column(db.Integer, db.ForeignKey('skills.id'), nullable=False)
    unlocked_date = db.Column(db.Date, nullable=False, default=date.today)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'skill_id', name='uq_user_skill'),
    )


class Benchmark(db.Model):
    __tablename__ = 'benchmarks'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    benchmark_type = db.Column(db.String(20), nullable=False)  # 'for_time' or 'amrap'
    is_default = db.Column(db.Boolean, default=False)

    results = db.relationship('BenchmarkResult', backref='benchmark', lazy='dynamic')


class BenchmarkResult(db.Model):
    __tablename__ = 'benchmark_results'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    benchmark_id = db.Column(db.Integer, db.ForeignKey('benchmarks.id'), nullable=False)
    time_seconds = db.Column(db.Integer, nullable=True)
    rounds = db.Column(db.Integer, nullable=True)
    reps = db.Column(db.Integer, nullable=True)
    rx = db.Column(db.Boolean, default=True, nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Invitation(db.Model):
    __tablename__ = 'invitations'

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    used_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    used_at = db.Column(db.DateTime, nullable=True)

    registered_user = db.relationship('User', foreign_keys=[used_by])

    @property
    def is_valid(self):
        return self.used_by is None
