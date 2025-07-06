# 🚀 دليل النشر الشامل - نظام إدارة الموارد

## Domain: manage.fikra.solutions | Port: 8005

---

## 📋 متطلبات النشر

### متطلبات النظام

- Ubuntu 20.04 LTS أو أحدث
- RAM: 4GB كحد أدنى (8GB مُستحسن)
- مساحة التخزين: 20GB كحد أدنى
- معالج: 2 CPU cores كحد أدنى

### البرامج المطلوبة

- Docker & Docker Compose
- Nginx
- Certbot (SSL certificates)
- PostgreSQL (يتم تثبيته عبر Docker)
- Redis (يتم تثبيته عبر Docker)

---

## 🛠️ خطوات النشر

### 1. تحضير الخادم

```bash
# تحديث النظام
sudo apt update && sudo apt upgrade -y

# تثبيت Git
sudo apt install git -y

# استنساخ المشروع
git clone https://github.com/your-username/erp-system.git
cd erp-system
```

### 2. تشغيل script النشر التلقائي

```bash
# إعطاء صلاحيات التنفيذ
chmod +x scripts/deploy.sh

# تشغيل النشر (يجب تشغيله كـ root)
sudo ./scripts/deploy.sh
```

### 3. النشر اليدوي (اختياري)

إذا كنت تفضل النشر اليدوي:

```bash
# نسخ ملف البيئة
cp env-production.template .env

# تعديل متغيرات البيئة
nano .env

# بناء وتشغيل المشروع
docker-compose up -d --build

# التحقق من حالة الخدمات
docker-compose ps
```

---

## ⚙️ الإعدادات المطلوبة

### 1. متغيرات البيئة (.env)

```env
# أمان - يجب تغييرها فوراً
SECRET_KEY=your-super-secret-key-change-this-immediately
JWT_SECRET_KEY=your-jwt-secret-key-change-this-immediately

# قاعدة البيانات
DATABASE_URL=postgresql://erp_user:secure_password_123@localhost:5432/erp_system_production

# Redis
REDIS_URL=redis://localhost:6379/0

# الدومين
DOMAIN=manage.fikra.solutions
PORT=8005

# البريد الإلكتروني
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@fikra.solutions
```

### 2. إعدادات SSL

```bash
# الحصول على شهادة SSL
sudo certbot certonly --nginx -d manage.fikra.solutions -d www.manage.fikra.solutions

# تجديد تلقائي
sudo crontab -e
# إضافة: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 3. إعدادات DNS

أضف هذه السجلات في إعدادات DNS:

```
A    manage.fikra.solutions        YOUR_SERVER_IP
A    www.manage.fikra.solutions    YOUR_SERVER_IP
AAAA manage.fikra.solutions        YOUR_SERVER_IPv6 (اختياري)
```

---

## 🔒 الأمان

### 1. Firewall

```bash
# إعداد الجدار الناري
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8005/tcp
```

### 2. كلمات المرور الافتراضية

**⚠️ يجب تغييرها فوراً:**

- **Admin Panel**: admin / admin123
- **Database**: erp_user / secure_password_123
- **Redis**: redis_password_123
- **Supervisor**: admin / supervisor_admin_123

### 3. تحديث كلمات المرور

```bash
# تغيير كلمة مرور الأدمن
docker-compose exec web python -c "
from app import create_app
from models.user import User
from extensions import db, bcrypt

app = create_app()
with app.app_context():
    admin = User.query.filter_by(username='admin').first()
    admin.password = bcrypt.generate_password_hash('NEW_PASSWORD').decode('utf-8')
    db.session.commit()
    print('كلمة المرور تم تحديثها')
"
```

---

## 📊 المراقبة والصيانة

### 1. مراقبة الخدمات

```bash
# حالة الخدمات
docker-compose ps

# السجلات
docker-compose logs -f

# استخدام الموارد
docker stats

# مراقبة النظام
htop
```

### 2. النسخ الاحتياطية

```bash
# نسخة احتياطية يدوية
sudo /usr/local/bin/erp-backup.sh

# عرض النسخ الاحتياطية
ls -la /opt/erp-system/backups/
```

### 3. تنظيف النظام

```bash
# تنظيف Docker
docker system prune -a

# تنظيف السجلات
sudo journalctl --vacuum-time=7d

# تنظيف النسخ الاحتياطية القديمة
find /opt/erp-system/backups/ -name "*.sql" -mtime +30 -delete
```

---

## 🔧 أوامر مفيدة

### إدارة الخدمات

```bash
# إعادة تشغيل
docker-compose restart

# إيقاف
docker-compose down

# تحديث التطبيق
git pull origin main
docker-compose build --no-cache
docker-compose up -d

# إعادة تعيين قاعدة البيانات
docker-compose exec db psql -U erp_user -d erp_system_production -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
```

### تشخيص الأخطاء

```bash
# سجلات التطبيق
docker-compose logs web

# سجلات قاعدة البيانات
docker-compose logs db

# سجلات Nginx
docker-compose logs nginx

# اختبار الاتصال
curl -I http://localhost:8005/health
```

---

## 🌐 الوصول للخدمات

### روابط الوصول

- **الموقع الرئيسي**: https://manage.fikra.solutions
- **Health Check**: https://manage.fikra.solutions/health
- **Portainer**: http://SERVER_IP:9000
- **Supervisor**: http://127.0.0.1:9001

### حسابات الدخول الافتراضية

```
نظام إدارة الموارد:
- المستخدم: admin
- كلمة المرور: admin123

Portainer:
- يتم إنشاؤه عند الدخول الأول

Supervisor:
- المستخدم: admin
- كلمة المرور: supervisor_admin_123
```

---

## 🆘 حل المشاكل الشائعة

### 1. الخدمات لا تعمل

```bash
# إعادة تشغيل جميع الخدمات
docker-compose down
docker-compose up -d

# التحقق من السجلات
docker-compose logs
```

### 2. مشاكل قاعدة البيانات

```bash
# إعادة تشغيل قاعدة البيانات
docker-compose restart db

# الدخول لقاعدة البيانات
docker-compose exec db psql -U erp_user -d erp_system_production
```

### 3. مشاكل SSL

```bash
# تجديد الشهادة
sudo certbot renew --nginx

# اختبار الإعدادات
sudo nginx -t
sudo systemctl reload nginx
```

### 4. مشاكل الذاكرة

```bash
# تنظيف الذاكرة
docker system prune -a
docker volume prune
```

---

## 📱 الاتصال والدعم

### معلومات الشركة

- **الاسم**: شركة فكرة للحلول التقنية
- **البريد الإلكتروني**: info@fikra.solutions
- **الموقع**: https://manage.fikra.solutions

### الدعم الفني

- **البريد الإلكتروني**: support@fikra.solutions
- **الهاتف**: +966 11 234 5678

---

## 📝 ملاحظات مهمة

1. **قم بتغيير جميع كلمات المرور الافتراضية فوراً**
2. **اعمل نسخة احتياطية قبل أي تحديث**
3. **راقب استخدام الموارد بانتظام**
4. **حدث الشهادات الأمنية كل 90 يوم**
5. **فعل التحديثات الأمنية للنظام**

---

## 🏆 تم النشر بنجاح!

إذا اتبعت جميع الخطوات بشكل صحيح، يجب أن يكون نظام إدارة الموارد يعمل الآن على:

**🌐 https://manage.fikra.solutions**

**استمتع بنظام إدارة الموارد الخاص بك! 🎉**
