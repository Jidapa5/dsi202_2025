from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # ✅ ใช้ allauth สำหรับ auth
    path('accounts/', include('allauth.urls')),

    # ✅ เปลี่ยน /login/ ให้ redirect ไปยัง Google login
    path('login/', lambda request: redirect('account_login')),

    # ✅ เส้นทางหลักของแอป outfits
    path('', include('outfits.urls')),

    path('accounts/', include('django.contrib.auth.urls')), 
]

# ✅ สำหรับให้แสดง media ได้ตอน dev
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
