from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from extensions import db
from models.expense import Expense

expenses_bp = Blueprint('expenses', __name__)

@expenses_bp.route('/', methods=['GET'])
@jwt_required()
def get_expenses():
    """Get all expenses"""
    try:
        expenses = Expense.query.order_by(Expense.expense_date.desc()).all()
        
        return jsonify({
            'success': True,
            'expenses': [expense.to_dict() for expense in expenses]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب المصروفات'
        }), 500 