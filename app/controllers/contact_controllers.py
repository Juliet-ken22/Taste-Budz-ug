from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request, get_jwt
from app import db
from app.models.ContactMessage import ContactMessage
from datetime import datetime

contact_bp = Blueprint('contact', __name__, url_prefix='/api/v1')

def optional_jwt():
    try:
        verify_jwt_in_request()
        g.current_user_id = get_jwt_identity() 
        g.current_user_claims = get_jwt()
    except Exception:
        g.current_user_id = None
        g.current_user_claims = None

@contact_bp.route('/contact-messages', methods=['POST'])
def submit_contact_message():
    optional_jwt()
    user_id = g.current_user_id 

    data = request.get_json()
    message = data.get('message')
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')

    if not message:
        return jsonify({"message": "Message content is required"}), 400

    try:
        contact = ContactMessage(
            user_id=user_id,
            name=name,
            email=email,
            phone=phone,
            message=message,
            status='new'  # Set initial status
        )
        db.session.add(contact)
        db.session.commit()
        
        return jsonify({
            "message": "Message received successfully",
            "data": {
                "id": contact.id,
                "name": contact.name,
                "email": contact.email,
                "phone": contact.phone,
                "message": contact.message,
                "status": contact.status,
                "created_at": contact.created_at.isoformat()
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to save message", "error": str(e)}), 500

@contact_bp.route('/contact-messages', methods=['GET', 'OPTIONS'])
@jwt_required()
def get_contact_messages():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    claims = get_jwt()
    if not isinstance(claims, dict) or claims.get('role') not in ['admin', 'super_admin']:
        return jsonify({"message": "Unauthorized"}), 403

    try:
        # Get query parameters for filtering
        status_filter = request.args.get('status', default=None)
        search_term = request.args.get('search', default=None)
        
        # Base query
        query = ContactMessage.query.order_by(ContactMessage.created_at.desc())
        
        # Apply filters if provided
        if status_filter and status_filter.lower() != 'all':
            query = query.filter(ContactMessage.status == status_filter.lower())
            
        if search_term:
            search = f"%{search_term}%"
            query = query.filter(
                db.or_(
                    ContactMessage.name.ilike(search),
                    ContactMessage.email.ilike(search),
                    ContactMessage.message.ilike(search)
                )
            )
        
        messages = query.all()
        
        # Format the response
        messages_data = []
        for msg in messages:
            messages_data.append({
                "id": msg.id,
                "user_id": msg.user_id,
                "name": msg.name,
                "email": msg.email,
                "phone": msg.phone,
                "message": msg.message,
                "status": msg.status,
                "created_at": msg.created_at.isoformat() if msg.created_at else None
            })
        
        return jsonify({
            "success": True,
            "data": messages_data,
            "count": len(messages_data)
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to fetch contact messages",
            "error": str(e)
        }), 500

# Add endpoint to update message status
@contact_bp.route('/contact-messages/<int:message_id>/status', methods=['PATCH', 'OPTIONS'])
@jwt_required()
def update_message_status(message_id):
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    claims = get_jwt()
    if not isinstance(claims, dict) or claims.get('role') not in ['admin', 'super_admin']:
        return jsonify({"message": "Unauthorized"}), 403

    data = request.get_json()
    new_status = data.get('status')
    
    if not new_status:
        return jsonify({"message": "Status is required"}), 400
    
    valid_statuses = ['new', 'read', 'archived', 'replied']
    if new_status not in valid_statuses:
        return jsonify({"message": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"}), 400

    try:
        message = ContactMessage.query.get_or_404(message_id)
        message.status = new_status
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Status updated successfully",
            "data": {
                "id": message.id,
                "status": message.status
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Failed to update status",
            "error": str(e)
        }), 500

# Add endpoint to get a single message
@contact_bp.route('/contact-messages/<int:message_id>', methods=['GET', 'OPTIONS'])
@jwt_required()
def get_contact_message(message_id):
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    claims = get_jwt()
    if not isinstance(claims, dict) or claims.get('role') not in ['admin', 'super_admin']:
        return jsonify({"message": "Unauthorized"}), 403

    try:
        message = ContactMessage.query.get_or_404(message_id)
        
        return jsonify({
            "success": True,
            "data": {
                "id": message.id,
                "user_id": message.user_id,
                "name": message.name,
                "email": message.email,
                "phone": message.phone,
                "message": message.message,
                "status": message.status,
                "created_at": message.created_at.isoformat() if message.created_at else None,
                "updated_at": message.updated_at.isoformat() if message.updated_at else None
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to fetch contact message",
            "error": str(e)
        }), 500