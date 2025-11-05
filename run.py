import os
from app import create_app, db
from app.models.user import User # Import model for shell context

app = create_app(os.environ.get('FLASK_ENV', 'default'))

@app.shell_context_processor
def make_shell_context():
    """Adds database instance and models to the Flask shell."""
    return dict(db=db, User=User)

if __name__ == '__main__':
    app.run()