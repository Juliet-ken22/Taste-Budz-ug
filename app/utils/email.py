from flask import current_app, render_template
import smtplib
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import re

logger = logging.getLogger(__name__)

def send_email_direct_smtp(recipient, subject, html_content):
    """Send email directly using SMTP with enhanced error reporting"""
    try:
        # Get SMTP configuration from Flask app
        smtp_server = current_app.config.get('MAIL_SERVER', 'mail.tastebz.com')
        smtp_port = current_app.config.get('MAIL_PORT', 587)
        username = current_app.config.get('MAIL_USERNAME', 'info@tastebz.com')
        password = current_app.config.get('MAIL_PASSWORD', 'UzDi?rYMZM]B-L7}')
        use_tls = current_app.config.get('MAIL_USE_TLS', True)
        use_ssl = current_app.config.get('MAIL_USE_SSL', False)
        sender_email = current_app.config.get('MAIL_DEFAULT_SENDER', 'info@tastebz.com')
        
        # Validate configuration
        if not all([username, password]):
            logger.error("Email credentials not configured")
            return False
        
        logger.info(f"Attempting to send email to {recipient} via {smtp_server}:{smtp_port}")
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = recipient
        
        # Add both HTML and plain text versions
        text_content = strip_tags(html_content)
        msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))

        # Connect to SMTP server
        try:
            if use_ssl:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30)
            else:
                server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
                if use_tls:
                    server.starttls()
            
            logger.debug(f"Connected to SMTP server: {smtp_server}:{smtp_port}")
            
            # Login
            server.login(username, password)
            logger.debug("SMTP authentication successful")
            
            # Send email - use sendmail instead of send_message for better compatibility
            server.sendmail(sender_email, recipient, msg.as_string())
            logger.info(f"Email successfully sent to {recipient}")
            
            server.quit()
            return True
            
        except smtplib.SMTPAuthenticationError as auth_error:
            logger.error(f"SMTP Authentication failed: {str(auth_error)}")
            return False
        except smtplib.SMTPException as smtp_error:
            logger.error(f"SMTP error: {str(smtp_error)}")
            return False
        except socket.timeout:
            logger.error("SMTP connection timed out")
            return False
        except Exception as conn_error:
            logger.error(f"Connection error: {str(conn_error)}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to send email to {recipient}: {str(e)}", exc_info=True)
        return False

def strip_tags(html_content):
    """Simple HTML to text conversion"""
    clean = re.compile('<.*?>')
    text = re.sub(clean, '', html_content)
    # Clean up extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def render_email_template(template_name, context):
    """Render email template using Flask's built-in template system"""
    try:
        # Try to render using Flask's template system
        template_path = f'emails/{template_name}'
        return render_template(template_path, **context)
    except Exception as e:
        logger.warning(f"Template {template_name} not found, using fallback: {str(e)}")
        # Fallback templates
        return get_fallback_template(template_name, context)

def get_fallback_template(template_name, context):
    """Provide fallback email templates"""
    if 'verification_email' in template_name:
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Email Verification</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: #f9f9f9; padding: 20px; border-radius: 5px; }}
                .header {{ background: #2563eb; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ padding: 20px; background: white; }}
                .otp-code {{ font-size: 32px; font-weight: bold; color: #2563eb; text-align: center; margin: 20px 0; padding: 10px; background: #f3f4f6; border-radius: 5px; }}
                .footer {{ padding: 20px; text-align: center; color: #6b7280; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to TasteBZ!</h1>
                </div>
                <div class="content">
                    <p>Hello {context.get('full_name', 'User')},</p>
                    <p>Thank you for registering with TasteBZ. Please use the following verification code to complete your registration:</p>
                    <div class="otp-code">{context.get('otp_code', 'N/A')}</div>
                    <p>This code will expire in {context.get('expiry_minutes', 15)} minutes.</p>
                    <p>If you didn't request this verification, please ignore this email.</p>
                </div>
                <div class="footer">
                    <p>Best regards,<br>TasteBZ Team</p>
                </div>
            </div>
        </body>
        </html>
        """
    elif 'admin_credentials' in template_name:
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Admin Account Credentials</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: #f9f9f9; padding: 20px; border-radius: 5px; }}
                .header {{ background: #059669; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ padding: 20px; background: white; }}
                .credentials {{ background: #f3f4f6; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                .footer {{ padding: 20px; text-align: center; color: #6b7280; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Admin Account Created</h1>
                </div>
                <div class="content">
                    <p>Hello {context.get('full_name', 'Admin')},</p>
                    <p>Your admin account has been created successfully. Here are your login credentials:</p>
                    
                    <div class="credentials">
                        <p><strong>Login Details:</strong></p>
                        <p><strong>Email:</strong> {context.get('email', 'N/A')}</p>
                        <p><strong>Password:</strong> {context.get('password', 'N/A')}</p>
                    </div>
                    
                    <p><strong>Important Security Notice:</strong></p>
                    <ul>
                        <li>Please change your password immediately after first login</li>
                        <li>Keep your credentials secure and do not share them</li>
                        <li>If you suspect any unauthorized access, contact the super admin immediately</li>
                    </ul>
                </div>
                <div class="footer">
                    <p>Best regards,<br>TasteBZ Team</p>
                </div>
            </div>
        </body>
        </html>
        """
    else:
        return f"""
        <html>
            <body>
                <p>{context}</p>
            </body>
        </html>
        """

def send_verification_email(recipient, subject, template, context):
    """Send verification email using direct SMTP"""
    try:
        html_content = render_email_template(template, context)
        success = send_email_direct_smtp(recipient, subject, html_content)
        
        if success:
            logger.info(f"✓ Verification email sent to {recipient}")
            return True
        else:
            logger.error(f"✗ Failed to send verification email to {recipient}")
            return False
            
    except Exception as e:
        logger.error(f"✗ Error in send_verification_email: {str(e)}")
        return False

def send_admin_credentials(recipient, subject, template, context):
    """Send admin credentials email using direct SMTP"""
    try:
        html_content = render_email_template(template, context)
        success = send_email_direct_smtp(recipient, subject, html_content)
        
        if success:
            logger.info(f"✓ Admin credentials email sent to {recipient}")
            return True
        else:
            logger.error(f"✗ Failed to send admin credentials to {recipient}")
            return False
            
    except Exception as e:
        logger.error(f"✗ Error in send_admin_credentials: {str(e)}")
        return False