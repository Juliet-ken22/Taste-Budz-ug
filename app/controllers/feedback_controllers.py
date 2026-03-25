from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app import db
from app.models.Feedback import Feedback
from datetime import datetime

feedback_bp = Blueprint('feedback', __name__, url_prefix='/api/v1/feedback_bp')

@feedback_bp.route('feedback', methods=['POST'])
@jwt_required()
def submit_feedback():
    user_id = get_jwt_identity()
    data = request.get_json()

    # Validate required fields
    if not data.get('message'):
        return jsonify({"success": False, "message": "Message content is required"}), 400

    try:
        feedback = Feedback(
            user_id=user_id,
            message=data.get('message'),
            rating=data.get('rating'),
            branch_id=data.get('branch_id'),
            status='pending'  # Default status
        )
        
        db.session.add(feedback)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Feedback submitted successfully",
            "data": feedback.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Failed to submit feedback",
            "error": str(e)
        }), 500

@feedback_bp.route('feedback', methods=['GET'])
@jwt_required()
def get_all_feedback():
    claims = get_jwt()
    
    # Authorization check
    if not isinstance(claims, dict) or claims.get('role') not in ['admin', 'super_admin']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        # Get query parameters
        status = request.args.get('status')
        branch_id = request.args.get('branch_id')
        min_rating = request.args.get('min_rating')
        search = request.args.get('search')
        
        # Base query
        query = Feedback.query
        
        # Apply filters
        if status and status.lower() != 'all':
            query = query.filter(Feedback.status == status.lower())
            
        if branch_id:
            query = query.filter(Feedback.branch_id == branch_id)
            
        if min_rating:
            query = query.filter(Feedback.rating >= int(min_rating))
            
        if search:
            search_term = f"%{search}%"
            query = query.filter(Feedback.message.ilike(search_term))
        
        # Order and execute
        feedbacks = query.order_by(Feedback.created_at.desc()).all()
        
        # Prepare response
        feedback_list = [fb.to_dict() for fb in feedbacks]
        
        return jsonify({
            "success": True,
            "data": feedback_list,
            "count": len(feedback_list)
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to fetch feedback",
            "error": str(e)
        }), 500

@feedback_bp.route('/<int:feedback_id>/status', methods=['PATCH'])
@jwt_required()
def update_feedback_status(feedback_id):
    claims = get_jwt()
    
    # Authorization check
    if not isinstance(claims, dict) or claims.get('role') not in ['admin', 'super_admin']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    data = request.get_json()
    new_status = data.get('status')
    
    if not new_status or new_status not in ['pending', 'reviewed', 'resolved']:
        return jsonify({
            "success": False,
            "message": "Valid status is required (pending, reviewed, resolved)"
        }), 400

    try:
        feedback = Feedback.query.get_or_404(feedback_id)
        feedback.status = new_status
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Feedback status updated successfully",
            "data": feedback.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Failed to update feedback status",
            "error": str(e)
        }), 500