from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from extensions import db
from models.subscription import ClientSubscription, SubscriptionPayment
from models.client import Client
from models.project import Project
from models.user import User

subscriptions_bp = Blueprint('subscriptions', __name__)

@subscriptions_bp.route('/', methods=['GET'])
@jwt_required()
def get_subscriptions():
    """Get all subscriptions with optional filtering"""
    try:
        # Get query parameters
        status = request.args.get('status')
        project_id = request.args.get('project_id', type=int)
        client_id = request.args.get('client_id', type=int)
        overdue_only = request.args.get('overdue_only', 'false').lower() == 'true'
        
        # Build query
        query = ClientSubscription.query
        
        if status:
            query = query.filter(ClientSubscription.status == status)
        if project_id:
            query = query.filter(ClientSubscription.project_id == project_id)
        if client_id:
            query = query.filter(ClientSubscription.client_id == client_id)
        
        subscriptions = query.all()
        
        # Filter overdue if requested
        if overdue_only:
            subscriptions = [s for s in subscriptions if s.is_overdue]
        
        return jsonify({
            'success': True,
            'subscriptions': [subscription.to_dict() for subscription in subscriptions],
            'total': len(subscriptions)
        }), 200
        
    except Exception as e:
        print(f"❌ Error getting subscriptions: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب الاشتراكات'
        }), 500

@subscriptions_bp.route('/', methods=['POST'])
@jwt_required()
def create_subscription():
    """Create new client subscription"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['client_id', 'project_id', 'subscription_plan', 'monthly_price', 'start_date']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'الحقل {field} مطلوب'
                }), 400
        
        # Validate client and project exist
        client = Client.query.get(data['client_id'])
        if not client:
            return jsonify({
                'success': False,
                'message': 'العميل غير موجود'
            }), 404
            
        project = Project.query.get(data['project_id'])
        if not project:
            return jsonify({
                'success': False,
                'message': 'المشروع غير موجود'
            }), 404
        
        # Check if subscription already exists
        existing = ClientSubscription.query.filter_by(
            client_id=data['client_id'],
            project_id=data['project_id'],
            status='active'
        ).first()
        
        if existing:
            return jsonify({
                'success': False,
                'message': 'يوجد اشتراك نشط بالفعل لهذا العميل في هذا المشروع'
            }), 400
        
        # Parse dates
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        
        # Calculate next billing date
        billing_cycle = data.get('billing_cycle', 'monthly')
        if billing_cycle == 'monthly':
            next_billing = start_date + timedelta(days=30)
        elif billing_cycle == 'quarterly':
            next_billing = start_date + timedelta(days=90)
        elif billing_cycle == 'yearly':
            next_billing = start_date + timedelta(days=365)
        else:
            next_billing = start_date + timedelta(days=30)
        
        # Create subscription
        subscription = ClientSubscription(
            client_id=data['client_id'],
            project_id=data['project_id'],
            subscription_plan=data['subscription_plan'],
            monthly_price=data['monthly_price'],
            currency=data.get('currency', 'SAR'),
            start_date=start_date,
            end_date=datetime.strptime(data['end_date'], '%Y-%m-%d').date() if data.get('end_date') else None,
            trial_end_date=datetime.strptime(data['trial_end_date'], '%Y-%m-%d').date() if data.get('trial_end_date') else None,
            status=data.get('status', 'active'),
            billing_cycle=billing_cycle,
            next_billing_date=next_billing,
            payment_method=data.get('payment_method'),
            user_limit=data.get('user_limit'),
            storage_limit_gb=data.get('storage_limit_gb'),
            features_enabled=data.get('features_enabled', []),
            custom_domain=data.get('custom_domain'),
            notes=data.get('notes'),
            contract_reference=data.get('contract_reference')
        )
        
        db.session.add(subscription)
        db.session.commit()
        
        # Update project subscriber count if it's a subscription project
        if project.project_type == 'subscription':
            project.subscriber_count = len(project.client_subscriptions)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم إنشاء الاشتراك بنجاح',
            'subscription': subscription.to_dict()
        }), 201
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': 'تنسيق التاريخ غير صحيح (يجب أن يكون YYYY-MM-DD)'
        }), 400
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error creating subscription: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في إنشاء الاشتراك'
        }), 500

@subscriptions_bp.route('/<int:subscription_id>', methods=['GET'])
@jwt_required()
def get_subscription(subscription_id):
    """Get subscription details"""
    try:
        subscription = ClientSubscription.query.get_or_404(subscription_id)
        
        return jsonify({
            'success': True,
            'subscription': subscription.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'الاشتراك غير موجود'
        }), 404

@subscriptions_bp.route('/<int:subscription_id>', methods=['PUT'])
@jwt_required()
def update_subscription(subscription_id):
    """Update subscription details"""
    try:
        subscription = ClientSubscription.query.get_or_404(subscription_id)
        data = request.get_json()
        
        # Update allowed fields
        updatable_fields = [
            'subscription_plan', 'monthly_price', 'currency', 'end_date',
            'trial_end_date', 'status', 'billing_cycle', 'payment_method',
            'user_limit', 'storage_limit_gb', 'features_enabled',
            'custom_domain', 'notes', 'contract_reference'
        ]
        
        for field in updatable_fields:
            if field in data:
                if field in ['end_date', 'trial_end_date'] and data[field]:
                    setattr(subscription, field, datetime.strptime(data[field], '%Y-%m-%d').date())
                else:
                    setattr(subscription, field, data[field])
        
        subscription.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم تحديث الاشتراك بنجاح',
            'subscription': subscription.to_dict()
        }), 200
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': 'تنسيق التاريخ غير صحيح'
        }), 400
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error updating subscription: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في تحديث الاشتراك'
        }), 500

@subscriptions_bp.route('/<int:subscription_id>', methods=['DELETE'])
@jwt_required()
def delete_subscription(subscription_id):
    """Cancel subscription (soft delete)"""
    try:
        subscription = ClientSubscription.query.get_or_404(subscription_id)
        
        # Change status to cancelled instead of deleting
        subscription.status = 'cancelled'
        subscription.cancelled_at = datetime.utcnow()
        subscription.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم إلغاء الاشتراك بنجاح'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error cancelling subscription: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في إلغاء الاشتراك'
        }), 500

@subscriptions_bp.route('/<int:subscription_id>/permanent', methods=['DELETE'])
@jwt_required()
def permanently_delete_subscription(subscription_id):
    """Permanently delete subscription (only for cancelled subscriptions)"""
    try:
        subscription = ClientSubscription.query.get_or_404(subscription_id)
        
        # Only allow permanent deletion for cancelled subscriptions
        if subscription.status != 'cancelled':
            return jsonify({
                'success': False,
                'message': 'يمكن حذف الاشتراكات الملغية فقط نهائياً'
            }), 400
        
        # Delete related payments first
        SubscriptionPayment.query.filter_by(subscription_id=subscription_id).delete()
        
        # Delete the subscription
        db.session.delete(subscription)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم حذف الاشتراك نهائياً'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error permanently deleting subscription: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في حذف الاشتراك نهائياً'
        }), 500

@subscriptions_bp.route('/<int:subscription_id>/payments', methods=['POST'])
@jwt_required()
def record_payment(subscription_id):
    """Record a payment for subscription"""
    try:
        subscription = ClientSubscription.query.get_or_404(subscription_id)
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['amount', 'payment_date']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'الحقل {field} مطلوب'
                }), 400
        
        # Parse payment date
        payment_date = datetime.strptime(data['payment_date'], '%Y-%m-%d').date()
        
        # Create payment record
        payment = SubscriptionPayment(
            subscription_id=subscription_id,
            amount=data['amount'],
            currency=data.get('currency', 'SAR'),
            payment_date=payment_date,
            payment_method=data.get('payment_method'),
            status=data.get('status', 'completed'),
            transaction_id=data.get('transaction_id'),
            invoice_number=data.get('invoice_number'),
            receipt_url=data.get('receipt_url'),
            billing_period_start=datetime.strptime(data['billing_period_start'], '%Y-%m-%d').date() if data.get('billing_period_start') else None,
            billing_period_end=datetime.strptime(data['billing_period_end'], '%Y-%m-%d').date() if data.get('billing_period_end') else None,
            notes=data.get('notes'),
            created_by=get_jwt_identity()
        )
        
        db.session.add(payment)
        
        # Update subscription payment info
        subscription.record_payment(data['amount'], payment_date)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم تسجيل الدفعة بنجاح',
            'payment': payment.to_dict(),
            'subscription': subscription.to_dict()
        }), 201
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': 'تنسيق التاريخ غير صحيح'
        }), 400
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error recording payment: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في تسجيل الدفعة'
        }), 500

@subscriptions_bp.route('/<int:subscription_id>/payments', methods=['GET'])
@jwt_required()
def get_subscription_payments(subscription_id):
    """Get payment history for subscription"""
    try:
        subscription = ClientSubscription.query.get_or_404(subscription_id)
        payments = SubscriptionPayment.query.filter_by(subscription_id=subscription_id).order_by(SubscriptionPayment.payment_date.desc()).all()
        
        return jsonify({
            'success': True,
            'payments': [payment.to_dict() for payment in payments],
            'total': len(payments)
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب تاريخ الدفعات'
        }), 500

@subscriptions_bp.route('/statistics', methods=['GET'])
@jwt_required()
def get_subscription_statistics():
    """Get subscription statistics"""
    try:
        # Total subscriptions by status
        active_count = ClientSubscription.query.filter_by(status='active').count()
        paused_count = ClientSubscription.query.filter_by(status='paused').count()
        cancelled_count = ClientSubscription.query.filter_by(status='cancelled').count()
        
        # Revenue calculations
        active_subscriptions = ClientSubscription.query.filter_by(status='active').all()
        monthly_revenue = sum(sub.monthly_revenue_projection for sub in active_subscriptions)
        
        # Overdue subscriptions
        overdue_subscriptions = [sub for sub in active_subscriptions if sub.is_overdue]
        overdue_count = len(overdue_subscriptions)
        
        # Trial subscriptions
        trial_subscriptions = [sub for sub in active_subscriptions if sub.is_trial]
        trial_count = len(trial_subscriptions)
        
        # Total revenue from all payments
        total_revenue = db.session.query(db.func.sum(SubscriptionPayment.amount)).filter(
            SubscriptionPayment.status == 'completed'
        ).scalar() or 0
        
        return jsonify({
            'success': True,
            'statistics': {
                'total_subscriptions': active_count + paused_count + cancelled_count,
                'active_subscriptions': active_count,
                'paused_subscriptions': paused_count,
                'cancelled_subscriptions': cancelled_count,
                'trial_subscriptions': trial_count,
                'overdue_subscriptions': overdue_count,
                'monthly_revenue': float(monthly_revenue),
                'total_revenue': float(total_revenue)
            }
        }), 200
        
    except Exception as e:
        print(f"❌ Error getting subscription statistics: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب إحصائيات الاشتراكات'
        }), 500

@subscriptions_bp.route('/overdue', methods=['GET'])
@jwt_required()
def get_overdue_subscriptions():
    """Get overdue subscriptions"""
    try:
        subscriptions = ClientSubscription.query.filter_by(status='active').all()
        overdue_subscriptions = [sub for sub in subscriptions if sub.is_overdue]
        
        return jsonify({
            'success': True,
            'subscriptions': [sub.to_dict() for sub in overdue_subscriptions],
            'total': len(overdue_subscriptions)
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب الاشتراكات المتأخرة'
        }), 500

@subscriptions_bp.route('/projects/<int:project_id>/available-clients', methods=['GET'])
@jwt_required()
def get_available_clients_for_project(project_id):
    """Get clients that can subscribe to a project"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # Get all clients
        all_clients = Client.query.filter_by(status='active').all()
        
        # Get clients already subscribed to this project
        subscribed_client_ids = [sub.client_id for sub in ClientSubscription.query.filter_by(
            project_id=project_id,
            status='active'
        ).all()]
        
        # Filter out already subscribed clients
        available_clients = [client for client in all_clients if client.id not in subscribed_client_ids]
        
        return jsonify({
            'success': True,
            'clients': [client.to_dict() for client in available_clients],
            'project': {
                'id': project.id,
                'name': project.name,
                'project_type': project.project_type
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب العملاء المتاحين'
        }), 500 