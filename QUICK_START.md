# ⚡ دليل البدء السريع - نظام إدارة الموارد

## 🚀 النشر السريع على VPS

### خطوات النشر في 5 دقائق:

```bash
# 1. تحديث النظام
sudo apt update && sudo apt upgrade -y

# 2. استنساخ المشروع
git clone https://github.com/your-repo/erp-system.git
cd erp-system

# 3. تشغيل النشر التلقائي
chmod +x scripts/deploy.sh
sudo ./scripts/deploy.sh

# 4. انتظار اكتمال النشر...
# سيتم تثبيت جميع المتطلبات تلقائياً
```

### النتيجة النهائية:

- **الموقع**: https://manage.fikra.solutions
- **البورت**: 8005
- **الأدمن**: admin / admin123

---

## 🔧 إعدادات سريعة

### 1. تعديل ملف البيئة:

```bash
cp env-production.template .env
nano .env
```

### 2. المتغيرات المهمة:

```env
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here
DOMAIN=manage.fikra.solutions
PORT=8005
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

### 3. تشغيل النظام:

```bash
docker-compose up -d
```

---

## 📋 فحص سريع

### اختبار الخدمات:

```bash
# حالة الخدمات
docker-compose ps

# اختبار الصحة
curl http://localhost:8005/health

# السجلات
docker-compose logs -f web
```

### روابط مهمة:

- **الموقع**: https://manage.fikra.solutions
- **Health Check**: https://manage.fikra.solutions/health
- **Portainer**: http://YOUR_IP:9000

---

## 🛠️ أوامر سريعة

```bash
# إعادة تشغيل
docker-compose restart

# إيقاف
docker-compose down

# تحديث
git pull && docker-compose up -d --build

# نسخة احتياطية
sudo /usr/local/bin/erp-backup.sh
```

---

## 🆘 حل سريع للمشاكل

### المشكلة: الخدمات لا تعمل

```bash
docker-compose down
docker-compose up -d
```

### المشكلة: قاعدة البيانات

```bash
docker-compose restart db
```

### المشكلة: SSL

```bash
sudo certbot renew
sudo nginx -t && sudo nginx -s reload
```

---

## 📱 معلومات الدعم

- **الدعم**: support@fikra.solutions
- **الموقع**: https://manage.fikra.solutions
- **الشركة**: شركة فكرة للحلول التقنية

---

**✅ نظام إدارة الموارد جاهز للاستخدام!**
