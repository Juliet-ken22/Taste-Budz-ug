from functools import wraps
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from app import db
from app.models.Branch import Branch
from app.models.User import User
import logging

# Setup
branch_bp = Blueprint('branch_bp', __name__, url_prefix='/api/v1')
logger = logging.getLogger(__name__)

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            claims = get_jwt()
            if not isinstance(claims, dict) or claims.get('role') not in ['admin', 'super_admin']:
                return jsonify({
                    "success": False,
                    "message": "Admin access required",
                    "data": None
                }), 403
            return fn(*args, **kwargs)
        except Exception as e:
            logger.error(f"Authorization error: {str(e)}")
            return jsonify({
                "success": False,
                "message": "Authorization failed",
                "data": None
            }), 500
    return wrapper

# OPTIONS handler for branches list
@branch_bp.route('/branches', methods=['OPTIONS'])
def branches_options():
    response = jsonify({'status': 'ok'})
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PATCH, PUT, DELETE')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, x-branch-id, X-Requested-With, X-Request-ID, X-Client-Version, X-Request-Timestamp, X-Client-Platform')
    return response

# OPTIONS handler for branch detail
@branch_bp.route('/branches/<string:branch_id>', methods=['OPTIONS'])
def branch_detail_options():
    response = jsonify({'status': 'ok'})
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
    response.headers.add('Access-Control-Allow-Methods', 'GET, PUT, DELETE, OPTIONS')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, x-branch-id, X-Requested-With, X-Request-ID, X-Client-Version, X-Request-Timestamp, X-Client-Platform')
    return response

# OPTIONS handler for branch dashboard
@branch_bp.route('/branches/<string:branch_id>/dashboard', methods=['OPTIONS'])
def branch_dashboard_options():
    response = jsonify({'status': 'ok'})
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
    response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, x-branch-id, X-Requested-With, X-Request-ID, X-Client-Version, X-Request-Timestamp, X-Client-Platform')
    return response

@branch_bp.route('/branches', methods=['GET'])
def get_branches():
    """Get all branches with consistent response structure"""
    try:
        # Get optional query parameters
        active_only = request.args.get('active', 'true').lower() == 'true'
        
        # Build query
        query = Branch.query
        if active_only:
            query = query.filter_by(is_active=True)
        
        # Order by creation date for consistent sequential IDs
        branches = query.order_by(Branch.created_at.asc()).all()
        
        # Format response data with sequential IDs
        branches_data = [{
            "seq_id": idx + 1,  # Sequential ID starting from 1
            "id": branch.id,    # Keep UUID for internal operations
            "name": branch.name,
            "address": branch.address,
            "phone": branch.phone,
            "is_active": branch.is_active,
            "created_at": branch.created_at.isoformat() if branch.created_at else None
        } for idx, branch in enumerate(branches)]
        
        return jsonify({
            "success": True,
            "message": "Branches retrieved successfully",
            "data": branches_data
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching branches: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Failed to fetch branches",
            "data": None
        }), 500

@branch_bp.route('/branches/<string:branch_id>', methods=['GET'])
def get_branch(branch_id):
    """Get single branch by ID"""
    try:
        branch = Branch.query.get_or_404(branch_id)
        
        # Get sequential ID by counting branches created before this one
        seq_id = Branch.query.filter(
            Branch.created_at <= branch.created_at,
            Branch.is_active == True
        ).count()
        
        return jsonify({
            "success": True,
            "message": "Branch retrieved successfully",
            "data": {
                "seq_id": seq_id,  # Sequential ID
                "id": branch.id,   # UUID
                "name": branch.name,
                "address": branch.address,
                "phone": branch.phone,
                "is_active": branch.is_active,
                "created_at": branch.created_at.isoformat() if branch.created_at else None
            }
        }), 200
    except Exception as e:
        logger.error(f"Error fetching branch {branch_id}: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Branch not found",
            "data": None
        }), 404

@branch_bp.route('/branches', methods=['POST'])
@jwt_required()
@admin_required
def create_branch():
    """Create new branch with validation"""
    try:
        if not request.is_json:
            return jsonify({
                "success": False,
                "message": "Request must be JSON",
                "data": None
            }), 400

        data = request.get_json()
        required_fields = ['name', 'address']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                "success": False,
                "message": f"Missing required fields: {', '.join(missing_fields)}",
                "data": None
            }), 400

        branch = Branch(
            name=data['name'].strip(),
            address=data['address'].strip(),
            phone=data.get('phone', '').strip(),
            is_active=data.get('is_active', True)
        )

        db.session.add(branch)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Branch created successfully",
            "data": {
                "id": branch.id,
                "name": branch.name
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating branch: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Failed to create branch",
            "data": None
        }), 500

@branch_bp.route('/branches/<string:branch_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_branch(branch_id):
    """Update existing branch"""
    try:
        branch = Branch.query.get_or_404(branch_id)
        
        if not request.is_json:
            return jsonify({
                "success": False,
                "message": "Request must be JSON",
                "data": None
            }), 400

        data = request.get_json()
        
        if 'name' in data:
            branch.name = data['name'].strip()
        if 'address' in data:
            branch.address = data['address'].strip()
        if 'phone' in data:
            branch.phone = data['phone'].strip()
        if 'is_active' in data:
            branch.is_active = bool(data['is_active'])

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Branch updated successfully",
            "data": {
                "id": branch.id
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating branch {branch_id}: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Failed to update branch",
            "data": None
        }), 500

@branch_bp.route('/branches/<string:branch_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_branch(branch_id):
    """Soft delete branch"""
    try:
        branch = Branch.query.get_or_404(branch_id)
        branch.is_active = False
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Branch deactivated successfully",
            "data": {
                "id": branch_id
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deactivating branch {branch_id}: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Failed to deactivate branch",
            "data": None
        }), 500

@branch_bp.route('/branches/<string:branch_id>/dashboard', methods=['GET'])
@jwt_required()
def branch_dashboard(branch_id):
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404

    # Only allow if user is assigned to branch or is super_admin
    if user.role != "super_admin" and user.branch_id != branch_id:
        return jsonify({"success": False, "message": "Access denied for this branch"}), 403

    branch = Branch.query.get_or_404(branch_id)
    # Example dashboard data
    return jsonify({
        "success": True,
        "message": f"Welcome to {branch.name} dashboard",
        "data": {
            "branch_id": branch.id,
            "branch_name": branch.name
        }
    }), 200