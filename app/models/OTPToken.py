import uuid
from datetime import datetime, timedelta
from app import db

class OTPToken(db.Model):
    __tablename__ = 'otptoken'
    id = db.Column(db.Integer, primary_key=True)
    # If OTPs are linked to User.id (UUID), change this. Currently linked to phone.
    # user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    phone = db.Column(db.String(20), nullable=False) # Added nullable=False
    token = db.Column(db.String(6), default=lambda: str(uuid.uuid4())[:6])
    expires_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(minutes=5))
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow) # Added created_at

    def __repr__(self):
        return f"<OTPToken {self.id} for {self.phone}>"
