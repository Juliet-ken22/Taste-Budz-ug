from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt
from flask import jsonify, request

def token_required(roles=None):
    """
    Decorator to ensure a valid JWT is present in the request and the user
    has the required role.

    Args:
        roles (list): A list of roles (e.g., ['admin', 'super_admin']) that
                      are allowed to access the endpoint.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Allow OPTIONS preflight requests to pass through without authentication.
            # The Flask-CORS extension will handle these requests.
            if request.method == 'OPTIONS':
                return f(*args, **kwargs)

            try:
                # Verify the JWT is valid
                verify_jwt_in_request()
                
                # Get the claims from the verified token
                claims = get_jwt()
                
                # Check if the user has the required role
                if roles and claims.get('role') not in roles:
                    return jsonify({
                        "message": "Insufficient permissions",
                        "error": "Forbidden"
                    }), 403
            except Exception as e:
                # Handle JWT verification errors
                return jsonify({"message": "Token is invalid or missing", "error": str(e)}), 401
                
            # Call the original function if all checks pass
            return f(*args, **kwargs)
            
        return decorated_function
    return decorator
