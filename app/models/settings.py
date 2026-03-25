from app import db
from datetime import datetime

class SystemConfig(db.Model):
    __tablename__ = 'system_config'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True)
    value = db.Column(db.String(200))
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

class BusinessHours(db.Model):
    __tablename__ = 'business_hours'
    id = db.Column(db.Integer, primary_key=True)
    day_of_week = db.Column(db.Integer)  # 0-6 (Monday-Sunday)
    open_time = db.Column(db.Time)
    close_time = db.Column(db.Time)
    is_closed = db.Column(db.Boolean, default=False)


# app/models/MaintenanceMode.py


class MaintenanceMode(db.Model):
    __tablename__ = 'maintenance_mode'
    
    id = db.Column(db.Integer, primary_key=True)
    maintenance_mode = db.Column(db.Boolean, nullable=False, default=False)
    
    def __repr__(self):
        return f'<MaintenanceMode {self.id}>'