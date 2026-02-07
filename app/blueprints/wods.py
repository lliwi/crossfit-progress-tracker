import json
import os
from datetime import datetime

from flask import Blueprint, render_template, current_app
from flask_login import login_required

wods_bp = Blueprint('wods', __name__, template_folder='../templates')

DATA_FILENAME = 'week-workout.json'


def load_week_data():
    """Load the weekly workout JSON from the data directory."""
    data_path = os.path.join(current_app.root_path, '..', 'data', DATA_FILENAME)
    if not os.path.exists(data_path):
        return None
    with open(data_path, 'r', encoding='utf-8') as f:
        raw = f.read().strip()
    # Sanitize: trim trailing garbage after last }
    last_brace = raw.rfind('}')
    if last_brace != -1:
        raw = raw[:last_brace + 1]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


@wods_bp.route('/')
@login_required
def index():
    week = load_week_data()
    today_weekday = datetime.now().isoweekday()  # 1=Mon ... 7=Sun
    return render_template('wods/index.html', week=week, today_weekday=today_weekday)
