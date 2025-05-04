from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from outfits import views as outfits_views # เปลี่ยนชื่อ import เล็กน้อย

urlpatterns = [
    path('admin/', admin.site.urls),

    # Authentication URLs (ใช้ของ Django)
    path('login/', auth_views.LoginView.as_view(template_name='outfits/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'), # ไม่ต้องระบุ template ก็ได้ถ้าใช้ default redirect
    path('register/', outfits_views.register, name='register'), # ใช้ view ที่เราสร้างเอง

    # Password Reset URLs (ถ้าต้องการ)
    # path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    # ... (เพิ่ม URL อื่นๆ สำหรับ password reset)

    # Include URLs จากแอป outfits
    path('', include('outfits.urls', namespace='outfits')), # ใส่ namespace='outfits'
]

# Serve media files ใน Development mode
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # ไม่จำเป็นต้อง serve static files แบบนี้ถ้าใช้ whitenoise หรือ Django จัดการเอง
    # urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# หมายเหตุ: ใน Production จริงๆ ควรให้ Web Server (เช่น Nginx) จัดการ Serve static และ media files