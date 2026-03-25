# File: app/controllers/footer_controller.py

from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models.ContactInfo import ContactInfo
from app.models.OpeningHours import OpeningHours
from app.utils.validation import validate_email
from datetime import datetime
import logging

footer_bp = Blueprint('footer', __name__, url_prefix='/api/v1/footer')

# Get footer contact information
@footer_bp.route('/contact-info', methods=['GET'])
def get_contact_info():
    try:
        contact_info = ContactInfo.query.first()
        
        if not contact_info:
            # Return default contact information if none exists in database
            contact_info = {
                'phone': '(+256)772 688833',
                'email': 'info@tastebudz.com',
                'address': 'C&C Building Old Kira Road Bukoto, Opposite UMC Hospital',
                'facebook_url': 'https://www.facebook.com/tastebudz',
                'instagram_url': 'https://www.instagram.com/tastebudz'
            }
        else:
            contact_info = {
                'phone': contact_info.phone,
                'email': contact_info.email,
                'address': contact_info.address,
                'facebook_url': contact_info.facebook_url,
                'instagram_url': contact_info.instagram_url
                
            }
        
        return jsonify({
            'success': True,
            'data': contact_info
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching contact info: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch contact information',
            'error': str(e)
        }), 500

# Get opening hours
@footer_bp.route('/opening-hours', methods=['GET'])
def get_opening_hours():
    try:
        opening_hours = OpeningHours.query.order_by(OpeningHours.day_of_week).all()
        
        if not opening_hours:
            # Return default opening hours if none exists in database
            opening_hours = [
                {'day': 'Monday - Friday', 'hours': '8am - 10pm'},
                {'day': 'Saturday', 'hours': '8am - 11pm'},
                {'day': 'Sunday', 'hours': '8am - 11pm'}
            ]
        else:
            opening_hours = [
                {
                    'day': hour.get_display_day(),
                    'hours': f"{hour.open_time} - {hour.close_time}"
                }
                for hour in opening_hours
            ]
        
        return jsonify({
            'success': True,
            'data': opening_hours
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching opening hours: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch opening hours',
            'error': str(e)
        }), 500


# Get quick links (static data)
@footer_bp.route('/quick-links', methods=['GET'])
def get_quick_links():
    try:
        # This could be made dynamic by storing in database
        quick_links = [
            {'title': 'Our Menu', 'url': '/menu'},
            {'title': 'Book a Table', 'url': '/reservations'},
            {'title': 'About Us', 'url': '/about'}
            
        ]
        
        return jsonify({
            'success': True,
            'data': quick_links
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching quick links: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch quick links',
            'error': str(e)
        }), 500

# Update contact information (Admin only)
@footer_bp.route('/contact-info/update', methods=['PUT'])
def update_contact_info():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        contact_info = ContactInfo.query.first()
        
        if not contact_info:
            # Create new contact info if it doesn't exist
            contact_info = ContactInfo()
            db.session.add(contact_info)
        
        # Update fields
        if 'phone' in data:
            contact_info.phone = data['phone']
        if 'email' in data:
            contact_info.email = data['email']
        if 'address' in data:
            contact_info.address = data['address']
        if 'facebook_url' in data:
            contact_info.facebook_url = data['facebook_url']
        if 'instagram_url' in data:
            contact_info.instagram_url = data['instagram_url']

        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Contact information updated successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating contact info: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to update contact information',
            'error': str(e)
        }), 500

# Update opening hours (Admin only)
@footer_bp.route('/opening-hours/update', methods=['PUT'])
def update_opening_hours():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        # Clear existing opening hours
        OpeningHours.query.delete()
        
        # Add new opening hours
        for day_data in data:
            opening_hour = OpeningHours(
                day_of_week=day_data.get('day_of_week'),
                open_time=day_data.get('open_time'),
                close_time=day_data.get('close_time'),
                is_closed=day_data.get('is_closed', False)
            )
            db.session.add(opening_hour)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Opening hours updated successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating opening hours: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to update opening hours',
            'error': str(e)
        }), 500