from app import db
from datetime import datetime

class Feedback(db.Model):
    __tablename__ = 'feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    message = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=True)  # Made nullable since it's optional
    status = db.Column(db.String(20), default='pending')  # Added status field
    branch_id = db.Column(db.String(36), db.ForeignKey('branch.id'), nullable=True)  # Added branch reference
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref='feedback_entries')
    branch = db.relationship('Branch', backref='feedback')

    def __repr__(self):
        return f"<Feedback {self.id}>"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_name": self.user.full_name if self.user else None,
            "message": self.message,
            "rating": self.rating,
            "status": self.status,
            "branch_id": self.branch_id,
            "branch_name": self.branch.name if self.branch else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }