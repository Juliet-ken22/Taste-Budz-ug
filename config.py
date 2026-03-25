from datetime import timedelta
import os
from dotenv import load_dotenv
from pathlib import Path



# Get the absolute path to the directory containing this file
basedir = Path(__file__).parent.absolute()

# Load environment variables from .env file
load_dotenv(basedir / '.env')

class Config:
    # Database
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost/project_taste_budz'
    # SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'mysql+pymysql://tastebzc_user:tastebudz2007jun@localhost/tastebzc_bd')
    # SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'tastebudzrestaurant')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_COOKIE_SECURE = os.getenv('JWT_COOKIE_SECURE', 'False').lower() in ('true', '1', 't')

    # File Uploads
    UPLOAD_FOLDER = basedir / 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    # Ensure upload directory exists
    UPLOAD_FOLDER.mkdir(exist_ok=True, parents=True)

    # CORS settings for development
    FRONTEND_URL = os.getenv('FRONTEND_URL', 'https://tastebz.com/')

    # Email settings - CORRECTED
        # Email Settings (FINAL WORKING VERSION)
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'mail.tastebz.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 465))  # Must use 465 on cPanel
    MAIL_USE_TLS = False                          # Must be disabled
    MAIL_USE_SSL = True                           # SSL must be enabled
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', 'info@tastebz.com')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', 'UzDi?rYMZM]B-L7}')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'info@tastebz.com')

    MAIL_SUPPRESS_SEND = False
    TESTING = False

    
  