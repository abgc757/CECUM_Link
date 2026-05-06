import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///cecum_link.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = ENV == "development"
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_UPLOAD_MB", "50")) * 1024 * 1024
