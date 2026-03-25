from flask import Blueprint, request, jsonify
from app.utils.auth import token_required
from datetime import datetime
from app.models.analytics import ActivityLog  # Updated import
from app import db

activities_bp = Blueprint('activities', __name__, url_prefix='/api/v1/activities')

@activities_bp.route('/recent', methods=['GET', 'OPTIONS'])
@token_required(roles=['admin', 'super_admin'])
def get_recent_activities():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        limit = request.args.get('limit', 10, type=int)
        
        # Query to get recent activities using ActivityLog model
        activities = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(limit).all()

        result = []
        for activity in activities:
            result.append({
                "id": activity.id,
                "type": activity.type,
                "message": activity.message,
                "time": format_time_ago(activity.created_at)
            })
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"message": f"Error fetching recent activities: {str(e)}"}), 500

@activities_bp.route('/', methods=['POST', 'OPTIONS'])
@token_required(roles=['admin', 'super_admin'])
def log_activity():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        data = request.get_json()
        
        if not data or 'type' not in data or 'message' not in data:
            return jsonify({"message": "Type and message are required"}), 400
        
        # Create a new activity using ActivityLog model
        activity = ActivityLog(
            type=data['type'],
            message=data['message'],
            reference_id=data.get('reference_id'),
            created_at=datetime.now()
        )
        
        db.session.add(activity)
        db.session.commit()
        
        return jsonify({
            "id": activity.id,
            "type": activity.type,
            "message": activity.message,
            "reference_id": activity.reference_id,
            "created_at": activity.created_at.isoformat()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Error logging activity: {str(e)}"}), 500

def format_time_ago(dt):
    """Format a datetime as a human-readable time ago string"""
    now = datetime.now()
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    
    hours = diff.seconds // 3600
    if hours > 0:
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    
    minutes = (diff.seconds % 3600) // 60
    if minutes > 0:
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    
    return "Just now"