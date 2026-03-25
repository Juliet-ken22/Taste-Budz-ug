# app/models/User.py
from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

class User(db.Model):
    __tablename__ = 'users'
    
    # UUID primary key
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)  # Now required
    email = db.Column(db.String(120), unique=True, nullable=False)
    
    password_hash = db.Column(db.String(255), nullable=True)
    otp = db.Column(db.String(6), nullable=True)
    otp_expires_at = db.Column(db.DateTime, nullable=True)
    
    role = db.Column(db.String(20), default="customer")
    is_verified = db.Column(db.Boolean, default=False)
    
    branch_id = db.Column(db.String(36), db.ForeignKey('branch.id'), nullable=True)  # Link staff to branch
    
    address = db.Column(db.Text, nullable=True)
    bio = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    branch = db.relationship('Branch', backref='users', lazy=True)

    # Password methods
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f"<User {self.email}>"
