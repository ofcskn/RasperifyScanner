# Stage 1: Build Python dependencies
FROM debian:trixie-slim AS deps

WORKDIR /deps
COPY requirements.txt .

# Build tools; libcap-dev removed since picamera2 is now host-mounted
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip gcc libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# --copies so the venv is fully portable between build and runtime stages
RUN python3 -m venv --copies /venv \
    && /venv/bin/pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime image
FROM debian:trixie-slim

WORKDIR /app

# System tools + native libraries needed by onnxruntime / numpy / Pillow.
# libboost-log/thread, liblttng-ust, libdw, libudev are transitive deps of
# the host-mounted libcamera (Pi-specific build); they ARE in Debian trixie.
# The Pi-specific .so files themselves (libcamera.so, libpisp.so, libyuv.so)
# are bind-mounted at runtime from the host via docker-compose volumes.
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    curl \
    iproute2 \
    libatlas3-base \
    libgomp1 \
    libboost-log1.83.0 \
    libboost-thread1.83.0 \
    liblttng-ust1t64 \
    libdw1t64 \
    libudev1 \
    libyaml-0-2 \
    libjpeg62-turbo \
    # Native runtime deps of the host-mounted picamera2 stack. simplejpeg needs
    # libturbojpeg; pykms (preview, imported eagerly by picamera2) needs
    # libkms++/libdrm/libfmt; the Pi vc4 IPA module links TensorFlow-Lite ->
    # abseil/farmhash/cpuinfo. These are stock Debian packages; only the
    # Pi-specific libs (libcamera/libpisp/libkms++/libtensorflow-lite) are
    # bind-mounted from the host (see docker-compose.yml).
    libturbojpeg0 \
    libdrm2 \
    libfmt10 \
    libabsl20240722 \
    libfarmhash0 \
    libcpuinfo0 \
    && rm -rf /var/lib/apt/lists/*

# Copy the portable venv from the build stage
COPY --from=deps /venv /venv

COPY . .

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["/venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
