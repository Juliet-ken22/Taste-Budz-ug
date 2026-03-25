# app/models/MenuItem_Toppings.py

from app import db # Assuming db is your SQLAlchemy instance
from datetime import datetime

class MenuItem(db.Model):
    __tablename__ = 'menu_item'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    size = db.Column(db.String(50), nullable=True) # Assuming you have a 'size' column
    category = db.Column(db.String(80), db.ForeignKey('category.name'), nullable=False)
    image_url = db.Column(db.String(255), nullable=True) # <--- ADD THIS LINE
    is_available = db.Column(db.Boolean, default=True) # <--- ADD THIS LINE
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Define relationship to Topping if needed
    toppings = db.relationship('Topping', backref='menu_item', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MenuItem {self.name}>"

class Topping(db.Model):
    __tablename__ = 'toppings'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=True)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_item.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Topping {self.name}>"
    



class Category(db.Model):
    __tablename__ = 'category'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    image_url = db.Column(db.String(255), nullable=True) # <-- New field for category image
    
    # You might also want to establish a relationship with MenuItem
    menu_items = db.relationship('MenuItem', backref='category_obj', lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "image_url": self.image_url
        }

