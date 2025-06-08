from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from extensions import db
from models.timetrack import TimeTrack

timetrack_bp = Blueprint('timetrack', __name__)

@timetrack_bp.route('/', methods=['GET'])
@jwt_required()
def get_time_tracks():
    """Get all time tracks"""
    try:
        time_tracks = TimeTrack.query.order_by(TimeTrack.date.desc()).all()
        
        return jsonify({
            'success': True,
            'time_tracks': [track.to_dict() for track in time_tracks]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب سجلات الوقت'
        }), 500 