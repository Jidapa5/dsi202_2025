from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns  # ✅ ใช้สำหรับ path แบบหลายภาษา
from django.views.i18n import set_language

# ✅ สำหรับ set language (เช่นจาก dropdown toggle)
urlpatterns = [
    path('set-language/', set_language, name='set_language'),
]

# ✅ เส้นทางทั้งหมดที่รองรับ i18n
urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),

    # ✅ Allauth สำหรับ Auth
    path('accounts/', include('allauth.urls')),

    # ✅ Django's built-in auth views (password reset ฯลฯ)
    path('auth/', include('django.contrib.auth.urls')),

    # ✅ เส้นทาง login กำหนดใหม่ให้ redirect ไป Google Login
    path('login/', lambda request: redirect('account_login')),

    # ✅ เส้นทางหลักของแอป outfits
    path('', include('outfits.urls')),
)

# ✅ เสิร์ฟ media ไฟล์ตอน DEBUG = True
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
