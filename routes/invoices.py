from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from extensions import db
from models.invoice import Invoice

invoices_bp = Blueprint('invoices', __name__)

@invoices_bp.route('/', methods=['GET'])
@jwt_required()
def get_invoices():
    """Get all invoices"""
    try:
        invoices = Invoice.query.order_by(Invoice.issue_date.desc()).all()
        
        return jsonify({
            'success': True,
            'invoices': [invoice.to_dict() for invoice in invoices]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب الفواتير'
        }), 500 