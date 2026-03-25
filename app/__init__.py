from flask import Flask, jsonify, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_cors import CORS
from config import Config
from flask_migrate import Migrate
import os
from dotenv import load_dotenv
from datetime import timedelta, datetime
from flask import Response
import time
import json
from flask_jwt_extended import JWTManager, jwt_required, verify_jwt_in_request, get_jwt_identity


db = SQLAlchemy()
jwt = JWTManager()
mail = Mail()
migrate = Migrate()

def create_app(config_class=Config):
    load_dotenv()
    
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Disable strict slashes to prevent redirects
    app.url_map.strict_slashes = False
    
    # Comprehensive CORS configuration to allow all custom headers
    CORS(app, resources={
    r"/api/*": {
        "origins": ["https://tastebz.com/", "http://localhost:3000"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        "allow_headers": [
            "Content-Type", 
            "Authorization", 
            "x-branch-id", 
            "X-Requested-With",
            "X-Request-ID",
            "X-Client-Version",
            "X-Request-Timestamp",
            "X-Client-Platform",
            "Accept",
            "Origin",
            "Access-Control-Allow-Origin",
            "Access-Control-Allow-Headers",
            "Access-Control-Allow-Methods"
        ],
        "supports_credentials": True,
        "max_age": 86400,
        "expose_headers": [
            "Content-Type",
            "Authorization",
            "X-Request-ID", 
            "X-Client-Version",
            "Access-Control-Allow-Origin",
            "Access-Control-Allow-Credentials"
        ]
    }
    })
    
    # JWT Configuration
    app.config['JWT_SECRET_KEY'] = config_class.JWT_SECRET_KEY
    app.config['JWT_TOKEN_LOCATION'] = ['headers', 'cookies']
    app.config['JWT_HEADER_NAME'] = 'Authorization'
    app.config['JWT_HEADER_TYPE'] = 'Bearer'
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = config_class.JWT_ACCESS_TOKEN_EXPIRES
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = getattr(
        config_class, 
        'JWT_REFRESH_TOKEN_EXPIRES', 
        timedelta(days=30))
    app.config['JWT_COOKIE_SECURE'] = config_class.JWT_COOKIE_SECURE
    app.config['JWT_COOKIE_SAMESITE'] = 'Lax' if app.debug else 'None'
    app.config['JWT_COOKIE_CSRF_PROTECT'] = False
    app.config['JWT_SESSION_COOKIE'] = False
    
    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    
    # CLI commands
    from Scripts.populate_categories import populate_categories_command
    app.cli.add_command(populate_categories_command)
    
    # Create upload folders
    upload_folders = [
        app.config['UPLOAD_FOLDER'],
        os.path.join(app.config['UPLOAD_FOLDER'], 'hero_images'),
        os.path.join(app.config['UPLOAD_FOLDER'], 'special_offers'),
        os.path.join(app.config['UPLOAD_FOLDER'], 'menu_items'),
        os.path.join(app.config['UPLOAD_FOLDER'], 'user_avatars'),
        os.path.join(app.config['UPLOAD_FOLDER'], 'logos')
    ]
    for folder in upload_folders:
        os.makedirs(folder, exist_ok=True)
    
    # Import models
    from app.models.User import User
    from app.models.MenuItem_Toppings import MenuItem, Topping, Category
    from app.models.Order import Order, OrderItem
    from app.models.Reservation import Reservation
    from app.models.Feedback import Feedback
    from app.models.Branch import Branch
    from app.models.CartItem import CartItem
    from app.models.Payment import Payment
    from app.models.ContactMessage import ContactMessage
    from app.models.notification import Notification
    from app.models.PaymentAccount import PaymentAccount
    from app.models.PasswordReset import PasswordResetToken
    from app.models.image import HomepageImage, SpecialOffer, Specialty
    from app.models.analytics import SalesAnalytics, CustomerMetrics, ProductPerformance, ActivityLog
    from app.models.settings import SystemConfig, BusinessHours, MaintenanceMode
    from app.models.ContactInfo import ContactInfo
    from app.models.OpeningHours import OpeningHours
    from app.models.AboutUs import AboutUs
    
    # Register blueprints
    from app.controllers.auth_controllers import auth_bp
    from app.controllers.order_controller import order_bp
    from app.controllers.menu_controllers import menu_bp
    from app.controllers.reservation_controllers import reservation_bp
    from app.controllers.cart_controller import cart_bp
    from app.controllers.branch_controllers import branch_bp
    from app.controllers.feedback_controllers import feedback_bp
    from app.controllers.payment_controllers import payment_bp
    from app.controllers.contact_controllers import contact_bp
    from app.controllers.notification_controllers import notification_bp
    from app.controllers.image_controllers import homepage_bp
    from app.controllers.analytic_controllers import analytics_bp
    from app.controllers.setting_controllers import settings_bp
    from app.controllers.activities_controllers import activities_bp
    from app.controllers.footer_controller import footer_bp
    from app.controllers.about_controller import about_bp
    
    # Register blueprints without trailing slashes
    blueprints = [
        (auth_bp, '/api/v1/auth'),
        (order_bp, '/api/v1/orders'),
        (menu_bp, '/api/v1/menu_bp'),
        (reservation_bp, '/api/v1/reservation_bp'),
        (cart_bp, '/api/v1/cart_bp'),
        (branch_bp, '/api/v1'),
        (feedback_bp, '/api/v1/feedback_bp'),
        (payment_bp, '/api/v1/payment_bp'),
        (contact_bp, '/api/v1'),
        (notification_bp, '/api/v1/notifications'),
        (homepage_bp, '/api/v1/homepage_bp'),
        (analytics_bp, '/api/v1/analytics'),
        (activities_bp, '/api/v1/activities'),
        (settings_bp, '/api/v1/settings_bp'),
        (footer_bp, '/api/v1/footer'),
        (about_bp, '/api/v1/about')
    ]
    
    for bp, url_prefix in blueprints:
        app.register_blueprint(bp, url_prefix=url_prefix)
    
    # JWT error handlers
    @jwt.unauthorized_loader
    def handle_unauthorized_error(reason):
        response = jsonify({
            "status": "error",
            "message": f"Authorization required: {reason}"
        })
        return response, 401
    
    @jwt.invalid_token_loader
    def handle_invalid_token_error(reason):
        response = jsonify({
            "status": "error",
            "message": f"Invalid token: {reason}"
        })
        return response, 422
    
    @jwt.expired_token_loader
    def handle_expired_token_error(jwt_header, jwt_payload):
        response = jsonify({
            "status": "error",
            "message": "Token has expired",
            "is_expired": True
        })
        return response, 401
    
    # Simplified after_request - no manual CORS headers
    @app.after_request
    def after_request(response):
        return response
    
    # Routes
    @app.route('/')
    def landing_page():
        current_year = datetime.now().year
        logo_url = '/uploads/logos/tastebudz_logo.png'
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TasteBudz Restaurant - Welcome</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🍽️</text></svg>">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #d32f2f 0%, #b71c1c 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            color: #fff;
            padding: 20px;
        }}
        
        .container {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 50px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
            text-align: center;
            max-width: 700px;
            width: 100%;
            backdrop-filter: blur(10px);
            color: #333;
        }}
        
        .logo {{
            width: 200px;
            height: 200px;
            margin: 0 auto 20px auto;
            display: block;
        }}
        
        h1 {{
            color: #d32f2f;
            margin-bottom: 20px;
            font-size: 2.8rem;
            font-weight: 700;
        }}
        
        .welcome-text {{
            font-size: 1.2rem;
            line-height: 1.8;
            margin-bottom: 30px;
            color: #666;
        }}
        
        .footer {{
            margin-top: 40px;
            color: #999;
            font-size: 0.9rem;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 30px;
            }}
            
            h1 {{
                font-size: 2.2rem;
            }}
            
            .logo {{
                width: 150px;
                height: 150px;
            }}
        }}
        
        @media (max-width: 480px) {{
            .container {{
                padding: 20px;
            }}
            
            h1 {{
                font-size: 1.8rem;
            }}
            
            .welcome-text {{
                font-size: 1rem;
            }}
            
            .logo {{
                width: 120px;
                height: 120px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <img src="{logo_url}" alt="TasteBudz Logo" class="logo" onerror="this.style.display='none'; this.parentNode.querySelector('.fallback-logo').style.display='block';">
        <div class="fallback-logo" style="display: none; font-size: 4rem; font-weight: bold; color: #d32f2f; margin-bottom: 20px; text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.1);">🍽️ TasteBudz</div>
        
        <h1>Welcome to TasteBudz Restaurant API</h1>
        
        <div class="welcome-text">
            Experience the finest culinary delights powered by our robust restaurant management system. 
            From online ordering to reservations, we've got your dining experience covered.
        </div>
        
        <div class="footer">
            © {current_year} TasteBudz Restaurant. All rights reserved.
        </div>
    </div>
</body>
</html>
        """
        return html, 200, {'Content-Type': 'text/html'}
    
    @app.route('/api')
    def api_info():
        return jsonify({
            "message": "Welcome to the TasteBudz Restaurant API",
            "status": "running",
            "version": "1.0.0",
            "environment": app.config['ENV'],
            "endpoints": {
                "health": "/api/v1/healthcheck",
                "auth": "/api/v1/auth",
                "menu": "/api/v1/menu_bp",
                "orders": "/api/v1/orders",
                "reservations": "/api/v1/reservation_bp"
            }
        }), 200
    
    @app.route('/api/v1/healthcheck')
    def healthcheck():
        try:
            db.session.execute('SELECT 1')
            db_status = "connected"
        except Exception as e:
            db_status = f"disconnected: {str(e)}"
        
        return jsonify({
            "status": "healthy",
            "database": db_status,
            "timestamp": datetime.now().isoformat(),
            "environment": app.config['ENV']
        }), 200
    
    @app.route('/api/v1/test-cors', methods=['GET', 'POST', 'OPTIONS'])
    def test_cors():
        return jsonify({
            "status": "success",
            "message": "CORS is properly configured",
            "request_origin": request.headers.get('Origin', 'Not provided'),
            "request_method": request.method,
            "cors_headers": dict(request.headers)
        }), 200
    
    # Endpoint for unseen orders count
    @app.route('/api/v1/orders/new_count', methods=['GET'])
    @jwt_required()
    def get_new_orders_count():
        count = Order.query.filter_by(seen=False).count()
        return jsonify({"new_orders": count}), 200

    # Endpoint for unseen reservations count
    @app.route('/api/v1/reservations/new_count', methods=['GET'])
    @jwt_required()
    def get_new_reservations_count():
        count = Reservation.query.filter_by(seen=False).count()
        return jsonify({"new_reservations": count}), 200

    
    @app.route('/uploads/<path:filename>')
    def serve_uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    
    @app.route('/uploads/<path:subpath>/<filename>')
    def serve_subfolder_image(subpath, filename):
        folder_path = os.path.join(app.config['UPLOAD_FOLDER'], subpath)
        return send_from_directory(folder_path, filename)
    
    

   

    @app.route('/api/v1/events')
    def sse_events():
        token = request.args.get('token', None)
        if not token:
            return jsonify({"error": "Missing token"}), 401

        # Verify JWT manually
        try:
            verify_jwt_in_request(optional=False, token=token)
        except Exception as e:
            return jsonify({"error": f"Invalid token: {str(e)}"}), 401

        def event_stream():
            while True:
                new_order = Order.query.filter_by(seen=False).order_by(Order.id.desc()).first()
                new_reservation = Reservation.query.filter_by(seen=False).order_by(Reservation.id.desc()).first()

                if new_order:
                    data = {"type": "order", "id": new_order.id}
                    yield f"data: {json.dumps(data)}\n\n"
                    new_order.seen = True
                    db.session.commit()

                if new_reservation:
                    data = {"type": "reservation", "id": new_reservation.id}
                    yield f"data: {json.dumps(data)}\n\n"
                    new_reservation.seen = True
                    db.session.commit()

                time.sleep(2)

        return Response(event_stream(), mimetype='text/event-stream')



    @app.route('/favicon.ico')
    def favicon():
        return '', 204
    
    return app

def get_app(config_class=Config):
    app = create_app(config_class)
    return app