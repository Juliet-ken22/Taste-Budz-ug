# app/socketio_handler.py
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_jwt_extended import jwt_required, get_jwt_identity, decode_token
from flask import request
from app import db
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

socketio = SocketIO(cors_allowed_origins="*", logger=True, engineio_logger=True)

def init_socketio(app):
    socketio.init_app(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')
    # Don't authenticate here, wait for the authenticate event

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')

@socketio.on('authenticate')
def handle_authentication(data):
    try:
        token = data.get('token')
        if not token:
            logger.warning('Authentication attempt without token')
            emit('authentication_failed', {'message': 'No token provided'})
            return False
        
        try:
            decoded_token = decode_token(token)
            user_id = decoded_token['sub']
            user_role = decoded_token.get('role', 'user')
            
            # Store user info in the session
            request.sid_user_id = user_id
            request.sid_user_role = user_role
            
            # Join user-specific room
            join_room(f"user_{user_id}")
            
            # Join role-specific room
            join_room(f"role_{user_role}")
            
            logger.info(f"Authenticated user {user_id} with role {user_role} via WebSocket")
            emit('authentication_success', {'user_id': user_id, 'role': user_role})
            return True
        except Exception as e:
            logger.error(f"Token decode error: {str(e)}")
            emit('authentication_failed', {'message': 'Invalid token'})
            return False
    except Exception as e:
        logger.error(f"WebSocket authentication failed: {str(e)}")
        emit('authentication_failed', {'message': 'Authentication failed'})
        return False

# ... rest of the functions remain the same ...

@socketio.on('join_room')
@jwt_required()
def on_join(data):
    user_id = get_jwt_identity()
    room = data.get('room')
    if room:
        join_room(room)
        emit('status', {'message': f'{user_id} has entered the room.'}, room=room)
        logger.info(f"User {user_id} joined room {room}")

@socketio.on('leave_room')
@jwt_required()
def on_leave(data):
    user_id = get_jwt_identity()
    room = data.get('room')
    if room:
        leave_room(room)
        emit('status', {'message': f'{user_id} has left the room.'}, room=room)
        logger.info(f"User {user_id} left room {room}")

@socketio.on('send_message')
@jwt_required()
def on_message(data):
    user_id = get_jwt_identity()
    room = data.get('room')
    message = data.get('message')
    
    if room and message:
        emit('new_message', {
            'user_id': user_id,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }, room=room)
        logger.info(f"Message from {user_id} in room {room}: {message}")

# Helper functions to send notifications
def notify_new_order(order_data):
    logger.info(f"Broadcasting new order: {order_data.get('id')}")
    socketio.emit('order_update', order_data, room='role_admin')
    socketio.emit('order_update', order_data, room='role_super_admin')

def notify_new_reservation(reservation_data):
    logger.info(f"Broadcasting new reservation: {reservation_data.get('id')}")
    socketio.emit('reservation_update', reservation_data, room='role_admin')
    socketio.emit('reservation_update', reservation_data, room='role_super_admin')

def notify_reservation_update(reservation_data):
    """Send notification when a reservation is updated"""
    logger.info(f"Broadcasting reservation update: {reservation_data.get('id')}")
    socketio.emit('reservation_update', reservation_data, room='role_admin')
    socketio.emit('reservation_update', reservation_data, room='role_super_admin')

def notify_new_notification(notification_data):
    recipient_id = notification_data.get('recipient_id')
    if recipient_id:
        logger.info(f"Sending notification to user {recipient_id}")
        socketio.emit('notification', notification_data, room=f"user_{recipient_id}")
    else:
        logger.info("Broadcasting notification to all users")
        socketio.emit('notification', notification_data)