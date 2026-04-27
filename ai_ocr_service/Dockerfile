FROM python:3.10-slim

# Evitar que Python genere archivos .pyc y asegurar logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalar dependencias del sistema
# Se añade 'curl' para el healthcheck de Docker
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    gcc \
    python3-dev \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Actualizar pip e instalar librerías de IA y API
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    fastapi \
    uvicorn \
    python-multipart \
    paddlepaddle==2.6.2 \
    paddleocr==2.7.3 \
    Pillow \
    "numpy<2.0.0"

# Copiamos el servidor (aunque el volumen lo sobreescriba en desarrollo, 
# es buena práctica para que la imagen sea autoportante)
COPY server.py .

# El puerto donde corre Uvicorn
EXPOSE 8000

# Comando para arrancar la aplicación
CMD ["python", "server.py"]
