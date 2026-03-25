# app/models/Payment.py
from app import db
from datetime import datetime

class Payment(db.Model):
    __tablename__ = 'payment'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    reservation_id = db.Column(db.Integer, db.ForeignKey('reservation.id'), nullable=True)
    
    transaction_id = db.Column(db.String(100), nullable=False, unique=True)
    amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='payments', lazy=True)
    
    # Corrected relationship, removed conflicting backref
    order = db.relationship('Order', back_populates='payment')
    reservation = db.relationship('Reservation', backref='payment', uselist=False)
    
    @property
    def payment_type(self):
        return 'order' if self.order_id else 'reservation'
    
    @property
    def reference_id(self):
        return self.order_id if self.order_id else self.reservation_id
    
    def __repr__(self):
        return f"<Payment {self.id} - {self.transaction_id}>"