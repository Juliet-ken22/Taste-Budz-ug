from functools import wraps
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt
from app import db
from app.models.MenuItem_Toppings import MenuItem, Topping, Category
import os
import uuid
from werkzeug.utils import secure_filename

menu_bp = Blueprint('menu_bp', __name__, url_prefix='/menu_bp')

# ==================== Helper Functions =======================
def admin_required(fn):
    """Decorator to check for admin or super_admin roles in the JWT."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if not isinstance(claims, dict) or claims.get('role') not in ['admin', 'super_admin']:
            return jsonify({
                'success': False,
                'message': "Unauthorized: Admin access required"
            }), 403
        return fn(*args, **kwargs)
    return wrapper

def standard_response(data=None, success=True, message="", status_code=200):
    """Standardized API response format"""
    return jsonify({
        'success': success,
        'message': message,
        'data': data if data is not None else []
    }), status_code

def to_dict_menu_item(item):
    return {
        "id": item.id,
        "name": item.name,
        "description": item.description,
        "price": float(item.price) if item.price else 0.0,
        "category": item.category,
        "size": item.size,
        "image_url": item.image_url,
        "is_available": item.is_available
    }

def to_dict_topping(topping):
    return {
        "id": topping.id,
        "name": topping.name,
        "price": float(topping.price) if topping.price else 0.0,
        "menu_item_id": topping.menu_item_id
    }

# ======================= Public Routes =========================================

@menu_bp.route('/menu', methods=['GET'])
def get_menu():
    """Retrieves all menu items from the database."""
    try:
        items = MenuItem.query.all()
        data = [to_dict_menu_item(item) for item in items]
        return standard_response(data=data, message="Menu items retrieved successfully")
    except Exception as e:
        current_app.logger.error(f"Error getting menu items: {str(e)}")
        return standard_response(None, False, "Failed to retrieve menu items", 500)

@menu_bp.route('/categories', methods=['GET'])
def get_menu_categories():
    """Retrieves all categories with their images from the database."""
    try:
        categories = Category.query.all()
        data = [{
            "id": cat.id,
            "name": cat.name,
            "image_url": cat.image_url
        } for cat in categories]
        return standard_response(data=data, message="Categories retrieved successfully")
    except Exception as e:
        current_app.logger.error(f"Error getting categories: {str(e)}")
        return standard_response(None, False, "Failed to retrieve categories", 500)

@menu_bp.route('/menu/<int:item_id>/toppings', methods=['GET'])
def get_toppings(item_id):
    """Retrieves all toppings for a specific menu item."""
    try:
        item = MenuItem.query.get_or_404(item_id)
        toppings = Topping.query.filter_by(menu_item_id=item.id).all()
        data = [to_dict_topping(t) for t in toppings]
        return standard_response(data=data, message="Toppings retrieved successfully")
    except Exception as e:
        current_app.logger.error(f"Error getting toppings: {str(e)}")
        return standard_response(None, False, "Failed to retrieve toppings", 500)

@menu_bp.route('/toppings', methods=['GET'])
def get_all_toppings():
    """Retrieves all toppings in the database."""
    try:
        toppings = Topping.query.all()
        data = [to_dict_topping(t) for t in toppings]
        return standard_response(data=data, message="All toppings retrieved successfully")
    except Exception as e:
        current_app.logger.error(f"Error getting all toppings: {str(e)}")
        return standard_response(None, False, "Failed to retrieve toppings", 500)

# ======================= Admin Routes (Protected) ===============================

@menu_bp.route('/menu', methods=['POST'])
@jwt_required()
@admin_required
def create_menu_item():
    """Creates a new menu item."""
    try:
        # Handle both form data and JSON
        if request.content_type.startswith('multipart/form-data'):
            data = request.form.to_dict()
            image_file = request.files.get('image')
        else:
            data = request.get_json()
            image_file = None

        # Required fields validation
        required_fields = ['name', 'price']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                'success': False,
                'message': f"Missing required fields: {', '.join(missing_fields)}",
                'missing_fields': missing_fields
            }), 400

        # Price validation
        try:
            price = float(data['price'])
            if price < 0:
                return jsonify({
                    'success': False,
                    'message': "Price cannot be negative",
                    'field': 'price'
                }), 400
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'message': "Invalid price format",
                'field': 'price'
            }), 400

        # Handle is_available
        is_available = True
        if 'is_available' in data:
            if isinstance(data['is_available'], str):
                is_available = data['is_available'].lower() in ['true', '1', 'yes']
            else:
                is_available = bool(data['is_available'])

        # Image handling
        image_url = None
        if image_file and image_file.filename:
            try:
                filename = secure_filename(f"{uuid.uuid4()}{os.path.splitext(image_file.filename)[1]}")
                upload_folder = os.path.join(current_app.root_path, 'static/uploads')
                os.makedirs(upload_folder, exist_ok=True)
                file_path = os.path.join(upload_folder, filename)
                image_file.save(file_path)
                image_url = f'/static/uploads/{filename}'
            except Exception as e:
                current_app.logger.error(f"Image save error: {str(e)}")
                return jsonify({
                    'success': False,
                    'message': "Failed to save image",
                    'field': 'image'
                }), 500

        # Create menu item
        new_item = MenuItem(
            name=data['name'].strip(),
            description=data.get('description', '').strip(),
            price=price,
            size=data.get('size', '').strip(),
            category=data.get('category', '').strip(),
            image_url=image_url,
            is_available=is_available
        )
        
        db.session.add(new_item)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': "Menu item created successfully",
            'data': to_dict_menu_item(new_item)
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Menu creation error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': "Server error while creating menu item",
            'error_details': str(e)
        }), 500

@menu_bp.route('/menu/<int:item_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_menu_item(item_id):
    """Updates an existing menu item."""
    try:
        item = MenuItem.query.get(item_id)
        if not item:
            return jsonify({
                'success': False,
                'message': "Menu item not found"
            }), 404
            
        # Handle both form data and JSON
        if request.content_type.startswith('multipart/form-data'):
            data = request.form.to_dict()
            image_file = request.files.get('image')
        else:
            data = request.get_json()
            image_file = None

        # Update fields
        if 'name' in data:
            item.name = data['name'].strip()
        
        if 'description' in data:
            item.description = data['description'].strip()
            
        if 'size' in data:
            item.size = data['size'].strip()
            
        if 'category' in data:
            item.category = data['category'].strip()

        # Handle price
        if 'price' in data:
            try:
                price = float(data['price'])
                if price < 0:
                    return jsonify({
                        'success': False,
                        'message': "Price cannot be negative",
                        'field': 'price'
                    }), 400
                item.price = price
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': "Invalid price format",
                    'field': 'price'
                }), 400

        # Handle is_available
        if 'is_available' in data:
            if isinstance(data['is_available'], str):
                item.is_available = data['is_available'].lower() in ['true', '1', 'yes']
            else:
                item.is_available = bool(data['is_available'])

        # Handle image update
        if image_file and image_file.filename:
            # Delete old image if exists
            if item.image_url:
                try:
                    old_path = os.path.join(current_app.root_path, item.image_url.lstrip('/'))
                    if os.path.exists(old_path):
                        os.remove(old_path)
                except Exception as e:
                    current_app.logger.error(f"Error deleting old image: {str(e)}")
            
            # Save new image
            try:
                filename = secure_filename(f"{uuid.uuid4()}{os.path.splitext(image_file.filename)[1]}")
                upload_folder = os.path.join(current_app.root_path, 'static/uploads')
                os.makedirs(upload_folder, exist_ok=True)
                file_path = os.path.join(upload_folder, filename)
                image_file.save(file_path)
                item.image_url = f'/static/uploads/{filename}'
            except Exception as e:
                current_app.logger.error(f"Image save error: {str(e)}")
                return jsonify({
                    'success': False,
                    'message': "Failed to save new image",
                    'field': 'image'
                }), 500
        
        db.session.commit()

        return jsonify({
            'success': True,
            'message': "Menu item updated successfully",
            'data': to_dict_menu_item(item)
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating menu item: {str(e)}")
        return jsonify({
            'success': False,
            'message': "Server error while updating menu item",
            'error_details': str(e)
        }), 500

@menu_bp.route('/menu/<int:item_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_menu_item(item_id):
    """Deletes a menu item."""
    try:
        item = MenuItem.query.get_or_404(item_id)
        
        # Delete associated image
        if item.image_url:
            try:
                image_path = os.path.join(current_app.root_path, item.image_url.lstrip('/'))
                if os.path.exists(image_path):
                    os.remove(image_path)
            except Exception as e:
                current_app.logger.error(f"Error deleting image file: {str(e)}")
        
        db.session.delete(item)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': "Menu item deleted successfully"
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting menu item: {str(e)}")
        return jsonify({
            'success': False,
            'message': "Server error while deleting menu item"
        }), 500

@menu_bp.route('/menu/<int:item_id>/toppings', methods=['POST'])
@jwt_required()
@admin_required
def add_topping(item_id):
    """Adds a topping to a specific menu item."""
    try:
        # Get JSON data with validation
        if not request.is_json:
            return jsonify({
                'success': False,
                'message': "Request must be JSON"
            }), 400
            
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': "No data provided"
            }), 400
        
        # Validate menu item exists
        menu_item = MenuItem.query.get(item_id)
        if not menu_item:
            return jsonify({
                'success': False,
                'message': f"Menu item with ID {item_id} not found"
            }), 404
        
        # Validate required fields
        name = data.get('name', '').strip()
        if not name:
            return jsonify({
                'success': False,
                'message': "Topping name is required",
                'field': 'name'
            }), 400
        
        # Validate price
        try:
            price = float(data.get('price', 0))
            if price < 0:
                return jsonify({
                    'success': False,
                    'message': "Price cannot be negative",
                    'field': 'price'
                }), 400
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'message': "Invalid price format",
                'field': 'price'
            }), 400
        
        # Check for duplicate topping name for this menu item (case insensitive)
        existing_topping = Topping.query.filter(
            Topping.menu_item_id == item_id,
            Topping.name.ilike(name)
        ).first()
        
        if existing_topping:
            return jsonify({
                'success': False,
                'message': f"A topping with name '{name}' already exists for this menu item",
                'field': 'name'
            }), 409
        
        # Create topping with explicit field assignment
        topping = Topping()
        topping.name = name
        topping.price = price
        topping.menu_item_id = item_id
        
        db.session.add(topping)
        db.session.commit()
        
        # Refresh to get the generated ID
        db.session.refresh(topping)
        
        return jsonify({
            'success': True,
            'message': "Topping added successfully",
            'data': to_dict_topping(topping)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding topping: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': "Server error while adding topping",
            'error_details': str(e)
        }), 500

@menu_bp.route('/toppings/<int:topping_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_topping(topping_id):
    """Deletes a topping."""
    try:
        topping = Topping.query.get_or_404(topping_id)
        db.session.delete(topping)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': "Topping deleted successfully"
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting topping: {str(e)}")
        return jsonify({
            'success': False,
            'message': "Server error while deleting topping"
        }), 500
    
@menu_bp.route('/categories', methods=['POST'])
@jwt_required()
@admin_required
def create_category():
    """Creates a new category with optional image."""
    try:
        if request.content_type.startswith('multipart/form-data'):
            data = request.form.to_dict()
            image_file = request.files.get('image')
        else:
            data = request.get_json() or {}
            image_file = None

        # Validate required field
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'message': "Category name is required"}), 400

        # Check for duplicate
        existing = Category.query.filter(Category.name.ilike(name)).first()
        if existing:
            return jsonify({'success': False, 'message': "Category already exists"}), 409

        # Handle image
        image_url = data.get('image_url')
        if image_file and image_file.filename:
            try:
                filename = secure_filename(f"{uuid.uuid4()}{os.path.splitext(image_file.filename)[1]}")
                upload_folder = os.path.join(current_app.root_path, 'static/uploads')
                os.makedirs(upload_folder, exist_ok=True)
                file_path = os.path.join(upload_folder, filename)
                image_file.save(file_path)
                image_url = f'/static/uploads/{filename}'
            except Exception as e:
                current_app.logger.error(f"Image save error: {str(e)}")
                return jsonify({'success': False, 'message': "Failed to save image"}), 500

        # Create category
        new_category = Category(name=name, image_url=image_url)
        db.session.add(new_category)
        db.session.commit()
        db.session.refresh(new_category)

        return jsonify({
            'success': True,
            'message': "Category created successfully",
            'data': {
                'id': new_category.id,
                'name': new_category.name,
                'image_url': new_category.image_url
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating category: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': "Server error while creating category"}), 500


@menu_bp.route('/categories/<int:category_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_category(category_id):
    """Update category name or image."""
    category = Category.query.get_or_404(category_id)
    try:
        data = request.form.to_dict() if request.content_type.startswith('multipart/form-data') else request.get_json() or {}
        image_file = request.files.get('image') if request.content_type.startswith('multipart/form-data') else None

        # Update name
        if 'name' in data:
            category.name = data['name'].strip()

        # Update image
        if image_file and image_file.filename:
            # Delete old image
            if category.image_url:
                old_path = os.path.join(current_app.root_path, category.image_url.lstrip('/'))
                if os.path.exists(old_path):
                    os.remove(old_path)
            # Save new image
            filename = secure_filename(f"{uuid.uuid4()}{os.path.splitext(image_file.filename)[1]}")
            upload_folder = os.path.join(current_app.root_path, 'static/uploads')
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, filename)
            image_file.save(file_path)
            category.image_url = f'/static/uploads/{filename}'

        db.session.commit()
        return jsonify({'success': True, 'message': "Category updated successfully"}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating category: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': "Server error while updating category"}), 500
