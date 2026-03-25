# File: app/controllers/about_controller.py

from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models.AboutUs import AboutUs
from flask_jwt_extended import jwt_required, get_jwt
import logging
from functools import wraps

about_bp = Blueprint('about', __name__, url_prefix='/api/v1/about')

def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if claims.get('role') not in ['admin', 'super_admin']:
            return jsonify({"message": "Admin access required"}), 403
        return fn(*args, **kwargs)
    return wrapper

# Get about us content
@about_bp.route('/content', methods=['GET'])
def get_about_content():
    try:
        about_content = AboutUs.query.first()
        
        if not about_content:
            # Return default content if none exists
            default_content = {
                'title': 'About Us',
                'paragraphs': [
                    'Welcome to Taste Budz, Kampala\'s favorite destination for delicious food and unforgettable experiences. '
                    'Since opening our doors in 2007, we\'ve been serving the heart of Uganda with passion, flavor, and a warm smile.',
                    
                    'With four branches across Kampala, Taste Budz is more than just a restaurant — we\'re a vibrant hub for '
                    'families, friends, and businesses. Whether you\'re stopping by for a quick bite, celebrating a birthday, '
                    'hosting a meeting, or planning a graduation party, we have the perfect space and service to make every moment special.',
                    
                    'From mouthwatering pizzas to full-service catering, birthday party spaces, conference rooms, '
                    'graduation parties, and more — Taste Budz is where good food meets great memories.'
                ],
                'slogan': 'Come hungry, leave happy.',
                'main_slogan': 'Taste Budz – Where every bite tells a story.',
                'features': [
                    {'icon': '🍕', 'title': 'Delicious Food'},
                    {'icon': '🎉', 'title': 'Event Spaces'},
                    {'icon': '🍽️', 'title': 'Catering'},
                    {'icon': '❤️', 'title': 'Great Service'}
                ],
                'founded_year': 2007,
                'branch_count': 4,
                'highlights': ['catering', 'birthday party spaces', 'conference rooms', 'graduation parties']
            }
            return jsonify({
                'success': True,
                'data': default_content
            }), 200
        
        return jsonify({
            'success': True,
            'data': about_content.to_dict()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching about content: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch about content',
            'error': str(e)
        }), 500

# Update about us content (Admin only)
@about_bp.route('/content/update', methods=['PUT'])
@admin_required
def update_about_content():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        about_content = AboutUs.query.first()
        
        if not about_content:
            # Create new about content if it doesn't exist
            about_content = AboutUs()
            db.session.add(about_content)
        
        # Update fields
        if 'title' in data:
            about_content.title = data['title']
        if 'paragraphs' in data:
            about_content.paragraphs = data['paragraphs']
        if 'slogan' in data:
            about_content.slogan = data['slogan']
        if 'main_slogan' in data:
            about_content.main_slogan = data['main_slogan']
        if 'features' in data:
            about_content.features = data['features']
        if 'founded_year' in data:
            about_content.founded_year = data['founded_year']
        if 'branch_count' in data:
            about_content.branch_count = data['branch_count']
        if 'highlights' in data:
            about_content.highlights = data['highlights']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'About content updated successfully',
            'data': about_content.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating about content: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to update about content',
            'error': str(e)
        }), 500

# Get about us statistics (for admin dashboard)
@about_bp.route('/stats', methods=['GET'])
@admin_required
def get_about_stats():
    try:
        about_content = AboutUs.query.first()
        
        stats = {
            'founded_year': about_content.founded_year if about_content else 2007,
            'branch_count': about_content.branch_count if about_content else 4,
            'feature_count': len(about_content.features) if about_content else 4,
            'paragraph_count': len(about_content.paragraphs) if about_content else 3,
            'highlight_count': len(about_content.highlights) if about_content else 4
        }
        
        return jsonify({
            'success': True,
            'data': stats
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching about stats: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch about statistics',
            'error': str(e)
        }), 500

# Reset about content to default (Admin only)
@about_bp.route('/content/reset', methods=['POST'])
@admin_required
def reset_about_content():
    try:
        # Delete existing content
        AboutUs.query.delete()
        
        # Create default content
        default_content = AboutUs(
            title='About Us',
            paragraphs=[
                'Welcome to Taste Budz, Kampala\'s favorite destination for delicious food and unforgettable experiences. '
                'Since opening our doors in 2007, we\'ve been serving the heart of Uganda with passion, flavor, and a warm smile.',
                
                'With four branches across Kampala, Taste Budz is more than just a restaurant — we\'re a vibrant hub for '
                'families, friends, and businesses. Whether you\'re stopping by for a quick bite, celebrating a birthday, '
                'hosting a meeting, or planning a graduation party, we have the perfect space and service to make every moment special.',
                
                'From mouthwatering pizzas to full-service catering, birthday party spaces, conference rooms, '
                'graduation parties, and more — Taste Budz is where good food meets great memories.'
            ],
            slogan='Come hungry, leave happy.',
            main_slogan='Taste Budz – Where every bite tells a story.',
            features=[
                {'icon': '🍕', 'title': 'Delicious Food'},
                {'icon': '🎉', 'title': 'Event Spaces'},
                {'icon': '🍽️', 'title': 'Catering'},
                {'icon': '❤️', 'title': 'Great Service'}
            ],
            founded_year=2007,
            branch_count=4,
            highlights=['catering', 'birthday party spaces', 'conference rooms', 'graduation parties']
        )
        
        db.session.add(default_content)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'About content reset to default successfully',
            'data': default_content.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error resetting about content: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to reset about content',
            'error': str(e)
        }), 500