# File: app/models/AboutUs.py

from app import db
from sqlalchemy.dialects.postgresql import JSON

class AboutUs(db.Model):
    __tablename__ = 'about_us'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, default='About Us')
    paragraphs = db.Column(JSON, nullable=False)  # List of paragraphs
    slogan = db.Column(db.String(200), nullable=True)
    main_slogan = db.Column(db.String(200), nullable=True)
    features = db.Column(JSON, nullable=False)  # List of feature objects
    founded_year = db.Column(db.Integer, nullable=False, default=2007)
    branch_count = db.Column(db.Integer, nullable=False, default=4)
    highlights = db.Column(JSON, nullable=False)  # List of highlight strings
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), 
                          onupdate=db.func.current_timestamp())
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'paragraphs': self.paragraphs,
            'slogan': self.slogan,
            'main_slogan': self.main_slogan,
            'features': self.features,
            'founded_year': self.founded_year,
            'branch_count': self.branch_count,
            'highlights': self.highlights,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<AboutUs {self.title}>'