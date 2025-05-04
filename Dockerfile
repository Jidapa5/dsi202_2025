# ใช้ Python เวอร์ชั่น 3.9 หรือใหม่กว่าเป็น Base Image
FROM python:3.9-slim

# ตั้งค่า Environment Variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# สร้างและกำหนด Working Directory
WORKDIR /app

# ติดตั้ง Dependencies ของระบบ (ถ้ามี)
# RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client

# ติดตั้ง Python Dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy โค้ดโปรเจกต์ทั้งหมดเข้าไปใน Container
COPY . .

# (Optional) Collect static files ถ้าต้องการให้ Nginx serve
# RUN python manage.py collectstatic --noinput

# Expose port ที่ Gunicorn จะรัน (ปกติ 8000)
EXPOSE 8000

# รัน Gunicorn (Web Server สำหรับ Production)
# แทนที่ 'mindvibe_project.wsgi:application' ด้วยชื่อโปรเจกต์ของคุณถ้าต่างไป
CMD ["gunicorn", "mindvibe_project.wsgi:application", "--bind", "0.0.0.0:8000"]