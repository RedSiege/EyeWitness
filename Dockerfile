FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends     chromium chromium-driver xvfb     && rm -rf /var/lib/apt/lists/*     && pip install --no-cache-dir         selenium>=4.29.0         rapidfuzz>=3.0.0         netaddr>=0.10.0         psutil>=5.9.0         pyvirtualdisplay>=3.0

ENV DISPLAY=:99     CHROME_HEADLESS=1     CHROME_NO_SANDBOX=1     DOCKER_CONTAINER=1

COPY Python/ /opt/eyewitness/

RUN echo '#!/bin/bash\nXvfb :99 -screen 0 1920x1080x24 -nolisten tcp -nolisten unix &\nexec python /opt/eyewitness/EyeWitness.py "$@"' > /entrypoint.sh && chmod +x /entrypoint.sh

WORKDIR /workspace

ENTRYPOINT ["/entrypoint.sh"]
