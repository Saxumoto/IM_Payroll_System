# app/main/__init__.py

from flask import Blueprint

bp = Blueprint('main', __name__, template_folder='templates')

# This line is CRITICAL for discovering routes
from . import routes