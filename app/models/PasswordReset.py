from datetime import datetime, timedelta
import uuid
from app import db

class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'

    id = db.Column(db.Integer, primary_key=True)
    # If reset tokens are linked to User.id (UUID), change this. Currently linked to phone.
    # user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    token = db.Column(db.String(6), default=lambda: str(uuid.uuid4())[:6])
    expires_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(minutes=10))
    is_used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow) # Added created_at

    def is_valid(self):
        return datetime.utcnow() < self.expires_at and not self.is_used

    def __repr__(self):
        return f"<PasswordResetToken {self.id} for {self.phone}>"
