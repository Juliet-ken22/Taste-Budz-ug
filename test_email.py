# test_email.py
import os
import sys
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Initialize Flask app
from app import create_app

app = create_app()

def test_email():
    with app.app_context():
        # Check if email config is loaded properly
        print("=== Email Configuration ===")
        print(f"MAIL_SERVER: {app.config.get('MAIL_SERVER')}")
        print(f"MAIL_PORT: {app.config.get('MAIL_PORT')}")
        print(f"MAIL_USERNAME: {app.config.get('MAIL_USERNAME')}")
        print(f"MAIL_DEFAULT_SENDER: {app.config.get('MAIL_DEFAULT_SENDER')}")
        print(f"MAIL_USE_TLS: {app.config.get('MAIL_USE_TLS')}")
        print(f"MAIL_USE_SSL: {app.config.get('MAIL_USE_SSL')}")
        
        # Test Flask-Mail integration
        from flask_mail import Mail
        mail = Mail(app)
        print(f"Mail extension initialized: {mail is not None}")
        
        # Test email sending using Flask-Mail
        from app.utils.email import send_verification_email
        
        test_email = "your_test_email@gmail.com"  # Replace with your actual email
        
        success = send_verification_email(
            recipient=test_email,
            subject="Test OTP - Email Configuration Test",
            template="verification_email.html",
            context={
                "full_name": "Test User",
                "otp_code": "123456",
                "expiry_minutes": 15,
                "purpose": "testing email configuration"
            }
        )
        
        if success:
            print("✅ Email sent successfully! Check your inbox (and spam folder).")
        else:
            print("❌ Failed to send email. Check your configuration and logs.")
        
        return success

if __name__ == "__main__":
    test_email()