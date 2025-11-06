# migrations/env.py

import os
import sys
from logging.config import fileConfig

# CRITICAL FIX: Add the project directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import Flask app components
from app import create_app, db
from app.models.user import User # Ensure all models are imported here

from alembic import context
from flask import current_app

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# --- NEW FIX: Explicitly resolve alembic.ini path for fileConfig ---
# The alembic.ini file is in the parent directory of this env.py file.
if config.config_file_name is not None:
    # Use os.path.dirname(__file__) which is the 'migrations' directory
    # and then go up one level to find 'alembic.ini'
    alembic_ini_path = os.path.join(os.path.dirname(__file__), '..', 'alembic.ini')
    
    # Use the resolved path for fileConfig, as the Alembic provided path may be incorrect.
    if os.path.exists(alembic_ini_path):
        fileConfig(alembic_ini_path)
    else:
        # Fallback to the original path provided by Alembic context if custom path fails
        fileConfig(config.config_file_name)

# Define target_metadata to use Flask-SQLAlchemy's metadata
target_metadata = db.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def run_migrations_offline():
    """Run migrations in 'offline' mode.
    This configures the context with just a URL
    and not an Engine, though an Engine a
    """
    # Initialize the app to get config data
    app = create_app(os.environ.get('FLASK_ENV', 'default'))
    
    url = app.config['SQLALCHEMY_DATABASE_URI']
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"has_table": False},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    # This callback sets up the Flask-SQLAlchemy integration
    def process_revision_directives(context, revision, directives):
        if current_app.config.get("ALEMBIC_SKIP_AUTO_CREATE"):
            directives[:] = []

    # Initialize the Flask app context
    app = create_app(os.environ.get('FLASK_ENV', 'default'))
    
    with app.app_context():
        # Pass the metadata from our db instance to Alembic
        connectable = db.get_engine()
        target_metadata = db.metadata

        context.configure(
            connection=connectable.connect(),
            target_metadata=target_metadata,
            process_revision_directives=process_revision_directives,
            **current_app.extensions["migrate"].configure_args
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()