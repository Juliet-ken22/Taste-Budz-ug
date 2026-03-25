from app import db
from datetime import datetime

class ContactMessage(db.Model):
    __tablename__ = 'contact_messages'  # Changed to plural for consistency

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='new')  # ADDED STATUS FIELD
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Define relationship to User if needed
    user = db.relationship('User', backref='contact_messages')

    def __repr__(self):
        return f"<ContactMessage {self.id}>"