import os
from pathlib import Path
import dj_database_url # เพิ่ม import

# ตั้งค่า base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Security settings (อ่านจาก Environment Variables)
# **สำคัญ:** ตั้งค่าเหล่านี้ใน Environment จริง หรือใช้ไฟล์ .env
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-fallback-key-for-dev') # ใส่ key fallback ปลอดภัยกว่า
DEBUG = int(os.environ.get('DEBUG', 0)) # Default เป็น 0 (Production)

# อ่าน Allowed Hosts จาก Environment หรือใช้ default
allowed_hosts_str = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_str.split(',') if host.strip()]


# ตั้งค่าการใช้งานแอปต่างๆ
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'outfits',  # แอป outfits
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # เพิ่มสำหรับ Serve static file ใน production (ถ้าไม่ใช้ Nginx)
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'mindvibe_project.urls'

# ตั้งค่าเทมเพลต
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'], # ถ้ามี Global templates
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                 # เพิ่ม context processor สำหรับ Cart (ถ้าต้องการแสดง cart ทั่วเว็บ)
                'outfits.context_processors.cart_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'mindvibe_project.wsgi.application'

# ฐานข้อมูล (อ่านจาก DATABASE_URL)
DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}" # Fallback เป็น SQLite ถ้าไม่มี DATABASE_URL
    )
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us' # หรือ 'th' ถ้าต้องการ
TIME_ZONE = 'Asia/Bangkok' # ตั้งค่า Time Zone
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'

# ที่อยู่สำหรับเก็บ static files ที่จะ serve ใน production (หลังรัน collectstatic)
STATIC_ROOT = BASE_DIR / 'staticfiles'
# ที่อยู่เพิ่มเติมสำหรับ static files ใน development
STATICFILES_DIRS = [ BASE_DIR / "outfits/static" ]
# เพิ่ม STATICFILES_STORAGE สำหรับ WhiteNoise (ถ้าใช้)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# Media files (User uploaded content)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login/Logout URLs
LOGIN_URL = 'login'
LOGOUT_REDIRECT_URL = 'home'
LOGIN_REDIRECT_URL = 'user_profile' # Redirect ไปหน้า profile หลัง login สำเร็จ

# Cart session key
CART_SESSION_ID = 'cart'
