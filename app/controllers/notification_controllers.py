from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.models.notification import Notification
from app.models.User import User
from app import db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

notification_bp = Blueprint('notification', __name__, url_prefix='/api/v1/notifications')

# Before request handler to manage preflight requests
# @notification_bp.before_request
# def handle_preflight():
#     if request.method == "OPTIONS":
#         response = jsonify({"status": "success"})
#         response.headers.add("Access-Control-Allow-Origin", "http://localhost:3000")
#         response.headers.add("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
#         response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
#         return response

# Explicit OPTIONS handlers for each route
@notification_bp.route('/', methods=['OPTIONS'])
def options_notifications():
    return jsonify({"status": "success"})

@notification_bp.route('/<int:notification_id>/read', methods=['OPTIONS'])
def options_mark_read():
    return jsonify({"status": "success"})

@notification_bp.route('/mark-all-read', methods=['OPTIONS'])
def options_mark_all_read():
    return jsonify({"status": "success"})

@notification_bp.route('/unread-count', methods=['OPTIONS'])
def options_unread_count():
    return jsonify({"status": "success"})

@notification_bp.route('/clear-all', methods=['OPTIONS'])
def options_clear_all():
    return jsonify({"status": "success"})

# GET all notifications
@notification_bp.route('/', methods=['GET'])
@jwt_required()
def get_notifications():
    try:
        claims = get_jwt()
        user_id = get_jwt_identity()
        
        is_admin = isinstance(claims, dict) and claims.get('role') in ['admin', 'super_admin']
        admin_view = request.args.get('admin_view', '').lower() == 'true' and is_admin
        
        # Base query
        query = Notification.query.order_by(Notification.created_at.desc())
        
        if not admin_view:
            query = query.filter_by(recipient_id=user_id)
        else:
            # Admins can see all notifications but we'll limit to recent ones
            query = query.limit(100)
        
        notifications = query.all()
        
        return jsonify({
            "success": True,
            "data": [{
                "id": note.id,
                "type": note.type,
                "message": note.message,
                "is_read": note.is_read,
                "created_at": note.created_at.isoformat() if note.created_at else None,
                "related_id": note.related_id,
                "recipient_id": note.recipient_id
            } for note in notifications]
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching notifications: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Failed to fetch notifications",
            "error": str(e)
        }), 500

# POST create new notification
@notification_bp.route('/', methods=['POST'])
@jwt_required()
def create_notification():
    try:
        claims = get_jwt()
        data = request.get_json()
        
        # Validate required fields
        if not data:
            return jsonify({
                "success": False,
                "error": "invalid_request",
                "message": "Request body is required"
            }), 400
        
        # Check if user is admin to send to others
        is_admin = isinstance(claims, dict) and claims.get('role') in ['admin', 'super_admin']
        user_id = get_jwt_identity()
        
        recipient_id = data.get('recipient_id')
        
        # If no recipient_id provided and user is not admin, send to self
        if not recipient_id and not is_admin:
            recipient_id = user_id
        elif not recipient_id and is_admin:
            # Admin sending to all users - this would require broadcast functionality
            return jsonify({
                "success": False,
                "error": "missing_recipient",
                "message": "Recipient ID is required for admin notifications"
            }), 400
        
        # Validate recipient exists if specific recipient is provided
        if recipient_id and recipient_id != 'broadcast':
            recipient = User.query.get(recipient_id)
            if not recipient:
                return jsonify({
                    "success": False,
                    "error": "invalid_recipient",
                    "message": "Recipient user not found"
                }), 404
        
        # Validate message
        message = data.get('message', '').strip()
        if not message:
            return jsonify({
                "success": False,
                "error": "missing_message",
                "message": "Message is required"
            }), 400
        
        # Create notification
        new_notification = Notification(
            recipient_id=recipient_id if recipient_id != 'broadcast' else None,
            type=data.get('type', 'general'),
            message=message,
            related_id=data.get('related_id'),
            is_read=False
        )
        
        db.session.add(new_notification)
        db.session.commit()
        
        # Emit WebSocket event if available
        try:
            from app.socketio_handler import socketio
            if socketio:
                socketio.emit('new_notification', {
                    'id': new_notification.id,
                    'type': new_notification.type,
                    'message': new_notification.message,
                    'recipient_id': new_notification.recipient_id,
                    'created_at': new_notification.created_at.isoformat() if new_notification.created_at else None
                }, room=str(recipient_id) if recipient_id != 'broadcast' else None)
        except Exception as ws_error:
            logger.warning(f"WebSocket emission failed: {str(ws_error)}")
        
        return jsonify({
            "success": True,
            "message": "Notification created successfully",
            "data": {
                "id": new_notification.id,
                "recipient_id": new_notification.recipient_id,
                "type": new_notification.type,
                "message": new_notification.message
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating notification: {str(e)}")
        return jsonify({
            "success": False,
            "error": "server_error",
            "message": "Internal server error"
        }), 500

# PUT mark notification as read
@notification_bp.route('/<int:notification_id>/read', methods=['PUT'])
@jwt_required()
def mark_notification_read(notification_id):
    try:
        claims = get_jwt()
        user_id = get_jwt_identity()
        
        notification = Notification.query.get(notification_id)
        if not notification:
            return jsonify({
                "success": False,
                "message": "Notification not found"
            }), 404
            
        # Check permissions
        is_admin = isinstance(claims, dict) and claims.get('role') in ['admin', 'super_admin']
        if (str(notification.recipient_id) != user_id and not is_admin):
            return jsonify({
                "success": False,
                "message": "Unauthorized"
            }), 403
        
        notification.is_read = True
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Notification marked as read",
            "data": {
                "notification_id": notification_id,
                "is_read": True
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error marking notification as read: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Failed to mark notification as read"
        }), 500

# POST mark all notifications as read
@notification_bp.route('/mark-all-read', methods=['POST'])
@jwt_required()
def mark_all_notifications_read():
    try:
        claims = get_jwt()
        user_id = get_jwt_identity()
        
        # Get all unread notifications for the user
        unread_notifications = Notification.query.filter_by(
            recipient_id=user_id, 
            is_read=False
        ).all()
        
        # Update each notification to mark as read
        for notification in unread_notifications:
            notification.is_read = True
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "All notifications marked as read"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error marking all notifications as read: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Failed to mark all notifications as read"
        }), 500

# GET unread notification count
@notification_bp.route('/unread-count', methods=['GET'])
@jwt_required()
def get_unread_count():
    try:
        user_id = get_jwt_identity()
        
        count = Notification.query.filter_by(
            recipient_id=user_id, 
            is_read=False
        ).count()
        
        return jsonify({
            "success": True,
            "data": {
                "unread_count": count
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting unread count: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Failed to get unread count"
        }), 500

# DELETE clear all notifications
@notification_bp.route('/clear-all', methods=['DELETE'])
@jwt_required()
def clear_all_notifications():
    try:
        claims = get_jwt()
        user_id = get_jwt_identity()
        
        # Both admins and regular users can only clear their own notifications
        # This is safer than allowing admins to clear all notifications
        Notification.query.filter_by(recipient_id=user_id).delete()
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "All notifications cleared successfully"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error clearing notifications: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Failed to clear notifications"
        }), 500

# Helper function to create notifications from other parts of the system
def create_system_notification(recipient_id=None, message="", notification_type="system", related_id=None):
    """
    Helper function to create system notifications
    """
    try:
        notification = Notification(
            recipient_id=recipient_id,
            type=notification_type,
            message=message,
            related_id=related_id,
            is_read=False
        )
        db.session.add(notification)
        db.session.commit()
        
        # Emit WebSocket event
        try:
            from app.socketio_handler import socketio
            if socketio and recipient_id:
                socketio.emit('new_notification', {
                    'id': notification.id,
                    'type': notification.type,
                    'message': notification.message,
                    'recipient_id': notification.recipient_id,
                    'created_at': notification.created_at.isoformat() if notification.created_at else None
                }, room=str(recipient_id))
        except Exception as ws_error:
            logger.warning(f"WebSocket emission failed: {str(ws_error)}")
            
        return notification
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating system notification: {str(e)}")
        return None