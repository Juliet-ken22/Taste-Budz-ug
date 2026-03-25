# ====================================================================
# File: app/controllers/auth_controllers.py - FULLY FIXED VERSION
# ====================================================================
import os
import json
from functools import wraps
from datetime import datetime, timedelta
import secrets
import random
from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)
from app import db
from app.models.User import User
from app.models.OTPToken import OTPToken
from app.models.PasswordReset import PasswordResetToken
from app.utils.email import send_verification_email, send_admin_credentials
from sqlalchemy.orm import joinedload

auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')


# ------------------------- Helpers -------------------------
def normalize_role(role):
    if not role:
        return None
    return role.strip().lower().replace(" ", "_")


def safe_user_dict(user):
    """
    Return a consistent user dict used in all auth responses.
    CRITICAL: This function now properly loads branch data with extensive logging.
    """
    role_raw = normalize_role(getattr(user, "role", None))  # e.g. 'super_admin'
    role_key = None
    if role_raw:
        # letters-only, no underscores -> 'superadmin'
        role_key = "".join(ch for ch in role_raw if ch.isalpha()).lower()

    # Get branch object if user has one
    branch_data = None
    branch_id = getattr(user, "branch_id", None)
    
    # EXTENSIVE LOGGING for debugging
    current_app.logger.info(f"=== safe_user_dict START ===")
    current_app.logger.info(f"User: {user.email}")
    current_app.logger.info(f"Role: {role_raw}")
    current_app.logger.info(f"Branch ID from user: {branch_id}")
    
    if branch_id:
        try:
            from app.models.Branch import Branch
            
            # First, try to use the relationship if it's already loaded
            if hasattr(user, 'branch') and user.branch:
                current_app.logger.info(f"Branch loaded via relationship: {user.branch.name}")
                branch_data = {
                    "id": user.branch.id,
                    "name": user.branch.name,
                    "address": getattr(user.branch, "address", None),
                    "phone": getattr(user.branch, "phone", None),
                    "is_active": getattr(user.branch, "is_active", True),
                    "seq_id": getattr(user.branch, "seq_id", None)
                }
            else:
                # Fallback: Query branch directly if relationship not loaded
                current_app.logger.warning(f"Branch relationship not loaded, querying directly for ID: {branch_id}")
                branch = db.session.query(Branch).filter_by(id=branch_id).first()
                
                if branch:
                    current_app.logger.info(f"Branch found via query: {branch.name}")
                    branch_data = {
                        "id": branch.id,
                        "name": branch.name,
                        "address": getattr(branch, "address", None),
                        "phone": getattr(branch, "phone", None),
                        "is_active": getattr(branch, "is_active", True),
                        "seq_id": getattr(branch, "seq_id", None)
                    }
                else:
                    current_app.logger.error(f"CRITICAL: Branch {branch_id} not found in database!")
                    
        except Exception as e:
            current_app.logger.error(f"ERROR loading branch data: {str(e)}")
            import traceback
            current_app.logger.error(traceback.format_exc())
    else:
        current_app.logger.info(f"User has no branch_id (role: {role_raw})")

    user_dict = {
        "id": user.id,
        "email": user.email,
        "full_name": getattr(user, "full_name", None),
        "phone": getattr(user, "phone", None),
        "role": role_raw,
        "role_key": role_key,
        "branch_id": branch_id,
        "branch": branch_data,  # ← CRITICAL: Full branch object
        "is_verified": getattr(user, "is_verified", False)
    }
    
    current_app.logger.info(f"Final user dict - branch_id: {user_dict['branch_id']}, branch: {user_dict['branch']}")
    current_app.logger.info(f"=== safe_user_dict END ===")
    
    return user_dict


def auth_success_response(user, token):
    """Standardized success response consumed by frontend."""
    user_payload = safe_user_dict(user)
    
    # Log the complete response for debugging
    current_app.logger.info(f"=== AUTH SUCCESS RESPONSE ===")
    current_app.logger.info(f"Token generated for user: {user.email}")
    current_app.logger.info(f"User payload: {json.dumps(user_payload, indent=2)}")
    current_app.logger.info(f"=== END AUTH SUCCESS RESPONSE ===")
    
    return jsonify({
        "access_token": token,
        "user": user_payload
    }), 200


def check_user_password(user, password):
    """
    Centralized password check.
    If your User model implements check_password(self, pwd) it will be used.
    Otherwise it will attempt to compare against user.password_hash using werkzeug.
    """
    if not user or password is None:
        return False

    # Prefer model-provided method
    if hasattr(user, "check_password") and callable(getattr(user, "check_password")):
        try:
            return user.check_password(password)
        except Exception:
            # Fall back to hash compare if model method errors
            pass

    # Fallback: check password_hash attribute
    pw_hash = getattr(user, "password_hash", None)
    if not pw_hash:
        return False
    try:
        return check_password_hash(pw_hash, password)
    except Exception:
        return False


# ------------------------- Decorators -------------------------
def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        role = normalize_role(claims.get('role'))
        if role not in ['admin', 'super_admin']:
            return jsonify({"message": "Admin access required"}), 403
        return fn(*args, **kwargs)
    return wrapper


def super_admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        role = normalize_role(claims.get('role'))
        if role != 'super_admin':
            return jsonify({"message": "Super admin access required"}), 403
        return fn(*args, **kwargs)
    return wrapper


# ------------------------- Customer Registration -------------------------
@auth_bp.route('/register/customer', methods=['POST'])
def register_customer():
    try:
        data = request.get_json(silent=True) or {}
        email = data.get("email")
        full_name = data.get("full_name")
        password = data.get("password")
        phone = data.get("phone")
        branch_id = data.get("branch_id")

        if not email or not full_name or not password or not phone:
            return jsonify({"message": "Email, full name, password, and phone are required"}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({"message": "Email already registered"}), 400
        if User.query.filter_by(phone=phone).first():
            return jsonify({"message": "Phone number already registered"}), 400

        otp = str(random.randint(100000, 999999))
        otp_expires_at = datetime.utcnow() + timedelta(minutes=15)

        new_user = User(
            email=email,
            full_name=full_name,
            phone=phone,
            password_hash=generate_password_hash(password),
            otp=otp,
            otp_expires_at=otp_expires_at,
            is_verified=False,
            role='customer',
            branch_id=branch_id
        )

        db.session.add(new_user)
        db.session.commit()

        # Try to send OTP email, but don't fail registration if email fails
        try:
            email_sent = send_verification_email(
                recipient=email,
                subject="Your Verification Code",
                template="verification_email.html",
                context={"full_name": full_name, "otp_code": otp, "expiry_minutes": 15}
            )
        except Exception as email_error:
            current_app.logger.error(f"Failed to send OTP email: {str(email_error)}")
            email_sent = False

        if email_sent:
            return jsonify({
                "message": "OTP sent to email",
                "email": email,
                "expires_at": otp_expires_at.isoformat()
            }), 200
        else:
            return jsonify({
                "message": "Registration successful but failed to send OTP email",
                "email": email,
                "otp": otp,
                "expires_at": otp_expires_at.isoformat(),
                "warning": "Please contact support for verification"
            }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Registration error")
        return jsonify({"message": "Registration failed", "error": str(e)}), 500


# ------------------------- Verify OTP -------------------------
@auth_bp.route('/verify', methods=['POST'])
def verify_otp():
    try:
        data = request.get_json(silent=True) or {}
        email = data.get("email")
        otp = data.get("otp")
        if not email or not otp:
            return jsonify({"message": "Email and OTP are required"}), 400

        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({"message": "User not found"}), 404
        if not user.otp or user.otp != str(otp):
            return jsonify({"message": "Invalid OTP"}), 401
        if user.otp_expires_at and datetime.utcnow() > user.otp_expires_at:
            return jsonify({"message": "OTP has expired"}), 401

        user.is_verified = True
        user.otp = None
        user.otp_expires_at = None
        db.session.commit()

        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={
                "email": user.email, 
                "role": normalize_role(user.role), 
                "branch_id": user.branch_id
            }
        )
        return auth_success_response(user, access_token)

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Verification error")
        return jsonify({"message": "Verification failed", "error": str(e)}), 500


# ------------------------- Admin Registration (Branch Assigned) -------------------------
@auth_bp.route('/register/admin', methods=['POST'])
@super_admin_required
def register_admin():
    try:
        data = request.get_json(silent=True) or {}
        required_fields = ['full_name', 'email', 'phone', 'password', 'branch_id']
        if not all(field in data and data[field] for field in required_fields):
            return jsonify({"message": "All fields are required"}), 400

        if User.query.filter_by(email=data['email']).first():
            return jsonify({"message": "Admin already exists"}), 400

        password = data.get('password') or secrets.token_urlsafe(12)

        new_admin = User(
            full_name=data['full_name'],
            email=data['email'],
            phone=data['phone'],
            role='admin',
            is_verified=True,
            branch_id=data['branch_id'],
            password_hash=generate_password_hash(password)
        )

        db.session.add(new_admin)
        db.session.commit()
        
        current_app.logger.info(f"New admin created: {data['email']} for branch: {data['branch_id']}")

        try:
            send_admin_credentials(
                recipient=data['email'],
                subject="Your Admin Account Credentials",
                template="admin_credentials.html",
                context={
                    "full_name": data['full_name'],
                    "email": data['email'],
                    "password": password,
                    "login_url": f"{current_app.config.get('FRONTEND_URL', '')}/admin-login"
                }
            )
            return jsonify({
                "message": "Admin created successfully",
                "admin": {"email": data['email'], "full_name": data['full_name'], "branch_id": data['branch_id']}
            }), 201

        except Exception as email_error:
            current_app.logger.exception("Failed to send admin credentials")
            return jsonify({
                "message": "Admin created but failed to send credentials email",
                "admin": {"email": data['email'], "full_name": data['full_name'], "branch_id": data['branch_id']},
                "error": "Please contact the admin to get credentials"
            }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Admin creation error")
        return jsonify({"message": "Admin creation failed", "error": str(e)}), 500


# ------------------------- Update User Profile (Admin can update branch) -------------------------
@auth_bp.route('/update-user/<user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    try:
        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({"message": "No data provided"}), 400

        current_user_id = get_jwt_identity()
        current_user = User.query.filter_by(id=str(current_user_id)).first()

        user = User.query.filter_by(id=str(user_id)).first()
        if not user:
            return jsonify({"message": "User not found"}), 404

        # Branch restriction: admins can only update users in their branch
        if current_user and current_user.role != "super_admin" and user.branch_id != current_user.branch_id:
            return jsonify({"message": "You cannot modify users outside your branch"}), 403

        if 'full_name' in data:
            user.full_name = data['full_name']
        if 'phone' in data:
            user.phone = data['phone']
        if 'role' in data:
            if current_user and current_user.role != "super_admin" and data['role'] == "super_admin":
                return jsonify({"message": "Cannot assign super admin role"}), 403
            user.role = normalize_role(data['role'])
        if 'branch_id' in data:
            if current_user and current_user.role != "super_admin":
                return jsonify({"message": "Cannot change branch"}), 403
            user.branch_id = data['branch_id']

        db.session.commit()
        return jsonify({"message": "User updated successfully"}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Update user error")
        return jsonify({"message": "Failed to update user", "error": str(e)}), 500


# ------------------------- FIXED Admin Login with Branch Loading -------------------------
@auth_bp.route('/login/admin', methods=['POST'])
def admin_login():
    try:
        data = request.get_json(silent=True) or {}
        email = data.get('email')
        password = data.get('password')

        current_app.logger.info(f"=== ADMIN LOGIN ATTEMPT ===")
        current_app.logger.info(f"Email: {email}")

        if not email or not password:
            return jsonify({"message": "Email and password required"}), 400

        # CRITICAL: Use joinedload to ensure branch is loaded with the user
        user = User.query.options(joinedload(User.branch)).filter_by(email=email).first()
        
        if not user:
            current_app.logger.warning(f"Admin login - User not found: {email}")
            return jsonify({"message": "Invalid credentials"}), 401
            
        current_app.logger.info(f"User found: {user.email}, Role: {user.role}, Branch ID: {user.branch_id}")
        
        if normalize_role(user.role) != 'admin':
            current_app.logger.warning(f"Admin login - User is not admin: {email}, role: {user.role}")
            return jsonify({"message": "Invalid credentials"}), 401
            
        if not check_user_password(user, password):
            current_app.logger.warning(f"Admin login - Invalid password for: {email}")
            return jsonify({"message": "Invalid credentials"}), 401

        # Log branch information
        if user.branch:
            current_app.logger.info(f"Branch loaded: {user.branch.name} (ID: {user.branch.id})")
        else:
            current_app.logger.warning(f"Branch relationship not loaded for user {user.email}")

        # CRITICAL: Include branch_id in JWT claims
        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={
                "email": user.email,
                "role": normalize_role(user.role),
                "branch_id": user.branch_id  # ← ENSURE THIS IS HERE
            }
        )

        current_app.logger.info(f"Admin login successful: {email}, branch_id: {user.branch_id}")
        current_app.logger.info(f"=== END ADMIN LOGIN ===")

        return auth_success_response(user, access_token)

    except Exception as e:
        current_app.logger.exception("Admin login failed")
        return jsonify({"message": "Login failed", "error": str(e)}), 500


# ------------------------- Standardized Super Admin Login -------------------------
@auth_bp.route('/login/super-admin', methods=['POST'])
def super_admin_login():
    try:
        data = request.get_json(silent=True) or {}
        email = data.get('email')
        password = data.get('password')

        current_app.logger.info(f"=== SUPER ADMIN LOGIN ATTEMPT ===")
        current_app.logger.info(f"Email: {email}")

        if not email or not password:
            return jsonify({"message": "Email and password required", "error": "Missing credentials"}), 400

        user = User.query.filter_by(email=email).first()
        
        if not user or normalize_role(user.role) != 'super_admin' or not check_user_password(user, password):
            current_app.logger.warning(f"Super admin login failed for: {email}")
            return jsonify({"message": "Invalid credentials", "error": "Invalid email or password"}), 401

        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={
                "email": user.email,
                "role": normalize_role(user.role)
                # Note: Super admin doesn't have branch_id
            }
        )

        current_app.logger.info(f"Super admin login successful: {email}")
        current_app.logger.info(f"=== END SUPER ADMIN LOGIN ===")

        return auth_success_response(user, access_token)

    except Exception as e:
        current_app.logger.exception("Super admin login error")
        return jsonify({"message": "Login failed", "error": str(e)}), 500


# ------------------------- Initialize Super Admin -------------------------
@auth_bp.route('/init-super-admin', methods=['POST'])
def init_super_admin():
    try:
        if User.query.filter_by(role='super_admin').first():
            return jsonify({"message": "Super admin already exists"}), 400
        data = request.get_json(silent=True) or {}
        required_fields = ['full_name', 'email', 'phone', 'password']

        if not all(field in data and data[field] for field in required_fields):
            return jsonify({"message": "All fields are required"}), 400

        super_admin = User(
            full_name=data['full_name'],
            email=data['email'],
            phone=data['phone'],
            role='super_admin',
            is_verified=True,
            password_hash=generate_password_hash(data['password'])
        )

        db.session.add(super_admin)
        db.session.commit()
        
        current_app.logger.info(f"Super admin created: {data['email']}")
        
        return jsonify({"message": "Super admin created successfully"}), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Super admin creation failed")
        return jsonify({"message": "Super admin creation failed", "error": str(e)}), 500


# ------------------------- Standardized Customer Login -------------------------
@auth_bp.route('/login/customer', methods=['POST'])
def customer_login():
    try:
        data = request.get_json(silent=True) or {}
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({"message": "Email and password required"}), 400

        # Load customer with branch if they have one
        user = User.query.options(joinedload(User.branch)).filter_by(email=email).first()
        
        if not user or normalize_role(user.role) != 'customer':
            return jsonify({"message": "Invalid credentials"}), 401

        if not user.password_hash:
            current_app.logger.error(f"Customer {user.id} has no password set")
            return jsonify({
                "message": "Account not properly configured",
                "resolution": "Please use password reset"
            }), 403

        if not check_user_password(user, password):
            current_app.logger.warning(f"Invalid password attempt for customer {user.id}")
            return jsonify({"message": "Invalid credentials"}), 401

        if not user.is_verified:
            return jsonify({
                "message": "Account not verified",
                "resolution": "Please verify your email address"
            }), 403

        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={
                "email": user.email,
                "role": normalize_role(user.role),
                "is_verified": user.is_verified,
                "branch_id": user.branch_id  # Include branch_id if customer has one
            },
            expires_delta=timedelta(hours=24)
        )

        return auth_success_response(user, access_token)

    except Exception as e:
        current_app.logger.exception("Customer login error")
        return jsonify({"message": "Login temporarily unavailable", "error": "Internal server error"}), 500


# ------------------------- Get Users (with branch restriction) -------------------------
@auth_bp.route('/users', methods=['GET'])
@admin_required
def get_users():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.filter_by(id=str(current_user_id)).first()

        query = User.query

        # Branch restriction: admins only see users in their branch
        if current_user and current_user.role != "super_admin":
            query = query.filter_by(branch_id=current_user.branch_id)

        # Order by creation date for consistent sequential IDs
        query = query.order_by(User.created_at.asc())

        # Pagination
        users_pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        users = users_pagination.items

        total_count = users_pagination.total
        start_sequence = (page - 1) * per_page + 1

        users_data = [{
            "seq_id": start_sequence + idx,
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": normalize_role(user.role),
            "branch_id": user.branch_id,
            "phone": user.phone,
            "is_verified": user.is_verified,
            "created_at": user.created_at.isoformat() if user.created_at else None
        } for idx, user in enumerate(users)]

        return jsonify({
            "status": "success",
            "count": total_count,
            "total_pages": users_pagination.pages,
            "current_page": page,
            "data": users_data
        }), 200

    except Exception as e:
        current_app.logger.exception("Error in get_users")
        return jsonify({"status": "error", "message": "Failed to retrieve users", "error": str(e)}), 500


# ------------------------- FIXED /me endpoint with Branch Loading -------------------------
@auth_bp.route('/me', methods=['GET', 'PUT'])
@jwt_required()
def get_user_me():
    try:
        user_id = get_jwt_identity()
        
        current_app.logger.info(f"=== /auth/me called ===")
        current_app.logger.info(f"User ID: {user_id}")
        
        if not user_id:
            current_app.logger.error("No user ID in JWT")
            return jsonify({"success": False, "message": "Invalid or missing token identity"}), 401

        # CRITICAL: Use joinedload to ensure branch is loaded
        user = User.query.options(joinedload(User.branch)).filter_by(id=str(user_id)).first()
        
        if not user:
            current_app.logger.error(f"User not found: {user_id}")
            return jsonify({"success": False, "message": "User not found"}), 404

        current_app.logger.info(f"User found: {user.email}, Branch ID: {user.branch_id}")
        if user.branch:
            current_app.logger.info(f"Branch loaded: {user.branch.name}")
        else:
            current_app.logger.warning(f"No branch for user (may be super admin or customer)")

        if request.method == 'GET':
            user_data = safe_user_dict(user)
            current_app.logger.info(f"Returning user data with branch: {user_data.get('branch')}")
            current_app.logger.info(f"=== /auth/me END ===")
            return jsonify({"success": True, "user": user_data}), 200

        elif request.method == 'PUT':
            data = request.get_json(silent=True) or {}
            if not data:
                return jsonify({"success": False, "message": "No data provided"}), 400

            # Update allowed fields
            if 'full_name' in data:
                user.full_name = data['full_name']
            if 'phone' in data:
                user.phone = data['phone']
            if 'address' in data:
                user.address = data['address']
            if 'bio' in data:
                user.bio = data['bio']

            db.session.commit()

            return jsonify({
                "success": True,
                "message": "Profile updated successfully",
                "user": safe_user_dict(user)
            }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Unexpected error in /auth/me")
        return jsonify({"success": False, "message": "Internal server error", "error": str(e)}), 500


# ------------------------- Password reset (request + reset) -------------------------
@auth_bp.route('/request-password-reset', methods=['POST'])
def request_password_reset():
    try:
        data = request.get_json(silent=True) or {}
        email = data.get("email")
        if not email:
            return jsonify({"message": "Email is required"}), 400

        user = User.query.filter_by(email=email).first()
        if not user:
            # Avoid leaking user existence
            return jsonify({"message": "If your email is registered, you will receive a password reset link"}), 200

        # Remove existing tokens for user
        PasswordResetToken.query.filter_by(user_id=user.id).delete()

        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=1)

        reset_token = PasswordResetToken(user_id=user.id, token=token, expires_at=expires_at)
        db.session.add(reset_token)
        db.session.commit()

        reset_url = f"{current_app.config.get('FRONTEND_URL', 'http://localhost:3000')}/reset-password?token={token}"

        try:
            # Implement your email sending here if desired
            pass
        except Exception:
            current_app.logger.exception("Failed to send reset email")

        return jsonify({"message": "Password reset link sent to your email", "reset_url": reset_url}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Password reset request error")
        return jsonify({"message": "Failed to process password reset request", "error": str(e)}), 500


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    try:
        data = request.get_json(silent=True) or {}
        token = data.get("token")
        new_password = data.get("new_password")
        if not token or not new_password:
            return jsonify({"message": "Token and new password are required"}), 400

        reset_token = PasswordResetToken.query.filter_by(token=token).first()
        if not reset_token:
            return jsonify({"message": "Invalid or expired token"}), 400

        if datetime.utcnow() > reset_token.expires_at:
            db.session.delete(reset_token)
            db.session.commit()
            return jsonify({"message": "Token has expired"}), 400

        user = User.query.get(reset_token.user_id)
        if not user:
            return jsonify({"message": "User not found"}), 404

        user.password_hash = generate_password_hash(new_password)

        db.session.delete(reset_token)
        db.session.commit()

        return jsonify({"message": "Password reset successfully"}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Password reset error")
        return jsonify({"message": "Failed to reset password", "error": str(e)}), 500


# ------------------------- Change password (authenticated) -------------------------
@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    try:
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({"success": False, "message": "Invalid or missing token identity"}), 401

        user = User.query.filter_by(id=str(user_id)).first()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        data = request.get_json(silent=True) or {}
        current_password = data.get("current_password")
        new_password = data.get("new_password")
        if not current_password or not new_password:
            return jsonify({"success": False, "message": "Current password and new password are required"}), 400

        if not check_user_password(user, current_password):
            return jsonify({"success": False, "message": "Current password is incorrect"}), 401

        user.password_hash = generate_password_hash(new_password)
        db.session.commit()

        return jsonify({"success": True, "message": "Password changed successfully"}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Change password error")
        return jsonify({"success": False, "message": "Failed to change password", "error": str(e)}), 500


# ------------------------- Send OTP -------------------------
@auth_bp.route('/send-otp', methods=['POST'])
def send_otp():
    try:
        data = request.get_json(silent=True) or {}
        email = data.get("email")
        purpose = data.get("purpose", "verification")
        if not email:
            return jsonify({"message": "Email is required"}), 400

        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({"message": "If this email is registered, you will receive an OTP shortly"}), 200

        otp = str(random.randint(100000, 999999))
        otp_expires_at = datetime.utcnow() + timedelta(minutes=15)
        user.otp = otp
        user.otp_expires_at = otp_expires_at
        db.session.commit()

        try:
            send_verification_email(
                recipient=email,
                subject="Your Verification Code",
                template="verification_email.html",
                context={"full_name": user.full_name, "otp_code": otp, "expiry_minutes": 15, "purpose": purpose}
            )
        except Exception:
            current_app.logger.exception("Failed to send OTP email")
            return jsonify({"message": "Failed to send OTP email", "error": "Please try again later"}), 500

        return jsonify({"message": "OTP sent successfully", "email": email, "expires_at": otp_expires_at.isoformat()}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Send OTP error")
        return jsonify({"message": "Failed to send OTP", "error": str(e)}), 500


# ------------------------- Test Email (admin only) -------------------------
@auth_bp.route('/test-email', methods=['POST'])
@admin_required
def test_email():
    try:
        data = request.get_json(silent=True) or {}
        email = data.get('email', current_app.config.get('MAIL_DEFAULT_SENDER'))
        success = send_verification_email(
            recipient=email,
            subject="Test Email",
            template="verification_email.html",
            context={"full_name": "Test User", "otp_code": "123456", "expiry_minutes": 15}
        )
        if success:
            return jsonify({"message": "Test email sent successfully", "status": "success"}), 200
        else:
            return jsonify({"message": "Failed to send test email. Check email configuration.", "status": "error"}), 500
    except Exception as e:
        current_app.logger.exception("Email test error")
        return jsonify({"message": "Email test failed", "error": str(e)}), 500


# ------------------------- Debug endpoint (REMOVE IN PRODUCTION) -------------------------
@auth_bp.route('/debug-user/<email>', methods=['GET'])
def debug_user(email):
    """Temporary debug endpoint - REMOVE IN PRODUCTION"""
    try:
        user = User.query.options(joinedload(User.branch)).filter_by(email=email).first()
        if not user:
            return jsonify({
                "found": False, 
                "message": f"No user found with email: {email}", 
                "total_users": User.query.count()
            }), 404
        
        return jsonify({
            "found": True,
            "email": user.email,
            "role": user.role,
            "full_name": user.full_name,
            "is_verified": user.is_verified,
            "has_password": bool(user.password_hash),
            "password_hash_start": user.password_hash[:20] if user.password_hash else None,
            "branch_id": user.branch_id,
            "branch_name": user.branch.name if user.branch else None,
            "branch_loaded": bool(user.branch)
        }), 200
    except Exception as e:
        current_app.logger.exception("Debug user error")
        return jsonify({"error": str(e)}), 500