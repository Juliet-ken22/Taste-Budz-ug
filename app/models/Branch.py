from app import db
from datetime import datetime
import uuid

class Branch(db.Model):
    __tablename__ = 'branch'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(50), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reservations = db.relationship(
        "Reservation", 
        back_populates="branch",
        overlaps="branch_reservations,branch"
    )

    branch_reservations = db.relationship(
        "Reservation",
        viewonly=True,
        overlaps="reservations,branch"
    )

    def __repr__(self):
        return f"<Branch {self.name}>"
