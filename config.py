import os
import sys
from dotenv import load_dotenv

# CRITICAL FIX: Add the project directory to sys.path for Alembic/env.py to work with absolute imports
sys.path.append(os.path.abspath(os.path.dirname(__file__))) 

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Base configuration class."""
    # SECRET_KEY must be set via environment variable in production
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MIGRATION_DIR = os.path.join(basedir, 'migrations')
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads', 'profile_pics')
    
    # File upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # Logging
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')
    
    @staticmethod
    def init_app(app):
        """Initialize application-specific configuration."""
        import logging
        from logging import StreamHandler
        
        if not app.debug and not app.testing:
            # Production logging
            if not os.path.exists('logs'):
                os.mkdir('logs')
            file_handler = logging.FileHandler('logs/payroll.log')
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
            app.logger.setLevel(logging.INFO)
            app.logger.info('Payroll System startup')

class DevelopmentConfig(Config):
    DEBUG = True
    # Allow weak secret key in development only
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

class ProductionConfig(Config):
    DEBUG = False
    # In production, these must be set via environment variables
    # Validation happens in init_app() method
    
    @staticmethod
    def init_app(app):
        """Initialize production configuration with validation."""
        Config.init_app(app)  # Call parent init_app for logging
        
        # Validate required environment variables
        if not os.environ.get('SECRET_KEY'):
            raise ValueError("SECRET_KEY environment variable must be set in production!")
        
        if not os.environ.get('DATABASE_URL'):
            raise ValueError("DATABASE_URL environment variable must be set in production!")
        
        # Set production values
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}