"""
Configuration module for KFC COS Calculator
Manages environment-specific settings and configurations
"""
import os
from datetime import timedelta
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.absolute()


class Config:
    """Base configuration class with common settings"""
    
    # Flask Core Settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database Configuration
    DB_PATH = os.environ.get('DB_PATH', str(BASE_DIR / 'kfc_cos.db'))
    NORMATIVI_PATH = os.environ.get('NORMATIVI_PATH', str(BASE_DIR / 'normativi.xlsx'))
    SVIRESTORANI_PATH = os.environ.get('SVIRESTORANI_PATH', str(BASE_DIR / 'svirestorani.xlsx'))
    
    # Server Configuration
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 8080))
    
    # Upload Configuration
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_FILE_SIZE', 52428800))  # 50MB default
    ALLOWED_EXTENSIONS = {'xls', 'xlsx'}
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', str(BASE_DIR / 'app.log'))
    LOG_MAX_BYTES = 10485760  # 10MB
    LOG_BACKUP_COUNT = 5
    
    # Application Settings
    RESTAURANTS = ['KFC SCC', 'KFC MCC', 'KFC BCC', 'KFC STM', 'KFC ICC']
    DEFAULT_FORECAST_PERIOD = 'all'
    DEFAULT_DATE_RANGE_DAYS = 30
    
    # Cache Configuration
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes
    
    # Pagination
    ITEMS_PER_PAGE = 50
    
    # Export Configuration
    EXPORT_FORMATS = ['excel', 'pdf']
    EXPORT_TEMP_DIR = BASE_DIR / 'exports'
    
    # Error Tracking (Optional)
    SENTRY_DSN = os.environ.get('SENTRY_DSN')
    
    # Email Configuration (Optional)
    MAIL_SERVER = os.environ.get('SMTP_SERVER', 'localhost')
    MAIL_PORT = int(os.environ.get('SMTP_PORT', 25))
    MAIL_USE_TLS = os.environ.get('SMTP_USE_TLS', 'False').lower() in ('true', '1', 'yes')
    MAIL_USERNAME = os.environ.get('SMTP_USERNAME')
    MAIL_PASSWORD = os.environ.get('SMTP_PASSWORD')
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@kfc.ba')
    
    @staticmethod
    def init_app(app):
        """Initialize application with configuration"""
        # Create necessary directories
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.EXPORT_TEMP_DIR, exist_ok=True)


class DevelopmentConfig(Config):
    """Development environment configuration"""
    DEBUG = True
    TESTING = False
    
    # More verbose logging in development
    LOG_LEVEL = 'DEBUG'
    
    # Development-specific settings
    SEND_FILE_MAX_AGE_DEFAULT = 0  # Disable caching in development


class ProductionConfig(Config):
    """Production environment configuration"""
    DEBUG = False
    TESTING = False
    
    # Security enhancements for production
    SESSION_COOKIE_SECURE = True  # Requires HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'
    
    # Production logging
    LOG_LEVEL = 'WARNING'
    
    @classmethod
    def init_app(cls, app):
        """Production-specific initialization"""
        Config.init_app(app)
        
        # Log to syslog or external service in production
        if cls.SENTRY_DSN:
            try:
                import sentry_sdk
                from sentry_sdk.integrations.flask import FlaskIntegration
                
                sentry_sdk.init(
                    dsn=cls.SENTRY_DSN,
                    integrations=[FlaskIntegration()],
                    traces_sample_rate=0.1,
                    profiles_sample_rate=0.1,
                )
            except ImportError:
                app.logger.warning('Sentry SDK not installed. Error tracking disabled.')


class TestingConfig(Config):
    """Testing environment configuration"""
    TESTING = True
    DEBUG = True
    
    # Use in-memory database for testing
    DB_PATH = ':memory:'
    
    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False
    
    # Fast password hashing for tests
    BCRYPT_LOG_ROUNDS = 4


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(config_name=None):
    """Get configuration class based on environment"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    return config.get(config_name, config['default'])
