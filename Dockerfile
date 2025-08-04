# EyeWitness Dockerfile
# Provides a fully containerized environment for running EyeWitness
# No Python, Firefox, or other dependencies needed on host system

FROM python:3.11-slim-bookworm

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    # Disable Selenium Manager to prevent network requests
    SE_MANAGER_PATH="" \
    SE_OFFLINE=1 \
    WDM_LOG_LEVEL=0

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Firefox and display dependencies
    firefox-esr \
    xvfb \
    x11-utils \
    # Required libraries
    libgtk-3-0 \
    libdbus-glib-1-2 \
    libxt6 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libasound2 \
    libpangocairo-1.0-0 \
    libatk1.0-0 \
    libcairo-gobject2 \
    libgtk-3-0 \
    libgdk-pixbuf-2.0-0 \
    # Fonts for proper rendering
    fonts-liberation \
    fonts-noto \
    fonts-noto-cjk \
    # Utilities
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install geckodriver
# Using specific version for compatibility
ARG GECKODRIVER_VERSION=v0.34.0
RUN ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ]; then \
        GECKO_ARCH="linux64"; \
    elif [ "$ARCH" = "arm64" ]; then \
        GECKO_ARCH="linux-aarch64"; \
    else \
        echo "Unsupported architecture: $ARCH" && exit 1; \
    fi && \
    wget -q -O /tmp/geckodriver.tar.gz \
        "https://github.com/mozilla/geckodriver/releases/download/${GECKODRIVER_VERSION}/geckodriver-${GECKODRIVER_VERSION}-${GECKO_ARCH}.tar.gz" && \
    tar -xzf /tmp/geckodriver.tar.gz -C /usr/local/bin && \
    rm /tmp/geckodriver.tar.gz && \
    chmod +x /usr/local/bin/geckodriver

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY setup/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY Python/ .

# Create directories for input/output with proper permissions
RUN mkdir -p /data /output && \
    chmod 777 /data /output

# Create non-root user for security
RUN useradd -m -u 1000 eyewitness && \
    chown -R eyewitness:eyewitness /app

# Create entrypoint script
RUN echo '#!/bin/bash\n\
# Handle signals for graceful shutdown\n\
trap "exit" INT TERM\n\
\n\
# If running as root, warn user\n\
if [ "$EUID" -eq 0 ]; then\n\
    echo "[!] Warning: Running as root. Output files will be owned by root."\n\
    echo "[!] Consider using --user $(id -u):$(id -g) when running docker"\n\
fi\n\
\n\
# Start Xvfb in background\n\
Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp &\n\
export DISPLAY=:99\n\
\n\
# Wait for Xvfb to start\n\
sleep 2\n\
\n\
# Run EyeWitness with all arguments\n\
python /app/EyeWitness.py "$@"\n\
' > /entrypoint.sh && chmod +x /entrypoint.sh

# Default to non-root user (can be overridden with --user)
USER eyewitness

# Set the entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Default command (show help)
CMD ["--help"]

# Labels for metadata
LABEL maintainer="Red Siege <GetOffensive@redsiege.com>" \
      description="EyeWitness - Web Screenshot Tool" \
      version="1.0" \
      org.opencontainers.image.source="https://github.com/RedSiege/EyeWitness"