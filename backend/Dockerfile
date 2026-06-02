# Stage 1: Build dependencies
FROM python:3.11-slim-bullseye AS deps

WORKDIR /deps
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Application image (ARM64-compatible)
FROM python:3.11-slim-bullseye

WORKDIR /app

# Copy installed packages from deps stage
COPY --from=deps /install /usr/local

COPY . .

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CAMERA_MOCK=true

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
