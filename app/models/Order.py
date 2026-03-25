# app/models/Order.py
from app import db
from datetime import datetime
import json
from sqlalchemy.orm import joinedload
# The Payment import is needed for the relationship definition
# Ensure this import path is correct for your project structure
from app.models.Payment import Payment 

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    total_price = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(50), default='pending')
    branch_id = db.Column(db.String(36), db.ForeignKey('branch.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    transaction_id = db.Column(db.String(100), nullable=True)
    
    order_type = db.Column(db.String(20), nullable=False)
    delivery_address = db.Column(db.Text)
    delivery_instructions = db.Column(db.Text)
    payment_method = db.Column(db.String(50))
    payment_status = db.Column(db.String(20), default='pending')
    
    # Add phone_number field
    phone_number = db.Column(db.String(20), nullable=True)
    
    # Relationships
    user = db.relationship('User', backref='orders', lazy='joined')
    branch = db.relationship('Branch', backref='orders_from_branch', lazy='joined')
    order_items = db.relationship('OrderItem', backref='order', lazy=True, cascade="all, delete-orphan")
    
    # Corrected relationship with Payment model
    payment = db.relationship(
        'Payment',
        back_populates='order', # This is the change
        uselist=False
    )
    
    def __repr__(self):
        return f"<Order {self.id} Status: {self.status}>"
    
    def to_dict(self, include_items=True):
        result = {
            'id': self.id,
            'user_id': self.user_id,
            'branch_id': self.branch_id,
            'transaction_id': self.transaction_id,
            'status': self.status,
            'total_price': float(self.total_price) if self.total_price else 0.0,
            'order_type': self.order_type,
            'delivery_address': self.delivery_address,
            'delivery_instructions': self.delivery_instructions,
            'payment_method': self.payment_method,
            'payment_status': self.payment_status,
            'phone_number': self.phone_number,  # Add this line
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            
            'user': {
                'id': self.user.id,
                'full_name': self.user.full_name,
                'email': self.user.email,
                'phone': self.user.phone
            } if self.user else None,
            
            'branch': {
                'id': self.branch.id,
                'name': self.branch.name,
                'address': self.branch.address,
                'phone': self.branch.phone
            } if self.branch else None,
            
            'payment': {
                'id': self.payment.id if self.payment else None,
                'method': self.payment.method if self.payment else None,
                'transaction_id': self.payment.transaction_id if self.payment else None,
                'status': self.payment.status if self.payment else None,
                'amount': float(self.payment.amount) if self.payment and self.payment.amount else None
            } if self.payment else None
        }
        
        if include_items:
            result['items'] = [item.to_dict() for item in self.order_items]
            
        return result

# The rest of your Order model and OrderItem class remains the same

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_item.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Float, nullable=False)
    toppings = db.Column(db.Text, nullable=True)
    
    menu_item = db.relationship('MenuItem', backref='order_items', lazy='joined')
    
    def __init__(self, order_id, menu_item_id, quantity, price, toppings=None):
        self.order_id = order_id
        self.menu_item_id = menu_item_id
        self.quantity = quantity
        self.price = price
        self.toppings = json.dumps(toppings) if toppings is not None else json.dumps([])
    
    def get_toppings(self):
        return json.loads(self.toppings) if self.toppings else []
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'menu_item_id': self.menu_item_id,
            'quantity': self.quantity,
            'price': float(self.price),
            'total': float(self.price * self.quantity),
            
            'menu_item': {
                'id': self.menu_item.id,
                'name': self.menu_item.name,
                'description': self.menu_item.description,
                'category': self.menu_item.category,
                'image_url': self.menu_item.image_url
            } if self.menu_item else None,
            
            'toppings': self.get_toppings_list()
        }
    
    def get_toppings_list(self):
        if not self.toppings:
            return []
            
        try:
            toppings_data = json.loads(self.toppings)
            
            if isinstance(toppings_data, list) and all(isinstance(t, dict) and 'id' in t and 'name' in t for t in toppings_data):
                return toppings_data
                
            if isinstance(toppings_data, list) and all(isinstance(t, int) for t in toppings_data):
                from app.models.MenuItem_Toppings import Topping
                toppings = Topping.query.filter(Topping.id.in_(toppings_data)).all()
                return [{'id': t.id, 'name': t.name, 'price': float(t.price)} for t in toppings]
                
            return []
        except (json.JSONDecodeError, Exception):
            return []
    
    def __repr__(self):
        return f"<OrderItem {self.id} - Order {self.order_id}>"

def get_order_with_details(order_id):
    return Order.query.options(
        joinedload(Order.user),
        joinedload(Order.branch),
        joinedload(Order.payment),
        joinedload(Order.order_items).joinedload(OrderItem.menu_item)
    ).filter_by(id=order_id).first()

def get_orders_with_details(page=1, per_page=10, status=None, user_id=None, branch_id=None, date_from=None, date_to=None):
    query = Order.query.options(
        joinedload(Order.user),
        joinedload(Order.branch),
        joinedload(Order.payment),
        joinedload(Order.order_items).joinedload(OrderItem.menu_item)
    ).order_by(Order.created_at.desc())
    
    if status:
        query = query.filter(Order.status == status)
    if user_id:
        query = query.filter(Order.user_id == user_id)
    if branch_id:
        query = query.filter(Order.branch_id == branch_id)
    if date_from:
        query = query.filter(Order.created_at >= date_from)
    if date_to:
        query = query.filter(Order.created_at <= date_to)
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return pagination.items, pagination.total