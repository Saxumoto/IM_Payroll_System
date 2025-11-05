# app/hr/__init__.py

from flask import Blueprint

bp = Blueprint('hr', __name__, template_folder='templates', url_prefix='/hr')

# This line is CRITICAL for discovering routes
from . import routes