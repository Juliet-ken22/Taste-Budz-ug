from datetime import datetime
from app import db

class SalesAnalytics(db.Model):
    __tablename__ = 'sales_analytics'
    id = db.Column(db.Integer, primary_key=True)
    period = db.Column(db.String(10))  # 'day', 'week', 'month'
    period_start = db.Column(db.Date)
    total_amount = db.Column(db.Float)
    order_count = db.Column(db.Integer)

class CustomerMetrics(db.Model):  # Renamed from CustomerActivity
    __tablename__ = 'customer_metrics'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date)
    new_customers = db.Column(db.Integer)
    repeat_customers = db.Column(db.Integer)
    churned_customers = db.Column(db.Integer)

class ActivityLog(db.Model):  # NEW: Model for activity logging
    __tablename__ = 'activity_logs'
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    reference_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

class ProductPerformance(db.Model):
    __tablename__ = 'product_performance'
    id = db.Column(db.Integer, primary_key=True)
    period = db.Column(db.String(10))
    product_id = db.Column(db.Integer)
    units_sold = db.Column(db.Integer)
    revenue = db.Column(db.Float)