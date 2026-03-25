from flask import Blueprint, request, jsonify
from app.utils.auth import token_required
from datetime import datetime, timedelta
from app.models.analytics import SalesAnalytics, CustomerMetrics, ProductPerformance  # Updated import
from app import db
from app.models.Order import Order
from app.models.User import User
from app.models.Branch import Branch
from app.models.ContactMessage import ContactMessage
from sqlalchemy import func, extract
import random

# Corrected URL prefix to match frontend
analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/v1/analytics')

@analytics_bp.route('/orders', methods=['GET', 'OPTIONS'])
@token_required(roles=['admin', 'super_admin'])
def get_order_analytics():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    # Mock data to match the expected format for AdminOverview.js
    monthly_breakdown = [
        {"month": "Jan", "order_count": 50, "revenue": 5000},
        {"month": "Feb", "order_count": 75, "revenue": 8500},
        {"month": "Mar", "order_count": 90, "revenue": 9200},
        {"month": "Apr", "order_count": 120, "revenue": 15000},
        {"month": "May", "order_count": 150, "revenue": 18500},
        {"month": "Jun", "order_count": 180, "revenue": 21000}
    ]
    total_customers = 1250
    
    return jsonify({
        "total_customers": total_customers,
        "monthly_breakdown": monthly_breakdown
    }), 200

@analytics_bp.route('/revenue', methods=['GET', 'OPTIONS'])
@token_required(roles=['admin', 'super_admin'])
def get_revenue_analytics():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    return jsonify({"status": "success"}), 200
@analytics_bp.route('/dashboard-stats', methods=['GET', 'OPTIONS'])
@token_required(roles=['admin', 'super_admin'])
def get_dashboard_stats():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        # Get total users count from CustomerMetrics
        latest_customer_metrics = CustomerMetrics.query.order_by(CustomerMetrics.date.desc()).first()
        
        if latest_customer_metrics:
            total_users = latest_customer_metrics.new_customers + latest_customer_metrics.repeat_customers
        else:
            total_users = User.query.filter(User.role == 'customer').count()
        
        pending_orders = Order.query.filter(Order.status == 'pending').count()
        total_branches = Branch.query.count()
        
        # Get new messages count - NOW USING THE STATUS FIELD
        new_messages = ContactMessage.query.filter(ContactMessage.status == 'new').count()
        
        completed_orders = Order.query.filter(Order.status == 'completed').count()
        
        current_month = datetime.now().replace(day=1)
        monthly_sales = SalesAnalytics.query.filter(
            SalesAnalytics.period == 'month',
            SalesAnalytics.period_start >= current_month
        ).first()
        
        total_revenue = monthly_sales.total_amount if monthly_sales else 0
        
        return jsonify({
            "total_users": total_users,
            "pending_orders": pending_orders,
            "total_branches": total_branches,
            "new_messages": new_messages,
            "completed_orders": completed_orders,
            "total_revenue": float(total_revenue)
        }), 200
    except Exception as e:
        return jsonify({"message": f"Error fetching dashboard stats: {str(e)}"}), 500

@analytics_bp.route('/monthly-revenue', methods=['GET', 'OPTIONS'])
@token_required(roles=['admin', 'super_admin'])
def get_monthly_revenue():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        six_months_ago = datetime.now().replace(day=1) - timedelta(days=150)
        
        monthly_revenue = SalesAnalytics.query.filter(
            SalesAnalytics.period == 'month',
            SalesAnalytics.period_start >= six_months_ago
        ).order_by(SalesAnalytics.period_start).all()
        
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        result = []
        
        for item in monthly_revenue:
            month_name = month_names[item.period_start.month - 1]
            result.append({
                "month": month_name,
                "revenue": float(item.total_amount) if item.total_amount else 0
            })
        
        if len(result) < 6:
            current_month = datetime.now().month
            for i in range(6):
                month_idx = (current_month - 5 + i) % 12
                month_name = month_names[month_idx]
                
                if not any(item['month'] == month_name for item in result):
                    result.append({
                        "month": month_name,
                        "revenue": 0
                    })
            
            result.sort(key=lambda x: month_names.index(x['month']))
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"message": f"Error fetching monthly revenue: {str(e)}"}), 500

@analytics_bp.route('/order-status-distribution', methods=['GET', 'OPTIONS'])
@token_required(roles=['admin', 'super_admin'])
def get_order_status_distribution():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        status_counts = db.session.query(
            Order.status,
            func.count(Order.id).label('count')
        ).group_by(Order.status).all()
        
        result = []
        for item in status_counts:
            result.append({
                "name": item.status.capitalize(),
                "value": item.count
            })
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"message": f"Error fetching order status distribution: {str(e)}"}), 500

@analytics_bp.route('/category-distribution', methods=['GET', 'OPTIONS'])
@token_required(roles=['admin', 'super_admin'])
def get_category_distribution():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        result = [
            {"name": "Appetizers", "value": 25},
            {"name": "Main Course", "value": 40},
            {"name": "Desserts", "value": 20},
            {"name": "Beverages", "value": 15}
        ]
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"message": f"Error fetching category distribution: {str(e)}"}), 500

@analytics_bp.route('/monthly-performance', methods=['GET', 'OPTIONS'])
@token_required(roles=['admin', 'super_admin'])
def get_monthly_performance():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        six_months_ago = datetime.now().replace(day=1) - timedelta(days=150)
        
        monthly_performance = SalesAnalytics.query.filter(
            SalesAnalytics.period == 'month',
            SalesAnalytics.period_start >= six_months_ago
        ).order_by(SalesAnalytics.period_start).all()
        
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        result = []
        
        for item in monthly_performance:
            month_name = month_names[item.period_start.month - 1]
            result.append({
                "month": month_name,
                "orders": item.order_count,
                "revenue": float(item.total_amount) if item.total_amount else 0
            })
        
        if len(result) < 6:
            current_month = datetime.now().month
            for i in range(6):
                month_idx = (current_month - 5 + i) % 12
                month_name = month_names[month_idx]
                
                if not any(item['month'] == month_name for item in result):
                    result.append({
                        "month": month_name,
                        "orders": 0,
                        "revenue": 0
                    })
            
            result.sort(key=lambda x: month_names.index(x['month']))
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"message": f"Error fetching monthly performance: {str(e)}"}), 500

@analytics_bp.route('/customers', methods=['GET', 'OPTIONS'])
@token_required(roles=['admin', 'super_admin'])
def get_customer_analytics():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        # Updated to use CustomerMetrics
        latest_customer_metrics = CustomerMetrics.query.order_by(CustomerMetrics.date.desc()).first()
        
        if latest_customer_metrics:
            total_customers = latest_customer_metrics.new_customers + latest_customer_metrics.repeat_customers
        else:
            total_customers = User.query.filter(User.role == 'customer').count()
        
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_customer_metrics = CustomerMetrics.query.filter(
            CustomerMetrics.date >= thirty_days_ago
        ).all()
        
        new_customers = sum(metrics.new_customers for metrics in recent_customer_metrics)
        
        six_months_ago = datetime.now() - timedelta(days=180)
        customer_growth = CustomerMetrics.query.filter(
            CustomerMetrics.date >= six_months_ago
        ).order_by(CustomerMetrics.date).all()
        
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        growth_data = []
        
        monthly_data = {}
        for metrics in customer_growth:
            month_name = month_names[metrics.date.month - 1]
            if month_name not in monthly_data:
                monthly_data[month_name] = 0
            monthly_data[month_name] += metrics.new_customers
        
        for month, customers in monthly_data.items():
            growth_data.append({
                "month": month,
                "customers": customers
            })
        
        return jsonify({
            "total_customers": total_customers,
            "new_customers": new_customers,
            "growth_data": growth_data
        }), 200
    except Exception as e:
        return jsonify({"message": f"Error fetching customer analytics: {str(e)}"}), 500

@analytics_bp.route('/popular-items', methods=['GET', 'OPTIONS'])
@token_required(roles=['admin', 'super_admin'])
def get_popular_items():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        limit = request.args.get('limit', 10, type=int)
        
        last_month = datetime.now().replace(day=1) - timedelta(days=1)
        last_month_start = last_month.replace(day=1)
        
        popular_items = db.session.query(
            ProductPerformance.product_id,
            func.sum(ProductPerformance.units_sold).label('total_units'),
            func.sum(ProductPerformance.revenue).label('total_revenue')
        ).filter(
            ProductPerformance.period == 'month',
            ProductPerformance.period_start >= last_month_start
        ).group_by(ProductPerformance.product_id).order_by(
            func.sum(ProductPerformance.units_sold).desc()
        ).limit(limit).all()
        
        result = []
        for item in popular_items:
            result.append({
                "name": f"Product {item.product_id}",
                "count": item.total_units,
                "revenue": float(item.total_revenue) if item.total_revenue else 0
            })
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"message": f"Error fetching popular items: {str(e)}"}), 500

@analytics_bp.route('/reservations', methods=['GET', 'OPTIONS'])
@token_required(roles=['admin', 'super_admin'])
def get_reservation_analytics():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        result = {
            "total_reservations": 245,
            "status_distribution": {
                "confirmed": 180,
                "pending": 45,
                "cancelled": 20
            },
            "trend_data": [
                {"month": "Jan", "reservations": 35},
                {"month": "Feb", "reservations": 42},
                {"month": "Mar", "reservations": 38},
                {"month": "Apr", "reservations": 45},
                {"month": "May", "reservations": 52},
                {"month": "Jun", "reservations": 33}
            ]
        }
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"message": f"Error fetching reservation analytics: {str(e)}"}), 500