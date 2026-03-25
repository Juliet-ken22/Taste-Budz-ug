from app import db
from datetime import datetime

class Reservation(db.Model):
    __tablename__ = 'reservation'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    reservation_time = db.Column(db.DateTime, nullable=False)
    guests = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), default='pending', nullable=False)
    branch_id = db.Column(db.String(36), db.ForeignKey('branch.id'), nullable=False)
    transaction_id = db.Column(db.String(100), default='', nullable=False)
    special_requests = db.Column(db.String(500), default='', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    # updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref='reservations')
    branch = db.relationship('Branch', back_populates='reservations')

    def __init__(self, **kwargs):
        # Set default values for nullable fields
        kwargs.setdefault('transaction_id', '')
        kwargs.setdefault('special_requests', '')
        super().__init__(**kwargs)

    def to_dict(self):
        """Returns a dictionary representation with all fields populated"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "reservation_time": self.reservation_time.isoformat(),
            "guests": self.guests,
            "status": self.status,
            "branch_id": self.branch_id,
            "transaction_id": self.transaction_id,
            "special_requests": self.special_requests,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            # 'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Reservation {self.id} for User {self.user_id}>"