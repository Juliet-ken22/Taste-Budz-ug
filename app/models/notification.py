from datetime import datetime
from app import db

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'order', 'reservation', etc.
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    related_id = db.Column(db.Integer)  # ID of related order/reservation
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Add property alias for backward compatibility if needed
    @property
    def read(self):
        return self.is_read
    
    @read.setter
    def read(self, value):
        self.is_read = value
    
    def __repr__(self):
        return f'<Notification {self.id} for user {self.recipient_id}>'