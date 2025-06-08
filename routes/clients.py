from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from extensions import db
from models.client import Client

clients_bp = Blueprint('clients', __name__)

@clients_bp.route('/', methods=['GET'])
@jwt_required()
def get_clients():
    """Get all clients"""
    try:
        clients = Client.query.filter_by(status='active').all()
        
        return jsonify({
            'success': True,
            'clients': [client.to_dict() for client in clients]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب العملاء'
        }), 500

@clients_bp.route('/<int:client_id>', methods=['GET'])
@jwt_required()
def get_client(client_id):
    """Get single client by ID"""
    try:
        client = Client.query.get_or_404(client_id)
        
        return jsonify({
            'success': True,
            'client': client.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'العميل غير موجود'
        }), 404 