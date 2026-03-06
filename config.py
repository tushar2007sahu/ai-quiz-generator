# backend/config.py
import os

class Config:
    # Format: mysql+pymysql://user:password@host/database_name
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:Tks200720@localhost/ai_quiz'
    SQLALCHEMY_TRACK_MODIFICATIONS = False