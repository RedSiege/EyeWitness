# EyeWitness - Simplified Docker Edition
# Fast, minimal, reliable - like other Docker tools

FROM python:3.11-slim-bookworm

# Install everything in ONE layer - fast and minimal
RUN apt-get update && apt-get install -y --no-install-recommends     chromium chromium-driver xvfb     && rm -rf /var/lib/apt/lists/*     && pip install --no-cache-dir         selenium>=4.29.0         rapidfuzz>=3.0.0         netaddr>=0.10.0         psutil>=5.9.0         pyvirtualdisplay>=3.0

# Set environment - no runtime complexity  
ENV DISPLAY=:99     CHROME_HEADLESS=1     CHROME_NO_SANDBOX=1     DOCKER_CONTAINER=1

# Copy app
WORKDIR /app
COPY Python/ .

# Simple entrypoint - start virtual display and run app
ENTRYPOINT ["/bin/bash", "-c", "Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp -nolisten unix & exec python EyeWitness.py \"$@\""]
