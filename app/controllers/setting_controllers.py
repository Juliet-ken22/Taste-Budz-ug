from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from app.utils.auth import token_required
from app.models.settings import SystemConfig, BusinessHours, MaintenanceMode
from app import db
from datetime import datetime

# Initialize the blueprint
settings_bp = Blueprint("settings", __name__, url_prefix="/api/v1/settings_bp")

# Helper function to get system config value
def get_config_value(key, default_value=None):
    config = SystemConfig.query.filter_by(key=key).first()
    return config.value if config else default_value

# Helper function to set system config value
def set_config_value(key, value):
    config = SystemConfig.query.filter_by(key=key).first()
    if config:
        config.value = str(value)
        config.last_updated = datetime.utcnow()
    else:
        config = SystemConfig(key=key, value=str(value))
        db.session.add(config)
    return config

@settings_bp.route('/settings', methods=['GET', 'OPTIONS'])
@cross_origin(supports_credentials=True)
@token_required(roles=['admin', 'super_admin'])
def get_system_settings():
    """
    Retrieves system settings.
    """
    try:
        settings = {
            "system_name": get_config_value("system_name", "Restaurant POS"),
            "tax_rate": float(get_config_value("tax_rate", 0.08)),
            "service_charge": float(get_config_value("service_charge", 0.1)),
            "currency": get_config_value("currency", "USD"),
            "online_ordering": get_config_value("online_ordering", "True").lower() == "true"
        }
        
        return jsonify({"status": "success", "data": settings})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@settings_bp.route('/settings', methods=['PUT', 'OPTIONS'])
@cross_origin(supports_credentials=True)
@token_required(roles=['admin', 'super_admin'])
def update_system_settings():
    """
    Updates system settings.
    """
    try:
        data = request.get_json()
        
        # Update each setting if provided
        if 'system_name' in data:
            set_config_value("system_name", data['system_name'])
        
        if 'tax_rate' in data:
            set_config_value("tax_rate", data['tax_rate'])
        
        if 'service_charge' in data:
            set_config_value("service_charge", data['service_charge'])
        
        if 'currency' in data:
            set_config_value("currency", data['currency'])
        
        if 'online_ordering' in data:
            set_config_value("online_ordering", data['online_ordering'])
        
        # Save all changes
        db.session.commit()
        
        # Return updated settings
        settings = {
            "system_name": get_config_value("system_name", "Restaurant POS"),
            "tax_rate": float(get_config_value("tax_rate", 0.08)),
            "service_charge": float(get_config_value("service_charge", 0.1)),
            "currency": get_config_value("currency", "USD"),
            "online_ordering": get_config_value("online_ordering", "True").lower() == "true"
        }
        
        return jsonify({
            "status": "success", 
            "message": "Settings updated successfully",
            "data": settings
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@settings_bp.route('/operating-hours', methods=['GET', 'OPTIONS'])
@cross_origin(supports_credentials=True)
@token_required()
def get_operating_hours():
    """
    Retrieves the restaurant's operating hours.
    """
    try:
        # Get all business hours ordered by day of week
        hours_list = BusinessHours.query.order_by(BusinessHours.day_of_week).all()
        
        # Convert to dictionary format
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        hours_dict = {}
        
        for i, day in enumerate(days):
            day_hours = next((h for h in hours_list if h.day_of_week == i), None)
            
            if day_hours:
                hours_dict[day] = {
                    "open": day_hours.open_time.strftime("%H:%M") if day_hours.open_time else "09:00",
                    "close": day_hours.close_time.strftime("%H:%M") if day_hours.close_time else "17:00",
                    "is_closed": day_hours.is_closed
                }
            else:
                # Default hours if not found
                hours_dict[day] = {
                    "open": "09:00",
                    "close": "17:00",
                    "is_closed": False
                }
        
        return jsonify({"status": "success", "data": hours_dict})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@settings_bp.route('/operating-hours', methods=['PUT', 'OPTIONS'])
@cross_origin(supports_credentials=True)
@token_required(roles=['admin', 'super_admin'])
def update_operating_hours():
    """
    Updates the restaurant's operating hours.
    """
    try:
        data = request.get_json()
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        
        for i, day in enumerate(days):
            if day in data:
                day_data = data[day]
                
                # Find existing hours for this day
                hours = BusinessHours.query.filter_by(day_of_week=i).first()
                
                if not hours:
                    # Create new hours entry if it doesn't exist
                    hours = BusinessHours(day_of_week=i)
                    db.session.add(hours)
                
                # Update the hours
                hours.is_closed = day_data.get("is_closed", False)
                
                if not hours.is_closed:
                    # Parse time strings and update
                    open_time = day_data.get("open", "09:00")
                    close_time = day_data.get("close", "17:00")
                    
                    # Convert string to time object
                    hours.open_time = datetime.strptime(open_time, "%H:%M").time()
                    hours.close_time = datetime.strptime(close_time, "%H:%M").time()
        
        # Save all changes
        db.session.commit()
        
        # Return updated hours
        return jsonify({
            "status": "success", 
            "message": "Operating hours updated successfully",
            "data": data
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@settings_bp.route('/maintenance-mode', methods=['GET', 'OPTIONS'])
@cross_origin(supports_credentials=True)
@token_required(roles=['admin', 'super_admin'])
def get_maintenance_mode():
    """
    Retrieves the current maintenance mode status.
    """
    try:
        # Get maintenance mode status
        maintenance = MaintenanceMode.query.first()
        
        if not maintenance:
            # Create default maintenance mode if it doesn't exist
            maintenance = MaintenanceMode(maintenance_mode=False)
            db.session.add(maintenance)
            db.session.commit()
        
        return jsonify({
            "status": "success", 
            "data": {
                "maintenance_mode": maintenance.maintenance_mode
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@settings_bp.route('/maintenance-mode', methods=['PUT', 'OPTIONS'])
@cross_origin(supports_credentials=True)
@token_required(roles=['admin', 'super_admin'])
def set_maintenance_mode():
    """
    Updates the maintenance mode status.
    """
    try:
        data = request.get_json()
        maintenance_mode = data.get('maintenance_mode', False)
        
        # Get or create maintenance mode record
        maintenance = MaintenanceMode.query.first()
        
        if not maintenance:
            maintenance = MaintenanceMode(maintenance_mode=maintenance_mode)
            db.session.add(maintenance)
        else:
            maintenance.maintenance_mode = maintenance_mode
        
        # Save changes
        db.session.commit()
        
        return jsonify({
            "status": "success", 
            "message": "Maintenance mode updated successfully",
            "data": {
                "maintenance_mode": maintenance.maintenance_mode
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500