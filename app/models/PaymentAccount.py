# app/models/PaymentAccount.py
from app import db
from datetime import datetime

# app/models/PaymentAccount.py

class PaymentAccount(db.Model):
    __tablename__ = 'payment_account'
    id = db.Column(db.Integer, primary_key=True)
    method_name = db.Column(db.String(100), nullable=False)
    merchant_id = db.Column(db.String(100), nullable=False)
    merchant_name = db.Column(db.String(100), nullable=False)
    instructions = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ✅ Match the UUID type from Branch.id
    branch_id = db.Column(db.String(36), db.ForeignKey('branch.id'), nullable=True)
    branch = db.relationship('Branch', backref=db.backref('payment_accounts', lazy=True))

