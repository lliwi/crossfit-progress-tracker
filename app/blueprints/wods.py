import json
import os
from datetime import datetime

from flask import Blueprint, render_template, current_app
from flask_login import login_required

wods_bp = Blueprint('wods', __name__, template_folder='../templates')

DATA_FILENAME = 'week-workout.json'
MAX_REPAIR_ATTEMPTS = 10


def _try_parse_json(raw):
    """Try to parse JSON, repairing missing closing braces/brackets."""
    raw = raw.strip()
    # Trim trailing garbage after last } or ]
    last_brace = max(raw.rfind('}'), raw.rfind(']'))
    if last_brace != -1:
        raw = raw[:last_brace + 1]
    for _ in range(MAX_REPAIR_ATTEMPTS):
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            msg = str(exc)
            if 'Expecting' in msg and ("'}'" in msg or 'delimiter' in msg):
                # Count unmatched openers and append closers
                opens = raw.count('{') - raw.count('}')
                closes = raw.count('[') - raw.count(']')
                if opens <= 0 and closes <= 0:
                    return None
                raw += ']' * closes + '}' * opens
            else:
                return None
    return None


def load_week_data():
    """Load the weekly workout JSON from the data directory."""
    data_path = os.path.join(current_app.root_path, '..', 'data', DATA_FILENAME)
    if not os.path.exists(data_path):
        return None
    with open(data_path, 'r', encoding='utf-8') as f:
        raw = f.read().strip()
    # Try parsing, repairing missing closing braces if needed
    parsed = _try_parse_json(raw)
    if parsed is None:
        return None
    # Unwrap nested data.data structure produced by the parser
    if (isinstance(parsed.get('data'), dict)
            and 'data' in parsed['data']):
        parsed = {
            'metadata': parsed.get('metadata', {}),
            'data': parsed['data']['data'],
        }
    return parsed


@wods_bp.route('/')
@login_required
def index():
    week = load_week_data()
    today_weekday = datetime.now().isoweekday()  # 1=Mon ... 7=Sun
    return render_template('wods/index.html', week=week, today_weekday=today_weekday)
