# ใช้ Python base image
FROM python:3.11-slim

# ตั้ง working directory ใน container
WORKDIR /app

# คัดลอกไฟล์ requirements
COPY requirements.txt .

# ติดตั้ง dependencies
RUN pip install --no-cache-dir -r requirements.txt

# คัดลอกโปรเจกต์เข้า container
COPY . .

# รัน server (สามารถเปลี่ยนเป็นคำสั่งอื่นภายหลัง เช่น gunicorn)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
