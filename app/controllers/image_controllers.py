from flask import Blueprint, jsonify, request, current_app, send_from_directory
from flask_jwt_extended import jwt_required
from app import db
from app.models.image import HomepageImage, SpecialOffer
import os
from app.models.image import Specialty
from werkzeug.utils import secure_filename
from datetime import datetime
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.User import User
import uuid 
from flask import Blueprint, request, jsonify, url_for  # Added url_for import
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
import uuid
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename
from sqlalchemy import text

# Define the blueprint with a URL prefix
homepage_bp = Blueprint('homepage_bp', __name__, url_prefix='/api/v1/homepage_bp')

# Configure allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    """Checks if the file extension is allowed."""
    if not filename:
        return False
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file, subfolder):
    """Helper function to handle file uploads."""
    if file.filename == '':
        current_app.logger.warning("Empty filename provided for upload.")
        return None
    
    filename = secure_filename(file.filename)
    unique_filename = f"{datetime.now().timestamp()}_{filename}"
    
    try:
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder)
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, unique_filename)
        file.save(file_path)
        
        # This is the crucial line: it returns the correct URL path
        return f"/uploads/{subfolder}/{unique_filename}"
    except Exception as e:
        current_app.logger.error(f"Error saving file: {str(e)}")
        return None

def standard_response(data=None, success=True, message=None, status=200):
    """Standardizes all API responses to consistent format."""
    return jsonify({
        'success': success,
        'data': data,
        'message': message or ('Operation successful' if success else 'Operation failed')
    }), status

@homepage_bp.route('/hero-images', methods=['GET'])
def get_hero_images():
    """Returns a list of all active hero images, ordered by display_order."""
    try:
        images = HomepageImage.query.filter_by(active=True).order_by(HomepageImage.display_order).all()
        data = [{
            'id': img.id,
            'image_url': img.image_url,
            'display_order': img.display_order,
        } for img in images]
        return standard_response(data=data)
    except Exception as e:
        current_app.logger.error(f"Error fetching hero images: {str(e)}")
        return standard_response(success=False, message="Failed to fetch hero images", status=500)

@homepage_bp.route('/special-offers', methods=['GET'])
def get_special_offers():
    """Returns a list of active special offers that have not expired."""
    try:
        offers = SpecialOffer.query.filter(
            SpecialOffer.active == True,
            SpecialOffer.valid_until >= datetime.utcnow()
        ).all()
        data = [{
            'id': offer.id,
            'title': offer.title,
            'description': offer.description,
            'image_url': offer.image_url,
            'valid_until': offer.valid_until.isoformat() if offer.valid_until else None,
        } for offer in offers]
        return standard_response(data=data)
    except Exception as e:
        current_app.logger.error(f"Error fetching special offers: {str(e)}")
        return standard_response(success=False, message="Failed to fetch special offers", status=500)

@homepage_bp.route('/admin/hero-images', methods=['POST'])
@jwt_required()
def add_hero_image():
    """Admin route to upload a new hero image."""
    try:
        if 'image' not in request.files:
            return standard_response(success=False, message='No image file provided', status=400)
            
        file = request.files['image']
        if not allowed_file(file.filename):
            return standard_response(success=False, message='Invalid file type. Allowed extensions are jpg, jpeg, png, gif.', status=400)
        image_url = save_uploaded_file(file, 'hero_images')
        if not image_url:
            return standard_response(success=False, message='Server error during file upload', status=500)
            
        new_image = HomepageImage(
            image_url=image_url,
            display_order=request.form.get('display_order', 0),
            active=request.form.get('active', 'true').lower() == 'true'
        )
        db.session.add(new_image)
        db.session.commit()
        
        return standard_response(
            data={
                'id': new_image.id,
                'image_url': image_url,
                'display_order': new_image.display_order
            },
            message='Image uploaded successfully',
            status=201
        )
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding hero image: {str(e)}")
        return standard_response(success=False, message='An unexpected server error occurred', status=500)

@homepage_bp.route('/admin/hero-images/<int:image_id>', methods=['DELETE'])
@jwt_required()
def delete_hero_image(image_id):
    """Admin route to delete a hero image."""
    try:
        image = HomepageImage.query.get_or_404(image_id)
        db.session.delete(image)
        db.session.commit()
        return standard_response(message='Hero image deleted successfully')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting hero image {image_id}: {str(e)}")
        return standard_response(success=False, message='An unexpected server error occurred', status=500)

@homepage_bp.route('/admin/special-offers', methods=['POST', 'OPTIONS'])
@jwt_required()
def create_special_offer():
    if request.method == 'OPTIONS':
        return standard_response()
    try:
        data = request.form
        if 'image' not in request.files:
            return standard_response(success=False, message='No image file provided', status=400)
        file = request.files['image']
        if not allowed_file(file.filename):
            return standard_response(success=False, message='Invalid file type. Allowed extensions are jpg, jpeg, png, gif.', status=400)
        image_url = save_uploaded_file(file, 'special_offers')
        if not image_url:
            return standard_response(success=False, message='Server error during file upload', status=500)
        new_offer = SpecialOffer(
            title=data.get('title'),
            description=data.get('description'),
            image_url=image_url,
            valid_until=datetime.fromisoformat(data.get('valid_until')) if data.get('valid_until') else None
        )
        db.session.add(new_offer)
        db.session.commit()
        return standard_response(
            data={
                'id': new_offer.id,
                'title': new_offer.title,
                'description': new_offer.description,
                'image_url': new_offer.image_url,
                'valid_until': new_offer.valid_until.isoformat() if new_offer.valid_until else None
            },
            message='Special offer created successfully',
            status=201
        )
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating special offer: {str(e)}")
        return standard_response(success=False, message='An unexpected server error occurred', status=500)

@homepage_bp.route('/admin/special-offers/<int:offer_id>', methods=['DELETE'])
@jwt_required()
def delete_special_offer(offer_id):
    """Admin route to delete a special offer."""
    try:
        offer = SpecialOffer.query.get_or_404(offer_id)
        db.session.delete(offer)
        db.session.commit()
        return standard_response(message='Special offer deleted successfully')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting special offer {offer_id}: {str(e)}")
        return standard_response(success=False, message='An unexpected server error occurred', status=500)

@homepage_bp.route('/specialty', methods=['GET'])
def get_specialties():
    try:
        # Verify database connection with proper text() wrapper
        db.session.execute(text('SELECT 1')).fetchone()
        
        specialties = Specialty.query.all()
        
        specialties_data = []
        for specialty in specialties:
            specialty_data = {
                'id': specialty.id,
                'title': specialty.title,
                'description': specialty.description,
                'icon_name': specialty.icon_name,
                'image_url': specialty.image_url,
                'is_active': getattr(specialty, 'is_active', True)  # Ensure is_active is always included
            }
            # Add optional fields if they exist
            if hasattr(specialty, 'created_at') and specialty.created_at:
                specialty_data['created_at'] = specialty.created_at.isoformat()
            
            specialties_data.append(specialty_data)
        return jsonify({
            'status': 'success',
            'data': specialties_data,
            'count': len(specialties_data)
        }), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Database error occurred',
            'error': str(e)
        }), 500
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Unexpected error occurred',
            'error': str(e)
        }), 500

@homepage_bp.route('/admin/specialty', methods=['POST'])
@jwt_required()
def admin_create_specialty():
    try:
        # Verify admin privileges
        current_user = get_jwt_identity()
        user = User.query.get(current_user)
        if not user or user.role not in ['admin', 'super_admin']:
            return jsonify({'error': 'Unauthorized'}), 403
            
        # Handle both form-data and json requests
        if request.content_type.startswith('multipart/form-data'):
            data = {
                'title': request.form.get('title'),
                'description': request.form.get('description'),
                'icon_name': request.form.get('icon_name'),
                'image_url': request.form.get('image_url', '')
            }
            image_file = request.files.get('image')
        else:
            data = request.get_json()
            image_file = None
            
        # Validate required fields
        required_fields = ['title', 'description', 'icon_name']
        if not all(field in data and data[field] for field in required_fields):
            return jsonify({
                'error': f'Missing required fields: {", ".join(required_fields)}'
            }), 400
            
        # Process image upload if present
        image_url = data.get('image_url', '')
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'specialties')
            
            # Create directory if it doesn't exist
            os.makedirs(upload_dir, exist_ok=True)
            
            filepath = os.path.join(upload_dir, unique_filename)
            image_file.save(filepath)
            image_url = url_for('static', filename=f'uploads/specialties/{unique_filename}', _external=True)
            
        new_specialty = Specialty(
            title=data['title'],
            description=data['description'],
            icon_name=data['icon_name'],
            image_url=image_url,
            is_active=True  # Explicitly set is_active to True
        )
        db.session.add(new_specialty)
        db.session.commit()
        
        return jsonify({
            'message': 'Specialty created successfully',
            'data': {
                'id': new_specialty.id,
                'title': new_specialty.title,
                'description': new_specialty.description,
                'icon_name': new_specialty.icon_name,
                'image_url': new_specialty.image_url,
                'is_active': new_specialty.is_active
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating specialty: {str(e)}")
        return jsonify({'error': str(e)}), 500

@homepage_bp.route('/admin/specialty/<int:id>', methods=['PUT'])
@jwt_required()
def admin_update_specialty(id):
    try:
        # Verify admin privileges
        current_user = get_jwt_identity()
        user = User.query.get(current_user)
        if not user or user.role not in ['admin', 'super_admin']:
            return jsonify({'error': 'Unauthorized'}), 403
            
        specialty = Specialty.query.get_or_404(id)
        
        # Handle both form-data and json requests
        if request.content_type.startswith('multipart/form-data'):
            data = {
                'title': request.form.get('title', specialty.title),
                'description': request.form.get('description', specialty.description),
                'icon_name': request.form.get('icon_name', specialty.icon_name),
                'image_url': request.form.get('image_url', specialty.image_url)
            }
            image_file = request.files.get('image')
        else:
            data = request.get_json()
            image_file = None
            
        # Process image upload if present
        image_url = data.get('image_url', specialty.image_url)
        if image_file and allowed_file(image_file.filename):
            # Delete old image if it exists
            if specialty.image_url and 'uploads/specialties' in specialty.image_url:
                try:
                    old_filename = specialty.image_url.split('/')[-1]
                    old_path = os.path.join(
                        current_app.config['UPLOAD_FOLDER'], 
                        'specialties', 
                        old_filename
                    )
                    if os.path.exists(old_path):
                        os.remove(old_path)
                except Exception as e:
                    current_app.logger.error(f"Error deleting old image: {str(e)}")
                    
            # Save new image
            filename = secure_filename(image_file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'specialties')
            os.makedirs(upload_dir, exist_ok=True)
            filepath = os.path.join(upload_dir, unique_filename)
            image_file.save(filepath)
            image_url = url_for('static', filename=f'uploads/specialties/{unique_filename}', _external=True)
            
        # Update fields
        specialty.title = data.get('title', specialty.title)
        specialty.description = data.get('description', specialty.description)
        specialty.icon_name = data.get('icon_name', specialty.icon_name)
        specialty.image_url = image_url
        db.session.commit()
        
        return jsonify({
            'message': 'Specialty updated successfully',
            'data': {
                'id': specialty.id,
                'title': specialty.title,
                'description': specialty.description,
                'icon_name': specialty.icon_name,
                'image_url': specialty.image_url,
                'is_active': getattr(specialty, 'is_active', True)
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating specialty: {str(e)}")
        return jsonify({'error': str(e)}), 500

@homepage_bp.route('/admin/specialty/<int:id>', methods=['PATCH'])
@jwt_required()
def patch_specialty(id):
    """Partial update for specialty, used for toggling is_active status"""
    try:
        # Verify admin privileges
        current_user = get_jwt_identity()
        user = User.query.get(current_user)
        if not user or user.role not in ['admin', 'super_admin']:
            return jsonify({'error': 'Unauthorized'}), 403
            
        specialty = Specialty.query.get_or_404(id)
        data = request.get_json()
        
        # Update is_active if provided
        if 'is_active' in data:
            specialty.is_active = data['is_active']
            
        db.session.commit()
        
        return jsonify({
            'message': 'Specialty updated successfully',
            'data': {
                'id': specialty.id,
                'title': specialty.title,
                'description': specialty.description,
                'icon_name': specialty.icon_name,
                'image_url': specialty.image_url,
                'is_active': specialty.is_active
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error patching specialty: {str(e)}")
        return jsonify({'error': str(e)}), 500

@homepage_bp.route('/admin/specialty/<int:specialty_id>', methods=['DELETE'])
@jwt_required()
def delete_specialty(specialty_id):
    try:
        # Verify admin privileges
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or user.role not in ['admin', 'super_admin']:
            return jsonify({
                'status': 'error',
                'message': 'Admin access required'
            }), 403
            
        specialty = Specialty.query.get_or_404(specialty_id)
        
        db.session.delete(specialty)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Specialty deleted successfully',
            'data': {
                'id': specialty_id
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Failed to delete specialty',
            'error': str(e)
        }), 500