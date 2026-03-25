# File: app/models/OpeningHours.py

from app import db

class OpeningHours(db.Model):
    __tablename__ = 'opening_hours'
    
    id = db.Column(db.Integer, primary_key=True)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Monday, 6=Sunday
    open_time = db.Column(db.String(10), nullable=True)  # Format: "8:00 AM"
    close_time = db.Column(db.String(10), nullable=True) # Format: "10:00 PM"
    is_closed = db.Column(db.Boolean, default=False, nullable=False)
    
    def get_display_day(self):
        days = {
            0: 'Monday',
            1: 'Tuesday',
            2: 'Wednesday',
            3: 'Thursday',
            4: 'Friday',
            5: 'Saturday',
            6: 'Sunday'
        }
        return days.get(self.day_of_week, 'Unknown')
    
    def __repr__(self):
        return f'<OpeningHours {self.get_display_day()}>'