from app import db
from datetime import datetime
import json # Import json for handling toppings as a JSON string

class CartItem(db.Model):
    __tablename__ = 'cart_item' # Or 'cart_items' if you prefer plural

    id = db.Column(db.Integer, primary_key=True)
    # Changed user_id to String(36) to match User.id type (UUID)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_item.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    # Storing toppings as TEXT, converting list to JSON string
    toppings = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow) # Added created_at for tracking

    # Define relationships if needed
    user = db.relationship('User', backref='cart_items')
    menu_item = db.relationship('MenuItem', backref='cart_items')

    def __init__(self, user_id, menu_item_id, quantity, toppings=None):
        self.user_id = user_id
        self.menu_item_id = menu_item_id
        self.quantity = quantity
        # Convert list of toppings to JSON string for storage
        self.toppings = json.dumps(toppings) if toppings is not None else json.dumps([])

    def get_toppings(self):
        # Convert JSON string back to list when retrieved
        return json.loads(self.toppings) if self.toppings else []

    def __repr__(self):
        return f"<CartItem {self.id} for User {self.user_id} - MenuItem {self.menu_item_id}>"

