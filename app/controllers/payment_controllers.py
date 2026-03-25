from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app import db
from app.models.PaymentAccount import PaymentAccount
from app.models.Payment import Payment
from app.models.Order import Order
from app.models.Reservation import Reservation
from app.models.User import User
from app.models.Branch import Branch # Added import for Branch model

payment_bp = Blueprint('payment', __name__, url_prefix='/api/v1/payment_bp')

# 🔓 GET /payment-accounts – Customers view merchant accounts
@payment_bp.route('/payment-accounts', methods=['GET'])
def list_payment_accounts():
    # Get branch_id from query parameters if provided
    branch_id = request.args.get('branch_id', type=int)
    
    # Filter accounts by branch_id if provided, otherwise get all accounts
    if branch_id:
        accounts = PaymentAccount.query.filter_by(branch_id=branch_id).all()
    else:
        accounts = PaymentAccount.query.all()
    
    data = []
    for acc in accounts:
        # Get branch name if branch_id exists
        branch_name = None
        if acc.branch_id:
            branch = Branch.query.get(acc.branch_id)
            branch_name = branch.name if branch else None
            
        data.append({
            "id": acc.id,
            "method_name": acc.method_name,
            "merchant_id": acc.merchant_id,
            "merchant_name": acc.merchant_name,
            "instructions": acc.instructions,
            "branch_id": acc.branch_id,
            "branch_name": branch_name
        })
    return jsonify(data), 200

# 🔐 POST /payment-accounts – Admin adds account
@payment_bp.route('/payment-accounts', methods=['POST'])
@jwt_required()
def create_payment_account():
    claims = get_jwt()
    if not isinstance(claims, dict) or claims.get('role') not in ['admin', 'super_admin']:
        return jsonify({"message": "Unauthorized"}), 403

    data = request.get_json()
    method_name = data.get('method_name')
    merchant_id = data.get('merchant_id')
    merchant_name = data.get('merchant_name')
    instructions = data.get('instructions')
    branch_id = data.get('branch_id') # New field

    if not all([method_name, merchant_id, merchant_name]):
        return jsonify({"message": "Method name, merchant ID, and merchant name are required"}), 400

    # Validate branch_id if provided
    if branch_id is not None:
        branch = Branch.query.get(branch_id)
        if not branch:
            return jsonify({"message": "Branch not found"}), 404

    account = PaymentAccount(
        method_name=method_name,
        merchant_id=merchant_id,
        merchant_name=merchant_name,
        instructions=instructions,
        branch_id=branch_id # Set branch_id
    )
    db.session.add(account)
    db.session.commit()
    return jsonify({"message": "Payment account added", "id": account.id}), 201

# 🔐 PUT /payment-accounts/<id> – Admin updates account
@payment_bp.route('/payment-accounts/<int:acc_id>', methods=['PUT'])
@jwt_required()
def update_payment_account(acc_id):
    claims = get_jwt()
    if not isinstance(claims, dict) or claims.get('role') not in ['admin', 'super_admin']:
        return jsonify({"message": "Unauthorized"}), 403

    account = PaymentAccount.query.get_or_404(acc_id)
    data = request.get_json()

    account.method_name = data.get('method_name', account.method_name)
    account.merchant_id = data.get('merchant_id', account.merchant_id)
    account.merchant_name = data.get('merchant_name', account.merchant_name)
    account.instructions = data.get('instructions', account.instructions)
    
    # Update branch_id if provided
    if 'branch_id' in data:
        branch_id = data.get('branch_id')
        if branch_id is not None:
            branch = Branch.query.get(branch_id)
            if not branch:
                return jsonify({"message": "Branch not found"}), 404
        account.branch_id = branch_id

    db.session.commit()
    return jsonify({"message": "Payment account updated"}), 200

# 🔐 DELETE /payment-accounts/<id> – Admin deletes
@payment_bp.route('/payment-accounts/<int:acc_id>', methods=['DELETE'])
@jwt_required()
def delete_payment_account(acc_id):
    claims = get_jwt()
    if not isinstance(claims, dict) or claims.get('role') not in ['admin', 'super_admin']:
        return jsonify({"message": "Unauthorized"}), 403

    account = PaymentAccount.query.get_or_404(acc_id)
    db.session.delete(account)
    db.session.commit()
    return jsonify({"message": "Payment account deleted"}), 200

# 🔐 POST /payments – Customer submits transaction ID
@payment_bp.route('/payments', methods=['POST'])
@jwt_required()
def submit_payment():
    user_id = get_jwt_identity()
    data = request.get_json()

    payment_type = data.get('payment_type')  # "order" or "reservation"
    reference_id = data.get('reference_id')
    transaction_id = data.get('transaction_id')
    amount = data.get('amount')
    payment_account_id = data.get('payment_account_id') # New field

    if payment_type not in ['order', 'reservation']:
        return jsonify({"message": "Invalid payment_type. Must be 'order' or 'reservation'"}), 400
    
    if not all([reference_id, transaction_id, amount]):
        return jsonify({"message": "Missing data: reference_id, transaction_id, and amount are required"}), 400

    # Optional: Verify if the reference_id exists for the given type
    if payment_type == 'order':
        if not Order.query.get(reference_id):
            return jsonify({"message": f"Order with ID {reference_id} not found"}), 404
    elif payment_type == 'reservation':
        if not Reservation.query.get(reference_id):
            return jsonify({"message": f"Reservation with ID {reference_id} not found"}), 404

    # Validate payment_account_id if provided
    if payment_account_id:
        payment_account = PaymentAccount.query.get(payment_account_id)
        if not payment_account:
            return jsonify({"message": "Payment account not found"}), 404

    payment = Payment(
        user_id=user_id,
        payment_type=payment_type,
        reference_id=reference_id,
        transaction_id=transaction_id,
        amount=amount,
        payment_account_id=payment_account_id # Set payment_account_id
    )
    db.session.add(payment)
    db.session.commit()
    return jsonify({"message": "Payment submitted", "payment_id": payment.id}), 201

# 🔐 GET /payments – Admin fetches all customer payments
@payment_bp.route('/payments', methods=['GET'])
@jwt_required()
def list_payments():
    claims = get_jwt()
    if not isinstance(claims, dict) or claims.get('role') not in ['admin', 'super_admin']:
        return jsonify({"message": "Unauthorized"}), 403

    payments = Payment.query.order_by(Payment.created_at.desc()).all()
    data = []
    for p in payments:
        user_details = User.query.get(p.user_id)
        payment_account = PaymentAccount.query.get(p.payment_account_id) if p.payment_account_id else None
        
        data.append({
            "id": p.id,
            "user_id": p.user_id,
            "user_email": user_details.email if user_details else "N/A",
            "reference_type": p.payment_type,
            "reference_id": p.reference_id,
            "transaction_id": p.transaction_id,
            "amount": p.amount,
            "payment_account_id": p.payment_account_id,
            "payment_method": payment_account.method_name if payment_account else "N/A",
            "created_at": p.created_at.isoformat()
        })
    return jsonify(data), 200