from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from datetime import datetime
from extensions import db
from models.client import Client

clients_bp = Blueprint('clients', __name__)

@clients_bp.route('/', methods=['GET'])
@jwt_required()
def get_clients():
    """Get all clients with filtering options"""
    try:
        current_app.logger.info('📥 بدء جلب قائمة العملاء')
        
        # Get query parameters
        client_type = request.args.get('type')  # 'company' or 'individual'
        status = request.args.get('status')
        search = request.args.get('search', '').strip()
        
        current_app.logger.info(f'🔍 فلاتر البحث: type={client_type}, status={status}, search={search}')
        
        # Build query
        query = Client.query
        
        # If status is explicitly provided (even as empty string), use it
        # If not provided at all, default to 'active'
        if status is not None:
            if status:  # Non-empty status
                query = query.filter_by(status=status)
                current_app.logger.info(f'🔍 تصفية حسب الحالة: {status}')
            # If status is empty string, don't filter by status (show all)
            else:
                current_app.logger.info('🔍 عرض جميع الحالات (بدون تصفية)')
        else:
            # Default behavior: show only active clients
            query = query.filter_by(status='active')
            current_app.logger.info('🔍 الحالة الافتراضية: active فقط')
        
        if client_type:
            query = query.filter_by(client_type=client_type)
            current_app.logger.info(f'🔍 تصفية حسب النوع: {client_type}')
        
        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                db.or_(
                    Client.name.like(search_filter),
                    Client.first_name.like(search_filter),
                    Client.last_name.like(search_filter),
                    Client.company_name.like(search_filter),
                    Client.email.like(search_filter)
                )
            )
            current_app.logger.info(f'🔍 البحث النصي: {search}')
        
        clients = query.order_by(Client.created_at.desc()).all()
        
        current_app.logger.info(f'✅ تم جلب {len(clients)} عميل')
        
        return jsonify({
            'success': True,
            'clients': [client.to_dict() for client in clients],
            'total': len(clients)
        })
        
    except Exception as e:
        current_app.logger.error(f"💥 خطأ في جلب العملاء: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب العملاء'
        }), 500

@clients_bp.route('/<int:client_id>', methods=['GET'])
@jwt_required()
def get_client(client_id):
    """Get single client by ID"""
    try:
        current_app.logger.info(f'📋 جلب بيانات العميل: {client_id}')
        client = Client.query.get_or_404(client_id)
        
        current_app.logger.info(f'✅ تم جلب بيانات العميل: {client.name}')
        return jsonify({
            'success': True,
            'client': client.to_dict()
        })
        
    except Exception as e:
        current_app.logger.error(f"💥 خطأ في جلب العميل {client_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'العميل غير موجود'
        }), 404

@clients_bp.route('/', methods=['POST'])
@jwt_required()
def create_client():
    """Create new client (company or individual)"""
    try:
        current_app.logger.info('🆕 بدء إنشاء عميل جديد')
        
        data = request.get_json()
        current_app.logger.debug(f'📄 البيانات المستلمة: {data}')
        
        if not data:
            current_app.logger.warning('❌ لا توجد بيانات في الطلب')
            return jsonify({
                'success': False,
                'message': 'لا توجد بيانات'
            }), 400
        
        # Validate required fields
        client_type = data.get('client_type', 'company')
        current_app.logger.info(f'👤 نوع العميل: {client_type}')
        
        if client_type not in ['company', 'individual']:
            current_app.logger.warning(f'❌ نوع عميل غير صحيح: {client_type}')
            return jsonify({
                'success': False,
                'message': 'نوع العميل يجب أن يكون company أو individual'
            }), 400
        
        email = data.get('email', '').strip().lower()
        if not email:
            current_app.logger.warning('❌ البريد الإلكتروني مفقود')
            return jsonify({
                'success': False,
                'message': 'البريد الإلكتروني مطلوب'
            }), 400
        
        current_app.logger.info(f'📧 البريد الإلكتروني: {email}')
        
        # Check if email already exists (only for active clients)
        existing_client = Client.query.filter_by(email=email, status='active').first()
        if existing_client:
            current_app.logger.warning(f'❌ البريد الإلكتروني موجود بالفعل: {email}')
            return jsonify({
                'success': False,
                'message': 'البريد الإلكتروني مسجل بالفعل'
            }), 400
        
        # Validate based on client type
        if client_type == 'individual':
            first_name = data.get('first_name', '').strip()
            last_name = data.get('last_name', '').strip()
            
            if not first_name or not last_name:
                current_app.logger.warning('❌ الاسم الأول أو الأخير مفقود للفرد')
                return jsonify({
                    'success': False,
                    'message': 'الاسم الأول والأخير مطلوبان للأفراد'
                }), 400
                
            name = f"{first_name} {last_name}"
            current_app.logger.info(f'👤 اسم الفرد: {name}')
            
        else:  # company
            company_name = data.get('company_name', '').strip()
            if not company_name:
                current_app.logger.warning('❌ اسم الشركة مفقود')
                return jsonify({
                    'success': False,
                    'message': 'اسم الشركة مطلوب للشركات'
                }), 400
            
            name = company_name
            current_app.logger.info(f'🏢 اسم الشركة: {name}')
        
        # Create new client
        current_app.logger.info('🔧 إنشاء كائن العميل الجديد')
        client = Client(
            client_type=client_type,
            name=name,
            email=email,
            phone=data.get('phone', '').strip(),
            secondary_phone=data.get('secondary_phone', '').strip(),
            address=data.get('address', '').strip(),
            city=data.get('city', '').strip(),
            country=data.get('country', '').strip(),
            postal_code=data.get('postal_code', '').strip(),
            website=data.get('website', '').strip(),
            status=data.get('status', 'active'),
            source=data.get('source', '').strip(),
            priority=data.get('priority', 'medium'),
            credit_limit=data.get('credit_limit'),
            currency=data.get('currency', 'SAR'),
            payment_terms=data.get('payment_terms', 30),
            notes=data.get('notes', '').strip(),
            tags=data.get('tags', [])
        )
        
        current_app.logger.info(f'⚙️ حالة العميل: {client.status}')
        current_app.logger.info(f'⭐ أولوية العميل: {client.priority}')
        
        # Set type-specific fields
        if client_type == 'individual':
            client.first_name = data.get('first_name', '').strip()
            client.last_name = data.get('last_name', '').strip()
            client.national_id = data.get('national_id', '').strip()
            client.gender = data.get('gender', '').strip()
            
            current_app.logger.info(f'👤 تفاصيل الفرد - الجنس: {client.gender}, الهوية: {client.national_id}')
            
            # Parse date of birth
            dob_str = data.get('date_of_birth')
            if dob_str:
                try:
                    client.date_of_birth = datetime.strptime(dob_str, '%Y-%m-%d').date()
                    current_app.logger.info(f'📅 تاريخ الميلاد: {client.date_of_birth}')
                except ValueError:
                    current_app.logger.warning(f'❌ تاريخ ميلاد غير صحيح: {dob_str}')
        
        else:  # company
            client.company_name = data.get('company_name', '').strip()
            client.tax_number = data.get('tax_number', '').strip()
            client.registration_number = data.get('registration_number', '').strip()
            client.industry = data.get('industry', '').strip()
            client.company_size = data.get('company_size', '').strip()
            
            current_app.logger.info(f'🏢 تفاصيل الشركة - القطاع: {client.industry}, الرقم الضريبي: {client.tax_number}')
            
            # Contact person information
            client.contact_person = data.get('contact_person', '').strip()
            client.contact_position = data.get('contact_position', '').strip()
            client.contact_phone = data.get('contact_phone', '').strip()
            client.contact_email = data.get('contact_email', '').strip()
            
            if client.contact_person:
                current_app.logger.info(f'👤 شخص الاتصال: {client.contact_person} - {client.contact_position}')
        
        current_app.logger.info('💾 حفظ العميل في قاعدة البيانات...')
        db.session.add(client)
        db.session.commit()
        
        current_app.logger.info(f'✅ تم إنشاء العميل بنجاح - ID: {client.id}')
        
        return jsonify({
            'success': True,
            'message': f'تم إنشاء العميل بنجاح',
            'client': client.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'💥 خطأ في إنشاء العميل: {str(e)}')
        current_app.logger.error(f'💥 تفاصيل الخطأ: {type(e).__name__}')
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في إنشاء العميل'
        }), 500

@clients_bp.route('/<int:client_id>', methods=['PUT'])
@jwt_required()
def update_client(client_id):
    """Update existing client"""
    try:
        client = Client.query.get_or_404(client_id)
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'لا توجد بيانات للتحديث'
            }), 400
        
        # Check email uniqueness if being updated
        new_email = data.get('email', '').strip().lower()
        if new_email and new_email != client.email:
            existing_client = Client.query.filter_by(email=new_email, status='active').first()
            if existing_client:
                return jsonify({
                    'success': False,
                    'message': 'البريد الإلكتروني مسجل بالفعل'
                }), 400
        
        # Update common fields
        common_fields = [
            'email', 'phone', 'secondary_phone', 'address', 'city', 'country',
            'postal_code', 'website', 'status', 'source', 'priority',
            'credit_limit', 'currency', 'payment_terms', 'notes', 'tags'
        ]
        
        for field in common_fields:
            if field in data:
                setattr(client, field, data[field])
        
        # Update type-specific fields
        if client.client_type == 'individual':
            individual_fields = ['first_name', 'last_name', 'national_id', 'gender']
            for field in individual_fields:
                if field in data:
                    setattr(client, field, data[field])
            
            # Update name if first/last name changed
            if 'first_name' in data or 'last_name' in data:
                first_name = data.get('first_name', client.first_name)
                last_name = data.get('last_name', client.last_name)
                client.name = f"{first_name} {last_name}" if first_name and last_name else client.name
            
            # Parse date of birth
            dob_str = data.get('date_of_birth')
            if dob_str:
                try:
                    client.date_of_birth = datetime.strptime(dob_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
        
        else:  # company
            company_fields = [
                'company_name', 'tax_number', 'registration_number', 'industry',
                'company_size', 'contact_person', 'contact_position',
                'contact_phone', 'contact_email'
            ]
            for field in company_fields:
                if field in data:
                    setattr(client, field, data[field])
            
            # Update name if company name changed
            if 'company_name' in data:
                client.name = data['company_name']
        
        client.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم تحديث العميل بنجاح',
            'client': client.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error updating client: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في تحديث العميل'
        }), 500

@clients_bp.route('/<int:client_id>', methods=['DELETE'])
@jwt_required()
def delete_client(client_id):
    """Delete client (soft delete by setting status to inactive)"""
    try:
        client = Client.query.get_or_404(client_id)
        
        # Check if client has active projects or subscriptions
        if client.active_projects_count > 0:
            return jsonify({
                'success': False,
                'message': f'لا يمكن حذف العميل. يوجد {client.active_projects_count} مشروع نشط مرتبط بهذا العميل'
            }), 400
        
        # Soft delete by setting status to inactive
        client.status = 'inactive'
        client.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم حذف العميل بنجاح'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting client: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في حذف العميل'
        }), 500

@clients_bp.route('/statistics', methods=['GET'])
@jwt_required()
def get_client_statistics():
    """Get client statistics"""
    try:
        total_clients = Client.query.filter_by(status='active').count()
        company_clients = Client.query.filter_by(status='active', client_type='company').count()
        individual_clients = Client.query.filter_by(status='active', client_type='individual').count()
        
        return jsonify({
            'success': True,
            'statistics': {
                'total_clients': total_clients,
                'company_clients': company_clients,
                'individual_clients': individual_clients,
                'inactive_clients': Client.query.filter_by(status='inactive').count()
            }
        })
        
    except Exception as e:
        print(f"Error getting client statistics: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في جلب إحصائيات العملاء'
        }), 500 