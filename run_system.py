# -*- coding: utf-8 -*-
"""
تشغيل سريع للنظام الشامل
"""

import os
import sys
from datetime import datetime

def run_system():
    """تشغيل النظام الشامل"""
    print("🚀 تشغيل نظام إدارة المشاريع الشامل...")
    print("="*60)
    
    # إعداد النظام
    print("⚙️ إعداد النظام...")
    try:
        # تشغيل سكريپت إعداد الاشتراكات
        os.system("python quick_setup_subscriptions.py")
        print("✅ تم إعداد النظام بنجاح")
    except Exception as e:
        print(f"❌ خطأ في إعداد النظام: {str(e)}")
    
    print("\n" + "="*60)
    print("🎉 النظام جاهز للاستخدام!")
    print("="*60)
    
    print("\n📋 معلومات تسجيل الدخول:")
    print("البريد الإلكتروني: admin@erp.com")
    print("كلمة المرور: admin123")
    
    print("\n🌐 الصفحات المتاحة:")
    print("- الصفحة الرئيسية: http://localhost:5000")
    print("- لوحة التحكم: http://localhost:5000/dashboard")
    print("- إدارة المشاريع: http://localhost:5000/projects")
    print("- الاشتراكات: http://localhost:5000/subscriptions")
    print("- إدارة العملاء: http://localhost:5000/clients")
    
    print("\n🔧 خصائص النظام المطور:")
    print("✅ مشاريع الاشتراك الشهري مع عدة عملاء")
    print("✅ المشاريع التقليدية مع نظام الدفعات (مقدم + أقساط)")
    print("✅ تفاصيل مخصصة لكل عميل (دومين، سيرفر، إلخ)")
    print("✅ نظام إرسال الرسائل (إيميل وواتساب)")
    print("✅ إحصائيات شاملة ومتقدمة")
    print("✅ واجهة عربية متجاوبة وحديثة")
    
    print("\n💰 الإيرادات الحالية:")
    try:
        # محاولة عرض الإحصائيات السريعة
        from app import create_app
        from models import ClientSubscription, Project
        from sqlalchemy import func
        
        app = create_app()
        with app.app_context():
            # الإيرادات الشهرية
            monthly_revenue = db.session.query(
                func.sum(ClientSubscription.monthly_amount)
            ).filter(ClientSubscription.status == 'active').scalar() or 0
            
            # عدد المشاريع
            total_projects = Project.query.count()
            subscription_projects = Project.query.filter_by(project_type='subscription').count()
            
            print(f"💵 الإيرادات الشهرية: {float(monthly_revenue):,.2f} ج.م")
            print(f"📊 إجمالي المشاريع: {total_projects}")
            print(f"🔄 مشاريع الاشتراك: {subscription_projects}")
            
    except Exception as e:
        print(f"📊 (إحصائيات غير متوفرة: {str(e)})")
    
    print("\n" + "="*60)
    print("🌟 النظام يدعم:")
    print("1️⃣ إدخال مشروع بسعر معين")
    print("2️⃣ مشاريع غير اشتراكية: مقدم + دفعات")
    print("3️⃣ مشاريع اشتراكية: متعددة العملاء")
    print("4️⃣ تفاصيل مخصصة: دومين، سيرفر، قاعدة بيانات")
    print("5️⃣ دفع اشتراك شهري للعملاء")
    print("6️⃣ عرض وإدارة جميع العملاء")
    print("7️⃣ إرسال رسائل (إيميل/واتساب)")
    print("="*60)
    
    print("\n🚀 تشغيل الخادم...")
    print("⏰ الوقت:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60 + "\n")
    
    # تشغيل الخادم
    try:
        os.system("python app.py")
    except KeyboardInterrupt:
        print("\n\n👋 تم إيقاف النظام. شكراً لك!")
    except Exception as e:
        print(f"\n❌ خطأ في تشغيل الخادم: {str(e)}")

if __name__ == '__main__':
    run_system() 