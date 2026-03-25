from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app import db
from app.models.Order import Order, OrderItem, get_order_with_details, get_orders_with_details
from app.models.MenuItem_Toppings import MenuItem
from app.models.User import User
from app.models.Branch import Branch
from app.models.Payment import Payment
from sqlalchemy import desc
from app.extensions import socketio
import json
from app.models.notification import Notification
from datetime import datetime, timezone
from sqlalchemy.orm import joinedload
import logging
from datetime import timedelta
from flask_cors import cross_origin  # Import cross_origin decorator

logger = logging.getLogger(__name__)

order_bp = Blueprint('orders', __name__, url_prefix='/api/v1/orders')

def _to_iso(dt):
    if not dt:
        return None
    # ensure timezone-aware iso with Z if naive
    try:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')
        return dt.isoformat()
    except Exception:
        return str(dt)

def validate_status_transition(current_status, new_status, user_role):
    """
    Validate if a status transition is allowed for a given user role
    """
    valid_transitions = {
        'customer': {
            'allowed_from': ['pending', 'preparing'],
            'allowed_to': ['cancelled']
        },
        'admin': {
            'allowed_from': ['pending', 'preparing', 'ready', 'delivered', 'completed', 'cancelled'],
            'allowed_to': ['pending', 'preparing', 'ready', 'delivered', 'completed', 'cancelled']
        }
    }
    
    rules = valid_transitions['admin'] if user_role in ['admin', 'super_admin'] else valid_transitions['customer']
    
    validation_errors = []
    
    if current_status not in rules['allowed_from']:
        validation_errors.append({
            "error": "invalid_current_status",
            "message": f"Cannot update from current status '{current_status}'",
            "allowed_from": rules['allowed_from']
        })
    
    if new_status not in rules['allowed_to']:
        validation_errors.append({
            "error": "invalid_target_status", 
            "message": f"Cannot update to status '{new_status}'",
            "allowed_to": rules['allowed_to']
        })
    
    return validation_errors

def can_order_be_cancelled(order):
    """
    Check if an order can be cancelled based on its current status
    """
    cancellable_statuses = ['pending', 'preparing']
    return order.status in cancellable_statuses

def notify_order_update(order):
    """
    Create a Notification record and emit a socket message.
    Non-fatal: errors are logged but do not break the main flow.
    """
    try:
        user_id = order.user_id
        notification = Notification(
            user_id=user_id,
            type='order',
            recipient_id=user_id,
            message=f"Your order #{order.id} status has been updated to {order.status}",
            is_read=False,
            related_id=order.id,
            created_at=datetime.utcnow()
        )
        db.session.add(notification)
        db.session.commit()
    except Exception as e:
        # If saving notification fails, rollback and continue (do not abort main flow)
        try:
            db.session.rollback()
        except Exception:
            pass
        logger.error(f"Notification DB error: {str(e)}")
    
    # Emit websocket with consistent payload
    try:
        payload = {
            'order_id': order.id,
            'user_id': order.user_id,
            'branch_id': order.branch_id,
            'status': order.status,
            'message': f"Order #{order.id} status updated to {order.status}",
            'timestamp': _to_iso(datetime.utcnow())
        }
        
        # Emit to user-specific room and admin rooms
        socketio.emit('order_update', payload, room=f'user_{order.user_id}')
        socketio.emit('order_update', payload, room='role_admin')
        socketio.emit('order_update', payload, room='role_super_admin')
        
        logger.info(f"WebSocket notification sent for order {order.id} status update to {order.status}")
    except Exception as e:
        logger.error(f"Socket emit error: {str(e)}")

def notify_new_order(order):
    """
    Send notification for new order creation
    """
    try:
        payload = {
            'order_id': order.id,
            'user_id': order.user_id,
            'branch_id': order.branch_id,
            'status': order.status,
            'message': f"New order #{order.id} received",
            'timestamp': _to_iso(datetime.utcnow())
        }
        
        # Emit to admin rooms
        socketio.emit('order_update', payload, room='role_admin')
        socketio.emit('order_update', payload, room='role_super_admin')
        
        logger.info(f"WebSocket notification sent for new order {order.id}")
    except Exception as e:
        logger.error(f"Socket emit error for new order: {str(e)}")

def serialize_menu_item(mi):
    if not mi:
        return None
    return {
        'id': getattr(mi, 'id', None),
        'name': getattr(mi, 'name', None),
        'description': getattr(mi, 'description', None),
        'price': float(getattr(mi, 'price', 0)) if getattr(mi, 'price', None) is not None else 0.0,
        'image_url': getattr(mi, 'image_url', None),
        'category': getattr(mi, 'category', None),
        'size': getattr(mi, 'size', None)
    }

def serialize_order(order, include_items=False, include_user=False, include_branch=False, include_payment=False, include_delivery=False):
    """
    Serialize an Order and optional related data. Adds both `total_price` and `total_amount`
    for compatibility with the frontend.
    """
    order_data = {
        'id': order.id,
        'user_id': order.user_id,
        'branch_id': order.branch_id,
        'transaction_id': getattr(order, 'transaction_id', None),
        'status': getattr(order, 'status', None),
        'total_price': float(order.total_price) if getattr(order, 'total_price', None) is not None else 0.0,
        'total_amount': float(order.total_price) if getattr(order, 'total_price', None) is not None else 0.0,
        'order_type': getattr(order, 'order_type', None),
        'delivery_address': getattr(order, 'delivery_address', None),
        'delivery_instructions': getattr(order, 'delivery_instructions', None),
        'payment_method': getattr(order, 'payment_method', None),
        'payment_status': getattr(order, 'payment_status', None),
        'created_at': _to_iso(getattr(order, 'created_at', None)),
        'updated_at': _to_iso(getattr(order, 'updated_at', None)),
        'can_be_cancelled': can_order_be_cancelled(order)
    }
    
    if include_user and hasattr(order, 'user') and order.user:
        user = order.user
        order_data['user'] = {
            'id': user.id,
            'email': getattr(user, 'email', None),
            'full_name': getattr(user, 'full_name', None),
            'phone': getattr(user, 'phone', None)
        }
    
    if include_branch and hasattr(order, 'branch') and order.branch:
        branch = order.branch
        order_data['branch'] = {
            'id': getattr(branch, 'id', None),
            'name': getattr(branch, 'name', None),
            'address': getattr(branch, 'address', None),
            'phone': getattr(branch, 'phone', None)
        }
    
    if include_payment and hasattr(order, 'payment') and order.payment:
        payment = order.payment
        order_data['payment'] = {
            'id': getattr(payment, 'id', None),
            'method': getattr(payment, 'method', None),
            'transaction_id': getattr(payment, 'transaction_id', None),
            'status': getattr(payment, 'status', None),
            'amount': float(getattr(payment, 'amount', 0)) if getattr(payment, 'amount', None) is not None else 0.0
        }
    
    if include_items:
        items = []
        for item in getattr(order, 'order_items', []):
            menu_item = getattr(item, 'menu_item', None)
            # parse toppings (store as list of dicts if saved JSON)
            toppings = []
            try:
                if item.toppings:
                    toppings = json.loads(item.toppings)
            except Exception:
                toppings = item.toppings or []
            items.append({
                'id': item.id,
                'menu_item_id': item.menu_item_id,
                'menu_item': serialize_menu_item(menu_item),
                'menu_item_name': getattr(menu_item, 'name', None) if menu_item else None,
                'quantity': getattr(item, 'quantity', 0),
                'price': float(getattr(item, 'price', 0)) if getattr(item, 'price', None) is not None else 0.0,
                'total': float(getattr(item, 'price', 0)) * getattr(item, 'quantity', 0) if getattr(item, 'price', None) is not None else 0.0,
                'toppings': toppings
            })
        order_data['items'] = items
    
    return order_data

def _int_id(val):
    """Try to normalize identity to int for reliable comparisons"""
    try:
        return int(val)
    except Exception:
        return val

# OPTIONS handler for base route
@order_bp.route('', methods=['OPTIONS'])
@cross_origin(origins='http://localhost:3000', methods=['GET', 'POST', 'OPTIONS', 'PATCH', 'PUT', 'DELETE'])
def handle_options():
    response = jsonify({'status': 'ok'})
    return response

# OPTIONS handler for user orders route
@order_bp.route('/user', methods=['OPTIONS'])
@cross_origin(origins='http://localhost:3000', methods=['GET', 'OPTIONS'])
def handle_user_options():
    response = jsonify({'status': 'ok'})
    return response

# OPTIONS handler for order detail route
@order_bp.route('/<string:order_id>', methods=['OPTIONS'])
@cross_origin(origins='http://localhost:3000', methods=['GET', 'OPTIONS'])
def handle_order_detail_options():
    response = jsonify({'status': 'ok'})
    return response

# OPTIONS handler for order status route
@order_bp.route('/<string:order_id>/status', methods=['OPTIONS'])
@cross_origin(origins='http://localhost:3000', methods=['GET', 'PATCH', 'OPTIONS'])
def handle_order_status_options():
    response = jsonify({'status': 'ok'})
    return response

# OPTIONS handler for order can-cancel route
@order_bp.route('/<string:order_id>/can-cancel', methods=['OPTIONS'])
@cross_origin(origins='http://localhost:3000', methods=['GET', 'OPTIONS'])
def handle_order_can_cancel_options():
    response = jsonify({'status': 'ok'})
    return response

@order_bp.route('', methods=['GET'])
@jwt_required()
@cross_origin(origins='http://localhost:3000')
def get_all_orders():
    """Get all orders with detailed information for admin"""
    claims = get_jwt()
    if claims.get('role') not in ['admin', 'super_admin']:
        return jsonify({"message": "Unauthorized"}), 403

    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        status = request.args.get('status')
        user_id = request.args.get('user_id')
        branch_id = request.args.get('branch_id')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        include_items = request.args.get('include_items', 'true').lower() == 'true'
        include_user = request.args.get('include_user', 'true').lower() == 'true'
        include_branch = request.args.get('include_branch', 'true').lower() == 'true'
        include_payment = request.args.get('include_payment', 'true').lower() == 'true'

        query = Order.query

        # Filters
        if status:
            query = query.filter(Order.status == status)
        if user_id:
            query = query.filter(Order.user_id == user_id)
        if branch_id:
            query = query.filter(Order.branch_id == branch_id)
        if date_from:
            query = query.filter(Order.created_at >= date_from)
        if date_to:
            to_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Order.created_at < to_date)

        # Eager load relationships
        options = []
        if include_items:
            options.append(joinedload(Order.order_items).joinedload(OrderItem.menu_item))
        if include_user:
            options.append(joinedload(Order.user))
        if include_branch:
            options.append(joinedload(Order.branch))
        if include_payment:
            options.append(joinedload(Order.payment))

        query = query.options(*options).order_by(desc(Order.created_at))

        # Pagination
        total = query.count()
        orders = query.offset((page - 1) * per_page).limit(per_page).all()

        # Serialize
        orders_data = [
            serialize_order(
                order,
                include_items=include_items,
                include_user=include_user,
                include_branch=include_branch,
                include_payment=include_payment
            ) for order in orders
        ]

        return jsonify({
            'orders': orders_data,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page if total > 0 else 1
        })
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error getting all orders: {str(e)}", exc_info=True)
        return jsonify({"message": str(e)}), 500


@order_bp.route('', methods=['POST'])
@jwt_required()
@cross_origin(origins='http://localhost:3000')
def create_order():
    try:
        user_id_raw = get_jwt_identity()
        user_id = _int_id(user_id_raw)
        data = request.get_json() or {}
        
        # Validate required fields
        required_fields = ['branch_id', 'items', 'order_type']
        for field in required_fields:
            if field not in data:
                return jsonify({"message": f"{field.replace('_', ' ').title()} is required"}), 400
        
        branch_id = data['branch_id']
        order_items_data = data['items']
        order_type = data['order_type']  # 'delivery' or 'pickup'
        
        # Validate order type
        valid_order_types = ['delivery', 'pickup']
        if order_type not in valid_order_types:
            return jsonify({
                "error": "invalid_order_type",
                "message": "Order type must be 'delivery' or 'pickup'",
                "valid_types": valid_order_types
            }), 400
        
        # Additional validation for delivery orders
        if order_type == 'delivery' and 'delivery_address' not in data:
            return jsonify({"message": "Delivery address is required for delivery orders"}), 400
        
        if not isinstance(order_items_data, list) or not order_items_data:
            return jsonify({"message": "Order items must be a non-empty list"}), 400
        
        # Validate payment method
        valid_payment_methods = ['cash', 'card', 'online']
        payment_method = data.get('payment_method', 'cash')
        if payment_method not in valid_payment_methods:
            return jsonify({
                "error": "invalid_payment_method",
                "message": "Invalid payment method",
                "valid_methods": valid_payment_methods
            }), 400
        
        # Create the order with all required fields
        order = Order(
            user_id=user_id,
            branch_id=branch_id,
            transaction_id=data.get('transaction_id'),
            status='pending',
            order_type=order_type,
            delivery_address=data.get('delivery_address') if order_type == 'delivery' else None,
            delivery_instructions=data.get('delivery_instructions'),
            payment_method=payment_method,
            payment_status='pending',
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.session.add(order)
        db.session.flush()  # Get the order ID before committing
        
        # Process order items
        total_amount = 0.0
        for item_data in order_items_data:
            menu_item_id = item_data.get('menu_item_id')
            quantity = item_data.get('quantity', 1)
            toppings = item_data.get('toppings', [])
            
            # Validate menu item
            menu_item = MenuItem.query.get(menu_item_id)
            if not menu_item:
                db.session.rollback()
                return jsonify({"message": f"Menu item {menu_item_id} not found"}), 404
            
            # Validate quantity
            if not isinstance(quantity, int) or quantity <= 0:
                db.session.rollback()
                return jsonify({"message": "Quantity must be a positive integer", "status": 400})

            # Create order item
            order_item = OrderItem(
                order_id=order.id,
                menu_item_id=menu_item_id,
                quantity=quantity,
                price=menu_item.price,
                toppings=json.dumps(toppings) if toppings else None
            )
            db.session.add(order_item)
            total_amount += (quantity * menu_item.price)
        
        # Set total price and commit
        order.total_price = total_amount
        db.session.commit()
        
        # Notify (non-fatal)
        try:
            notify_new_order(order)
        except Exception as e:
            logger.error(f"Notification error for new order: {str(e)}")
        
        return jsonify({
            "message": "Order created successfully",
            "data": serialize_order(order, include_items=True, include_user=True, include_branch=True),
            "estimated_delivery_time": getattr(order, 'estimated_delivery_time', "30-45 minutes")
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating order: {str(e)}")
        return jsonify({"message": str(e)}), 500

@order_bp.route('/user', methods=['GET'])
@jwt_required()
@cross_origin(origins='http://localhost:3000')
def get_user_orders():
    try:
        user_id_raw = get_jwt_identity()
        user_id = _int_id(user_id_raw)
        include_items = request.args.get('include_items', 'true').lower() == 'true'
        options = []
        if include_items:
            options.append(joinedload(Order.order_items).joinedload(OrderItem.menu_item))
        orders = Order.query.options(*options).filter_by(user_id=user_id).order_by(desc(Order.created_at)).all()
        return jsonify({
            "data": [serialize_order(order, include_items=include_items, include_user=False, include_branch=True) for order in orders]
        }), 200
    except Exception as e:
        logger.error(f"Error getting user orders: {str(e)}")
        return jsonify({"message": str(e)}), 500

@order_bp.route('/<string:order_id>', methods=['GET'])
@jwt_required()
@cross_origin(origins='http://localhost:3000')
def get_order_details(order_id):
    """Get detailed order information with all related data"""
    try:
        # Get query parameters for what to include
        include_items = request.args.get('include_items', 'true').lower() == 'true'
        include_user = request.args.get('include_user', 'true').lower() == 'true'
        include_branch = request.args.get('include_branch', 'true').lower() == 'true'
        include_payment = request.args.get('include_payment', 'true').lower() == 'true'
        
        # Build the query with eager loading
        options = []
        if include_items:
            options.append(joinedload(Order.order_items).joinedload(OrderItem.menu_item))
        if include_user:
            options.append(joinedload(Order.user))
        if include_branch:
            options.append(joinedload(Order.branch))
        if include_payment:
            options.append(joinedload(Order.payment))
        
        order = Order.query.options(*options).filter(Order.id == order_id).first()
        
        if not order:
            return jsonify({"message": "Order not found"}), 404
        
        # Check authorization
        claims = get_jwt()
        is_admin = claims.get('role') in ['admin', 'super_admin']
        is_owner = str(order.user_id) == get_jwt_identity()
        
        if not (is_admin or is_owner):
            return jsonify({"message": "Unauthorized"}), 403
        
        # Convert to dictionary and return
        return jsonify(serialize_order(
            order,
            include_items=include_items,
            include_user=include_user,
            include_branch=include_branch,
            include_payment=include_payment
        ))
    
    except Exception as e:
        logger.error(f"Error getting order details: {str(e)}")
        return jsonify({"message": str(e)}), 500

@order_bp.route('/<string:order_id>/status', methods=['GET'])
@jwt_required()
@cross_origin(origins='http://localhost:3000')
def get_order_status(order_id):
    try:
        user_id_raw = get_jwt_identity()
        user_id = _int_id(user_id_raw)
        order = Order.query.get_or_404(order_id)
        if order.user_id != user_id and get_jwt().get('role') not in ['admin', 'super_admin']:
            return jsonify({"message": "Unauthorized"}), 403
        return jsonify({
            "status": order.status,
            "last_updated": _to_iso(getattr(order, 'updated_at', None)),
            "created_at": _to_iso(getattr(order, 'created_at', None))
        }), 200
    except Exception as e:
        logger.error(f"Error getting order status: {str(e)}")
        return jsonify({"message": str(e)}), 500

@order_bp.route('/<string:order_id>/can-cancel', methods=['GET'])
@jwt_required()
@cross_origin(origins='http://localhost:3000')
def can_cancel_order(order_id):
    """
    Check if an order can be cancelled
    """
    try:
        order = Order.query.get_or_404(order_id)
        claims = get_jwt()
        current_user_id = _int_id(get_jwt_identity())
        
        # Check authorization
        is_admin = claims.get('role') in ['admin', 'super_admin']
        is_owner = (order.user_id == current_user_id)
        
        if not (is_admin or is_owner):
            return jsonify({"message": "Unauthorized"}), 403
        
        # Check if order can be cancelled
        cancellable_statuses = ['pending', 'preparing']
        can_cancel = order.status in cancellable_statuses
        
        return jsonify({
            "can_cancel": can_cancel,
            "current_status": order.status,
            "cancellable_statuses": cancellable_statuses,
            "message": f"Order can{'' if can_cancel else 'not'} be cancelled" 
        }), 200
        
    except Exception as e:
        logger.error(f"Error checking order cancellation: {str(e)}")
        return jsonify({"message": str(e)}), 500

@order_bp.route('/<string:order_id>/status', methods=['PATCH'])
@jwt_required()
@cross_origin(origins='http://localhost:3000', methods=['PATCH'])
def update_order_status(order_id):
    try:
        # Enhanced logging
        logger.info(f"=== ORDER STATUS UPDATE REQUEST ===")
        logger.info(f"Order ID: {order_id}")
        logger.info(f"Request data: {request.get_json()}")
        logger.info(f"JWT Identity: {get_jwt_identity()}")
        logger.info(f"JWT Claims: {get_jwt()}")
        
        claims = get_jwt()
        current_user_id = _int_id(get_jwt_identity())
        data = request.get_json() or {}
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({
                "error": "missing_field",
                "message": "Status is required",
                "field": "status"
            }), 400
        
        order = Order.query.get_or_404(order_id)
        user_role = claims.get('role', 'customer')
        is_admin = user_role in ['admin', 'super_admin']
        is_owner = (order.user_id == current_user_id)
        
        if not (is_admin or is_owner):
            return jsonify({"message": "Unauthorized"}), 403
        
        # Validate transitions using helper function
        validation_errors = validate_status_transition(order.status, new_status, user_role)
        
        if validation_errors:
            return jsonify({
                "error": "invalid_status_transition",
                "message": "Status transition not allowed",
                "details": validation_errors,
                "current_status": order.status,
                "requested_status": new_status,
                "user_role": user_role
            }), 400
        
        # Store old status for notification
        old_status = order.status
        order.status = new_status
        order.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Order {order_id} status changed from {old_status} to {new_status}")
        
        # Non-fatal notify
        try:
            notify_order_update(order)
        except Exception as e:
            logger.error(f"Notification error for order status update: {str(e)}")
        
        return jsonify({
            "success": True,
            "order_id": order.id,
            "old_status": old_status,
            "new_status": new_status,
            "message": f"Order status updated to {new_status}"
        }), 200
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating order status: {str(e)}", exc_info=True)
        return jsonify({
            "error": "server_error", 
            "message": "Internal server error",
            "details": str(e)
        }), 500