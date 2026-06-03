# Stage 1: Build Python dependencies
FROM python:3.11-slim-bookworm AS deps

WORKDIR /deps
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Runtime image
FROM python:3.11-slim-bookworm

WORKDIR /app

# System tools + libcamera runtime bindings needed by picamera2.
# python3-libcamera provides the _libcamera.so extension for the system Python;
# PYTHONPATH below makes it visible to the pip-installed Python 3.11 as well.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    iproute2 \
    libcamera0t64 \
    libcamera-dev \
    python3-libcamera \
    python3-kms++ \
    python3-prctl \
    libatlas3-base \
    && rm -rf /var/lib/apt/lists/*

# Expose system libcamera Python bindings to the pip Python interpreter
ENV PYTHONPATH=/usr/lib/python3/dist-packages:$PYTHONPATH

# Copy installed pip packages from deps stage
COPY --from=deps /install /usr/local

COPY . .

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
