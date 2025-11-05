# app/employee/__init__.py

from flask import Blueprint

bp = Blueprint('employee', __name__, template_folder='templates', url_prefix='/employee')
# This line is CRITICAL for discovering routes
from . import routes