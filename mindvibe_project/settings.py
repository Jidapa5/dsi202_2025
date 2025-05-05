# mindvibe_project/settings.py
import os
from pathlib import Path
import dj_database_url # ตรวจสอบว่ามี import นี้
from dotenv import load_dotenv

load_dotenv() # ตรวจสอบว่ามีการเรียกใช้

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY is not set in environment variables!")

DEBUG = int(os.environ.get('DEBUG', 0)) == 1

allowed_hosts_str = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_str.split(',') if host.strip()]
if DEBUG and 'localhost' not in ALLOWED_HOSTS: # ตรวจสอบก่อนเพิ่ม
    ALLOWED_HOSTS.append('localhost')
# เพิ่ม '*' ถ้าต้องการ allow ทุก host (สำหรับ development เท่านั้น)
# ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic', # ควรอยู่หลัง messages
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'outfits', # แอปของคุณ
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # ควรอยู่สูงๆ หลัง SecurityMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'mindvibe_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # --- แก้ไข DIRS ให้ถูกต้อง ---
        'DIRS': [BASE_DIR / 'templates'], # โฟลเดอร์ templates ระดับ project
        'APP_DIRS': True, # ให้หา template ในแอปด้วย
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'outfits.context_processors.cart', # context processor ของคุณ
            ],
        },
    },
]

WSGI_APPLICATION = 'mindvibe_project.wsgi.application'

# --- Database ---
# ใช้ dj_database_url เพื่ออ่านจาก DATABASE_URL env var
# ถ้าไม่มี env var จะใช้ sqlite เป็น default
DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
    )
}


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'th'
TIME_ZONE = 'Asia/Bangkok'
USE_I18N = True
USE_TZ = True # ควรเป็น True

# --- Static/Media files ---
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles' # สำหรับ collectstatic ตอน deploy
# --- แก้ไข STATICFILES_DIRS ---
# ถ้า static files ของ project (ไม่ใช่ของ app) อยู่ที่ root/static
# STATICFILES_DIRS = [BASE_DIR / 'static']
# ถ้าไม่มี static files ส่วนกลาง ให้ comment หรือลบออกไปเลย
STATICFILES_DIRS = [] # ลองแบบนี้ดูก่อน
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage' # สำหรับ Whitenoise ตอน deploy

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login' # ใช้ name 'login' ของ Django Auth
LOGOUT_REDIRECT_URL = 'outfits:home' # ไปหน้า home หลัง logout
LOGIN_REDIRECT_URL = 'outfits:user_profile' # ไปหน้า profile หลัง login/register

CART_SESSION_ID = 'cart'

# --- Bank Account Information ---
BANK_ACCOUNT_NAME = os.environ.get('BANK_ACCOUNT_NAME', 'โปรดระบุชื่อบัญชีใน .env')
BANK_ACCOUNT_NUMBER = os.environ.get('BANK_ACCOUNT_NUMBER', 'โปรดระบุเลขบัญชีใน .env')
BANK_NAME = os.environ.get('BANK_NAME', 'โปรดระบุธนาคารใน .env')
# --- เปลี่ยนเป็น Static Path ---
BANK_QR_CODE_STATIC_PATH = os.environ.get('BANK_QR_CODE_STATIC_PATH', 'outfits/images/my_qr.jpg') # <--- แก้ไข path และชื่อไฟล์ให้ตรงกับของคุณ

# --- Email Configuration ---
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true' # อ่านค่า boolean
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER or 'webmaster@localhost' # ใส่ default ไว้

