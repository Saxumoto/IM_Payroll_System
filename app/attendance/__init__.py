# app/attendance/__init__.py

from flask import Blueprint

bp = Blueprint('attendance', __name__, template_folder='templates', url_prefix='/attendance')

# This line is CRITICAL for discovering routes
from . import routes