FROM python:3.11

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install build tools for packages like crc16
RUN apt-get update && \
    apt-get install -y gcc build-essential && \
    apt-get clean

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt 

COPY . /app/


RUN python manage.py collectstatic --noinput

CMD ["gunicorn", "mindvibe_project.wsgi:application", "--bind", "0.0.0.0:8000"]
