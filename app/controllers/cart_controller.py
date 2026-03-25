from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app import db
from app.models.CartItem import CartItem
from app.models.MenuItem_Toppings import MenuItem
from app.models.Order import Order
from app.models.Order import OrderItem
from flask_cors import cross_origin
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

cart_bp = Blueprint('cart', __name__, url_prefix='/api/v1/cart_bp')

# Helper function to clean invalid cart items
def clean_invalid_cart_items(user_id):
    """Remove cart items that reference non-existent menu items"""
    try:
        # Find cart items with invalid menu item references
        invalid_items = db.session.query(CartItem).outerjoin(MenuItem).filter(
            CartItem.user_id == user_id,
            MenuItem.id.is_(None)
        ).all()
        
        count = len(invalid_items)
        if count > 0:
            logger.warning(f"Removing {count} invalid cart items for user {user_id}")
            for item in invalid_items:
                db.session.delete(item)
            db.session.commit()
            return count
        return 0
    except Exception as e:
        logger.error(f"Error cleaning invalid cart items: {str(e)}")
        db.session.rollback()
        return 0

# 🔐 POST /cart/items – Add item to cart
@cart_bp.route('/cart/items', methods=['POST'])
@jwt_required()
def add_to_cart():
    user_id = get_jwt_identity()
    data = request.get_json()
    menu_item_id = data.get('menu_item_id')
    quantity = data.get('quantity', 1)
    toppings = data.get('toppings', [])
    
    # Validate menu item exists
    menu_item = MenuItem.query.get(menu_item_id)
    if not menu_item:
        logger.error(f"Menu item not found: {menu_item_id}")
        return jsonify({"success": False, "message": "Menu item not found"}), 404
    
    # Create cart item
    cart_item = CartItem(
        user_id=user_id,
        menu_item_id=menu_item_id,
        quantity=quantity,
        toppings=json.dumps(toppings)
    )
    
    try:
        db.session.add(cart_item)
        db.session.commit()
        return jsonify({"success": True, "message": "Item added to cart"}), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding item to cart: {str(e)}")
        return jsonify({"success": False, "message": "Failed to add item to cart"}), 500

# 🔐 GET /cart – View user's cart
@cart_bp.route('/cart', methods=['GET'])
@jwt_required()
def view_cart():
    user_id = get_jwt_identity()
    
    # Clean invalid cart items first
    clean_invalid_cart_items(user_id)
    
    items = CartItem.query.filter_by(user_id=user_id).all()
    
    data = []
    for item in items:
        menu_item = MenuItem.query.get(item.menu_item_id)
        if not menu_item:
            logger.warning(f"Skipping cart item {item.id} with invalid menu item {item.menu_item_id}")
            continue
        
        toppings_list = item.get_toppings()
        
        data.append({
            "id": item.id,
            "menu_item": {
                "id": menu_item.id,
                "name": menu_item.name,
                "price": menu_item.price,
                "image_url": menu_item.image_url
            },
            "quantity": item.quantity,
            "toppings": toppings_list
        })
    
    return jsonify({"items": data}), 200

# 🔐 DELETE /cart/remove/<item_id> – Remove specific cart item
@cart_bp.route('/cart/remove/<int:item_id>', methods=['DELETE'])
@jwt_required()
def remove_from_cart(item_id):
    user_id = get_jwt_identity()
    item = CartItem.query.filter_by(id=item_id, user_id=user_id).first()
    
    if not item:
        return jsonify({"success": False, "message": "Cart item not found"}), 404
    
    try:
        db.session.delete(item)
        db.session.commit()
        return jsonify({"success": True, "message": "Item removed from cart"}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error removing cart item: {str(e)}")
        return jsonify({"success": False, "message": "Failed to remove item"}), 500

# 🔐 DELETE /cart/clear – Clear the entire user's cart
@cart_bp.route('/cart/clear', methods=['DELETE'])
@jwt_required()
def clear_cart():
    user_id = get_jwt_identity()
    
    try:
        # Find and delete all cart items for the current user
        items_to_delete = CartItem.query.filter_by(user_id=user_id).all()
        for item in items_to_delete:
            db.session.delete(item)
        
        db.session.commit()
        return jsonify({"success": True, "message": "Cart cleared successfully"}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error clearing cart: {str(e)}")
        return jsonify({"success": False, "message": "Failed to clear cart"}), 500

# 🔐 POST /cart/checkout – Convert cart to order
# In cart_bp.py

@cart_bp.route('/checkout', methods=['POST'])
@jwt_required()
def checkout_cart():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['branch_id', 'order_type', 'payment_method', 'transaction_id']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({
            "success": False,
            "message": f"Missing required fields: {', '.join(missing_fields)}"
        }), 400
    
    # Validate order_type
    valid_order_types = ['delivery', 'pickup']
    if data['order_type'] not in valid_order_types:
        return jsonify({
            "success": False,
            "message": f"Invalid order_type. Must be one of: {', '.join(valid_order_types)}"
        }), 400
    
    # Validate delivery address if needed
    if data['order_type'] == 'delivery' and not data.get('delivery_address'):
        return jsonify({
            "success": False,
            "message": "Delivery address is required for delivery orders"
        }), 400
    
    # Clean invalid cart items first
    invalid_count = clean_invalid_cart_items(user_id)
    if invalid_count > 0:
        logger.info(f"Removed {invalid_count} invalid cart items for user {user_id}")
    
    cart_items = CartItem.query.filter_by(user_id=user_id).all()
    if not cart_items:
        return jsonify({"success": False, "message": "Your cart is empty"}), 400
    
    try:
        # Filter out cart items with invalid menu item references
        valid_cart_items = []
        for item in cart_items:
            if not item.menu_item:
                logger.warning(f"Skipping cart item {item.id} with invalid menu item {item.menu_item_id}")
                continue
            valid_cart_items.append(item)
        
        if not valid_cart_items:
            return jsonify({"success": False, "message": "No valid items in cart"}), 400
        
        # Calculate total price using only valid items
        total_price = sum(
            (item.menu_item.price * item.quantity) 
            for item in valid_cart_items
        )
        
        # Create the order with phone_number
        order = Order(
            user_id=user_id,
            branch_id=data['branch_id'],
            order_type=data['order_type'],
            status='pending',
            payment_method=data['payment_method'],
            transaction_id=data['transaction_id'],
            total_price=total_price,
            payment_status='pending',
            delivery_address=data.get('delivery_address'),
            delivery_instructions=data.get('notes'),
            phone_number=data.get('phone_number')  # Now this field exists in the model
        )
        db.session.add(order)
        db.session.flush()
        
        # Create order items using only valid cart items
        for cart_item in valid_cart_items:
            order_item = OrderItem(
                order_id=order.id,
                menu_item_id=cart_item.menu_item.id,
                quantity=cart_item.quantity,
                price=cart_item.menu_item.price,
                toppings=cart_item.toppings
            )
            db.session.add(order_item)
        
        # Clear cart - remove all items for this user (both valid and invalid)
        CartItem.query.filter_by(user_id=user_id).delete()
        
        db.session.commit()
        
        logger.info(f"Order {order.id} created successfully for user {user_id}")
        
        return jsonify({
            "success": True,
            "message": "Order placed successfully",
            "order_id": order.id,
            "total_price": total_price
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Checkout error: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "Checkout failed",
            "error": str(e)
        }), 500
# 🔐 PUT /cart/items/<item_id> – Update cart item quantity
@cart_bp.route('/cart/items/<int:item_id>', methods=['PUT'])
@jwt_required()
def update_cart_item(item_id):
    user_id = get_jwt_identity()
    data = request.get_json()
    new_quantity = data.get('quantity')
    
    if not new_quantity or not isinstance(new_quantity, int) or new_quantity <= 0:
        return jsonify({"success": False, "message": "Invalid quantity"}), 400
    
    cart_item = CartItem.query.filter_by(id=item_id, user_id=user_id).first()
    if not cart_item:
        return jsonify({"success": False, "message": "Cart item not found"}), 404
    
    try:
        cart_item.quantity = new_quantity
        db.session.commit()
        return jsonify({"success": True, "message": "Cart item updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating cart item: {str(e)}")
        return jsonify({"success": False, "message": "Failed to update cart item"}), 500