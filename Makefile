# =================================================================
# ERP System Makefile
# Domain: manage.fikra.solutions
# Port: 8005
# =================================================================

.PHONY: help dev prod deploy stop restart logs clean backup health test

# Default target
help:
	@echo "🚀 نظام إدارة الموارد - أوامر المساعدة"
	@echo "======================================"
	@echo ""
	@echo "📋 أوامر التطوير:"
	@echo "  make dev      - تشغيل بيئة التطوير"
	@echo "  make dev-stop - إيقاف بيئة التطوير"
	@echo "  make dev-logs - عرض سجلات التطوير"
	@echo ""
	@echo "📋 أوامر الإنتاج:"
	@echo "  make prod     - تشغيل بيئة الإنتاج"
	@echo "  make deploy   - النشر الكامل"
	@echo "  make stop     - إيقاف النظام"
	@echo "  make restart  - إعادة تشغيل النظام"
	@echo ""
	@echo "📋 أوامر المراقبة:"
	@echo "  make logs     - عرض السجلات"
	@echo "  make health   - فحص صحة النظام"
	@echo "  make status   - حالة الخدمات"
	@echo ""
	@echo "📋 أوامر الصيانة:"
	@echo "  make backup   - نسخة احتياطية"
	@echo "  make clean    - تنظيف النظام"
	@echo "  make update   - تحديث النظام"
	@echo "  make test     - اختبار النظام"
	@echo ""
	@echo "🌐 الموقع: https://manage.fikra.solutions"
	@echo "🔧 البورت: 8005"

# Development commands
dev:
	@echo "🚀 تشغيل بيئة التطوير..."
	cp env-production.template .env.dev
	docker-compose -f docker-compose.dev.yml up -d
	@echo "✅ بيئة التطوير تعمل على: http://localhost:8005"

dev-stop:
	@echo "⏹️ إيقاف بيئة التطوير..."
	docker-compose -f docker-compose.dev.yml down

dev-logs:
	@echo "📜 عرض سجلات التطوير..."
	docker-compose -f docker-compose.dev.yml logs -f

dev-shell:
	@echo "🐚 الدخول لحاوية التطوير..."
	docker-compose -f docker-compose.dev.yml exec web bash

# Production commands
prod:
	@echo "🏭 تشغيل بيئة الإنتاج..."
	@if [ ! -f .env ]; then \
		echo "⚠️ ملف .env غير موجود، نسخ من القالب..."; \
		cp env-production.template .env; \
		echo "📝 يرجى تعديل .env بالقيم الصحيحة"; \
	fi
	docker-compose up -d --build
	@echo "✅ بيئة الإنتاج تعمل على: https://manage.fikra.solutions"

deploy:
	@echo "🚀 بدء النشر الكامل..."
	chmod +x scripts/deploy.sh
	sudo ./scripts/deploy.sh

stop:
	@echo "⏹️ إيقاف النظام..."
	docker-compose down

restart:
	@echo "🔄 إعادة تشغيل النظام..."
	docker-compose restart

# Monitoring commands
logs:
	@echo "📜 عرض السجلات..."
	docker-compose logs -f --tail=100

health:
	@echo "🏥 فحص صحة النظام..."
	@echo "Testing health endpoint..."
	curl -s http://localhost:8005/health | python3 -m json.tool || echo "❌ فشل الاتصال بالخدمة"

status:
	@echo "📊 حالة الخدمات..."
	docker-compose ps

# Maintenance commands
backup:
	@echo "💾 إنشاء نسخة احتياطية..."
	@if [ -f /usr/local/bin/erp-backup.sh ]; then \
		sudo /usr/local/bin/erp-backup.sh; \
	else \
		echo "⚠️ script النسخ الاحتياطي غير موجود"; \
	fi

clean:
	@echo "🧹 تنظيف النظام..."
	docker system prune -a -f
	docker volume prune -f

update:
	@echo "⬆️ تحديث النظام..."
	git pull origin main
	docker-compose build --no-cache
	docker-compose up -d
	@echo "✅ تم التحديث بنجاح"

test:
	@echo "🧪 اختبار النظام..."
	@echo "Testing database connection..."
	docker-compose exec web python -c "from app import create_app; from extensions import db; app = create_app(); app.app_context().push(); db.session.execute('SELECT 1'); print('✅ Database OK')"
	@echo "Testing health endpoint..."
	curl -s http://localhost:8005/health > /dev/null && echo "✅ Health endpoint OK" || echo "❌ Health endpoint failed"

# Database commands
db-init:
	@echo "🗄️ تهيئة قاعدة البيانات..."
	docker-compose exec web python -c "from app import create_app; from extensions import db; app = create_app(); app.app_context().push(); db.create_all(); print('✅ Database initialized')"

db-migrate:
	@echo "🔄 تطبيق migrations..."
	docker-compose exec web python -c "from flask_migrate import upgrade; from app import create_app; app = create_app(); app.app_context().push(); upgrade(); print('✅ Migrations applied')"

db-shell:
	@echo "🐚 الدخول لقاعدة البيانات..."
	docker-compose exec db psql -U erp_user -d erp_system_production

# Security commands
security-scan:
	@echo "🔍 فحص أمني..."
	@echo "Checking for security updates..."
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v $(PWD):/app --workdir /app aquasec/trivy image erp-system_web:latest

ssl-renew:
	@echo "🔒 تجديد شهادة SSL..."
	sudo certbot renew --quiet
	sudo nginx -t && sudo nginx -s reload

# Quick shortcuts
quick-start: dev
	@echo "🚀 البدء السريع اكتمل!"

production-deploy: deploy
	@echo "🏭 النشر الإنتاجي اكتمل!"

# Environment setup
setup-dev:
	@echo "⚙️ إعداد بيئة التطوير..."
	cp env-production.template .env.dev
	@echo "📝 يرجى تعديل .env.dev للتطوير"

setup-prod:
	@echo "⚙️ إعداد بيئة الإنتاج..."
	cp env-production.template .env
	@echo "📝 يرجى تعديل .env للإنتاج"
	@echo "⚠️ لا تنس تغيير كلمات المرور!"

# Information
info:
	@echo "📋 معلومات النظام:"
	@echo "  الدومين: manage.fikra.solutions"
	@echo "  البورت: 8005"
	@echo "  الشركة: شركة فكرة للحلول التقنية"
	@echo "  الدعم: support@fikra.solutions"
	@echo ""
	@echo "📁 الملفات المهمة:"
	@echo "  - .env (إعدادات الإنتاج)"
	@echo "  - .env.dev (إعدادات التطوير)"
	@echo "  - docker-compose.yml (الإنتاج)"
	@echo "  - docker-compose.dev.yml (التطوير)"
	@echo "  - DEPLOYMENT.md (دليل النشر)"
	@echo "  - QUICK_START.md (البدء السريع)" 