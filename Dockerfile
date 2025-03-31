# Alap image
FROM python:3.11-slim

# Környezeti változók
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Függőségek telepítése
RUN apt-get update && apt-get install -y \
    libffi-dev \
    python3-dev \
    build-essential

# Munkakönyvtár létrehozása
WORKDIR /app
COPY . /app

# requirements.txt bemásolása
COPY requirements.txt .

# Pip frissítés és függőségek telepítése
RUN pip install --upgrade pip --no-cache-dir && pip install --no-cache-dir -r requirements.txt

# Teljes projekt bemásolása
COPY . .

# Statikus fájlok összegyűjtése
RUN python manage.py collectstatic --noinput

# Port kinyitása (pl. 8000, ha a runserver-t használod)
EXPOSE 8080

# A gunicorn telepítése
RUN pip install gunicorn

# A parancs a gunicorn indításához
CMD ["gunicorn", "--workers", "3", "--bind", "0.0.0.0:8080", "_core.wsgi:application"]