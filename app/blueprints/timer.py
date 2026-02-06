from flask import Blueprint, render_template
from flask_login import login_required

timer_bp = Blueprint('timer', __name__, template_folder='../templates')


@timer_bp.route('/')
@login_required
def index():
    return render_template('timer/index.html')
