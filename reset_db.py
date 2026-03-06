from app import app
from models import db

with app.app_context():
    print("Resetting database...")
    db.drop_all() 
    db.create_all()
    print("Database reset and updated successfully!")