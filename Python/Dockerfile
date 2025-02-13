FROM debian
LABEL maintainer Archidote

RUN apt-get update && \
    echo '\e[32m[*] Installing Debian Dependencies...\e[39m' && \ 
    apt-get install -y git wget cmake python3 xvfb python3-pip python3-netaddr python3-dev firefox-esr python3-venv && \
    rm -rf /var/lib/apt/lists/*

RUN	git clone --depth 1 https://github.com/RedSiege/EyeWitness.git /EyeWitness

WORKDIR /EyeWitness

RUN echo -e '\e[32m[*] Setting up the EyeWitness Python env (venv and dependencies)...\e[39m"' && \
    python3 -m venv venv && . venv/bin/activate && \ 
    python3 -m pip install --no-cache-dir fuzzywuzzy selenium==4.9.1 python-Levenshtein pyvirtualdisplay netaddr && \
    cd Python/setup && ./setup.sh && \
    rm -rf /var/lib/apt/lists/*

ENTRYPOINT ["/bin/bash", "-c", "source /EyeWitness/venv/bin/activate && python3 /EyeWitness/Python/EyeWitness.py -d /tmp/out --no-prompt $@"]