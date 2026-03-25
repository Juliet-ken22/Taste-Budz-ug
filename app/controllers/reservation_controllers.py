from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime
from app import db
from app.models.Branch import Branch
from app.models.Reservation import Reservation
from app.models.User import User
from flask_cors import CORS
import logging
from uuid import UUID

logger = logging.getLogger(__name__)

reservation_bp = Blueprint('reservation', __name__, url_prefix='/api/v1/reservation_bp')

# Configure CORS (unchanged)
CORS(
    reservation_bp,
    resources={
        r"/reservations/*": {
            "origins": "http://localhost:3000",
            "supports_credentials": True,
            "methods": ["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        },
        r"/admin/reservations*": {
            "origins": "http://localhost:3000",
            "supports_credentials": True,
            "methods": ["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    }
)


def format_reservation_response(reservation, include_user_details=False):
    """Helper function to format reservation response with no null values"""
    branch = Branch.query.get(reservation.branch_id)
    user = User.query.get(reservation.user_id) if include_user_details else None
    
    response = {
        "id": reservation.id,
        "user_id": reservation.user_id,
        "branch_id": reservation.branch_id,
        "branch_name": branch.name if branch else "Not Specified",
        "guests": reservation.guests,
        "reservation_time": reservation.reservation_time.isoformat(),
        "status": reservation.status,
        "transaction_id": reservation.transaction_id,
        "special_requests": reservation.special_requests,
        "created_at": reservation.created_at.isoformat()
    }
    
    if include_user_details:
        response.update({
            "user_email": user.email if user else "Not Available",
            "user_full_name": user.full_name if user else "Not Available",
            "user_phone": user.phone if user else "Not Available"
        })
    
    return response


@reservation_bp.route('/reservations', methods=['POST'])
@jwt_required()
def create_reservation():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    required_fields = ['branch_id', 'guests', 'reservation_time']
    if not all(field in data for field in required_fields):
        return jsonify({"message": "Missing required fields"}), 400
    
    try:
        time_obj = datetime.fromisoformat(data['reservation_time'])
        if time_obj < datetime.now():
            return jsonify({"message": "Reservation time must be in the future"}), 400
            
        if not Branch.query.get(data['branch_id']):
            return jsonify({"message": "Invalid branch"}), 400
            
        new_reservation = Reservation(
            user_id=user_id,
            branch_id=data['branch_id'],
            guests=data['guests'],
            reservation_time=time_obj,
            transaction_id=data.get('transaction_id', ''),
            special_requests=data.get('special_requests', ''),
        )
        
        db.session.add(new_reservation)
        db.session.commit()
        
        return jsonify({
            "message": "Reservation created successfully",
            "reservation": format_reservation_response(new_reservation)
        }), 201
        
    except ValueError:
        return jsonify({"message": "Invalid reservation time format. Use ISO 8601 format"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": str(e)}), 500


@reservation_bp.route('/reservations/my-reservations', methods=['GET'])
@jwt_required()
def get_user_reservations():
    try:
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({"message": "Invalid token"}), 401

        reservations = (
            db.session.query(Reservation)
            .filter(Reservation.user_id == user_id)
            .order_by(Reservation.reservation_time.desc())
            .all()
        )

        result = []
        for res in reservations:
            reservation_data = res.to_dict()
            reservation_data['branch_name'] = res.branch.name if res.branch else None
            result.append(reservation_data)

        return jsonify(result), 200
        
    except Exception as e:
        current_app.logger.error(f"Reservation fetch error: {str(e)}", exc_info=True)
        return jsonify({
            "message": "Failed to fetch reservations",
            "error": str(e)
        }), 500


@reservation_bp.route('/admin/reservations', methods=['GET'])
@jwt_required()
def get_all_reservations():
    claims = get_jwt()
    if not isinstance(claims, dict) or claims.get('role') not in ['admin', 'super_admin']:
        return jsonify({"message": "Unauthorized"}), 403
    
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    date_filter = request.args.get('date')
    status_filter = request.args.get('status')
    customer_name = request.args.get('customerName')

    query = Reservation.query
    
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(db.func.date(Reservation.reservation_time) == filter_date)
        except ValueError:
            return jsonify({"message": "Invalid date format. Use YYYY-MM-DD"}), 400
    
    if status_filter:
        query = query.filter(Reservation.status == status_filter)
    
    if customer_name:
        query = query.join(User).filter(User.full_name.ilike(f'%{customer_name}%'))
    
    paginated = query.order_by(Reservation.reservation_time.desc())\
        .paginate(page=page, per_page=limit, error_out=False)
    
    data = {
        "reservations": [
            format_reservation_response(res, include_user_details=True) 
            for res in paginated.items
        ],
        "total": paginated.total,
        "page": paginated.page,
        "limit": paginated.per_page,
        "pages": paginated.pages
    }
    
    return jsonify(data), 200


@reservation_bp.route('/reservations/<int:reservation_id>/status', methods=['PATCH'])
@jwt_required()
def update_reservation_status(reservation_id):
    try:
        claims = get_jwt()
        if not isinstance(claims, dict) or claims.get('role') not in ['admin', 'super_admin']:
            return jsonify({"message": "Unauthorized"}), 403
        
        reservation = Reservation.query.get_or_404(reservation_id)
        data = request.get_json()
        
        allowed_statuses = ['pending', 'confirmed', 'cancelled', 'completed']
        new_status = data.get('status')
        if not new_status or new_status not in allowed_statuses:
            return jsonify({
                "message": f"Invalid status. Allowed values: {', '.join(allowed_statuses)}"
            }), 400
        
        reservation.status = new_status
        reservation.transaction_id = data.get('transaction_id', reservation.transaction_id)
        
        db.session.commit()
        
        return jsonify({
            "message": f"Reservation status updated to {new_status}",
            "reservation": format_reservation_response(reservation)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Internal server error: {str(e)}"}), 500


@reservation_bp.route('/admin/reservations/<int:reservation_id>', methods=['DELETE'])
@jwt_required()
def delete_reservation(reservation_id):
    claims = get_jwt()
    if not isinstance(claims, dict) or claims.get('role') not in ['admin', 'super_admin']:
        return jsonify({"message": "Unauthorized"}), 403
    
    reservation = Reservation.query.get_or_404(reservation_id)
    db.session.delete(reservation)
    db.session.commit()
    
    return jsonify({
        "message": "Reservation deleted successfully",
        "deleted_id": reservation_id
    }), 200
